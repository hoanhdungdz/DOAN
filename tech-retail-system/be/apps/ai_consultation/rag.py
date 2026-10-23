"""Grounded consultation: public retrieval + ORM constraints + live, server-owned cards."""

from decimal import Decimal, InvalidOperation
import re
from django.conf import settings
from django.core.cache import cache
from django.db.models import F
from django.utils import timezone
from common.errors import BusinessError
from apps.products.models import ProductVariant, Category, Brand, Product
from apps.stores.models import Store
from .index import documents, sync_index, normalize
from .provider import GeminiProvider, ready

STOP = set(
    "toi ban muon can cho la va cua co nao nhung mot cac voi de duoc trong giup xem ve nay khong hang san pham may tim".split()
)
CATEGORIES = {
    "laptop": ("laptop", "may tinh xach tay"),
    "dien thoai": ("dien thoai", "iphone", "smartphone"),
    "may tinh bang": ("may tinh bang", "ipad", "tablet"),
    "may tinh de ban": ("mac mini", "may tinh de ban", "desktop"),
    "man hinh": ("man hinh pc", "man hinh gaming", "monitor"),
    "am thanh": ("tai nghe", "loa bluetooth", "dong ho", "smartwatch"),
    "gia dung": ("tivi", "robot hut bui", "smarthome"),
}


def redact(text):
    text = re.sub(r"[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}", "[email đã ẩn]", str(text))
    text = re.sub(r"(?<!\w)(?:\+?84|0)\d[\d .-]{7,14}\d(?!\w)", "[điện thoại đã ẩn]", text)
    return re.sub(r"AIza[\w-]{20,}|Bearer\s+[\w.-]+", "[khóa đã ẩn]", text, flags=re.I)


def words(text):
    return set(re.findall(r"[a-z0-9]+", normalize(text))) - STOP


def _money(number, unit):
    try:
        value = (
            Decimal(number.replace(",", ".")) * 1_000_000
            if unit.startswith("tr")
            else Decimal(number.replace(".", "").replace(",", ""))
        )
        return (
            value
            if value.is_finite() and 0 <= value <= 1_000_000_000_000 and (unit or value >= 10_000)
            else None
        )
    except InvalidOperation:
        return None


def criteria(question):
    q = normalize(question)
    data = {
        "stores": [],
        "brands": [],
        "category": None,
        "min": None,
        "max": None,
        "strict_max": False,
        "in_stock": "con hang" in q,
    }
    number = r"(\d+(?:[.,]\d+)*)"
    unit = r"\s*(trieu|tr\b|vnd|dong|₫)?"
    between = re.search(number + r"\s*(?:-|den|toi)\s*" + number + unit, q)
    if between and between.group(3):
        data["min"] = _money(between.group(1), between.group(3))
        data["max"] = _money(between.group(2), between.group(3))
    else:
        upper = re.search(r"(duoi|khong qua|toi da|tam|khoang|ngan sach|gia)\s*" + number + unit, q)
        lower = re.search(r"(?:tren|it nhat|tu)\s*" + number + unit, q)
        if upper:
            data["max"] = _money(upper.group(2), upper.group(3) or "")
            data["strict_max"] = upper.group(1) == "duoi"
        if lower:
            data["min"] = _money(lower.group(1), lower.group(2) or "")
    for category in Category.objects.filter(is_active=True):
        name = normalize(category.name)
        for group, aliases in CATEGORIES.items():
            if group in name and any(
                re.search(r"\b" + re.escape(alias) + r"\b", q) for alias in aliases
            ):
                data["category"] = category.pk
                break
        if data["category"]:
            break
    for store in Store.objects.filter(is_active=True):
        aliases = [
            normalize(s).replace("chi nhanh", "").strip() for s in re.split(r"[-—]", store.name)
        ]
        if any(len(alias) >= 4 and alias in q for alias in aliases):
            data["stores"].append(store.pk)
    for brand in Brand.objects.filter(is_active=True):
        name = normalize(brand.name).split(" chinh hang")[0].strip()
        if len(name) >= 2 and re.search(r"\b" + re.escape(name) + r"\b", q):
            data["brands"].append(brand.pk)
    return data


def eligible(filters, product_slug=""):
    qs = (
        ProductVariant.objects.filter(
            is_active=True,
            product__is_active=True,
            product__category__is_active=True,
            product__brand__is_active=True,
        )
        .select_related("product")
        .prefetch_related("product__images")
    )
    if filters["category"]:
        qs = qs.filter(product__category_id=filters["category"])
    if filters["brands"]:
        qs = qs.filter(product__brand_id__in=filters["brands"])
    if filters["min"] is not None:
        qs = qs.filter(price__gte=filters["min"])
    if filters["max"] is not None:
        qs = qs.filter(**{"price__lt" if filters["strict_max"] else "price__lte": filters["max"]})
    if product_slug:
        qs = qs.filter(product__slug=product_slug)
    if filters["in_stock"] or filters["stores"]:
        lookup = {
            "balances__on_hand__gt": F("balances__reserved"),
            "balances__warehouse__is_active": True,
            "balances__warehouse__store__is_active": True,
        }
        if filters["stores"]:
            lookup["balances__warehouse__store_id__in"] = filters["stores"]
        qs = qs.filter(**lookup)
    return qs.distinct().order_by("price", "pk")


def ranked_sources(rows, query_vector, question, product_ids, *, policy_only=False):
    tokens = words(question)
    ranked = []
    for row in rows:
        if row["kind"] == "product" and (policy_only or row["ref"] not in product_ids):
            continue
        similarity = sum(a * b for a, b in zip(query_vector, row["vector"], strict=True))
        overlap = len(tokens & words(row["text"])) / max(len(tokens), 1)
        title_overlap = len(tokens & words(row["title"])) / max(len(tokens), 1)
        if similarity < 0.35 and overlap == 0:
            continue
        score = similarity + min(0.25, overlap * 0.25) + min(0.15, title_overlap * 0.15)
        ranked.append((score, row))
    ranked.sort(key=lambda pair: (-pair[0], pair[1]["id"]))
    sources, per_ref = [], {}
    for _, row in ranked:
        ref = (row["kind"], row["ref"])
        if per_ref.get(ref, 0) >= 2:
            continue
        per_ref[ref] = per_ref.get(ref, 0) + 1
        sources.append(row)
        if len(sources) == 8:
            break
    return sources


def _navigation(answer, path="", label=""):
    return {
        "answer": answer,
        "products": [],
        "sources": [],
        "mode": "guidance",
        "actions": [{"path": path, "label": label}] if path else [],
        "checked_at": timezone.now().isoformat(),
    }


def customer_wording(text):
    # Remove presentation notes only, after validating the original provider output.
    # VNPay test-environment information and substantive policy terms stay intact.
    text = re.sub(r"\([^()\n]*(?:mô phỏng|đồ án)[^()\n]*\)", "", text, flags=re.I)
    sentences = re.split(r"(?<=[.!?])\s+|\n", text.strip())
    sentences = [
        sentence
        for sentence in sentences
        if not (
            normalize(sentence).startswith(("day la ", "luu y: day la "))
            and any(label in normalize(sentence) for label in ("mo phong", "do an"))
        )
    ]
    return re.sub(r"\s+([,.;:!?])", r"\1", re.sub(r"\s+", " ", " ".join(sentences))).strip()


def _product_cards(variants, filters):
    cards = []
    for variant in variants:
        balances = variant.balances.select_related("warehouse__store").filter(
            warehouse__is_active=True,
            warehouse__store__is_active=True,
        )
        if filters["stores"]:
            balances = balances.filter(warehouse__store_id__in=filters["stores"])
        stock_by_store = {}
        for balance in balances:
            store = balance.warehouse.store
            stock = stock_by_store.setdefault(store.pk, {"store_name": store.name, "available": 0})
            stock["available"] += balance.available
        cards.append(
            {
                "id": variant.pk,
                "name": variant.product.name,
                "sku": variant.sku,
                "path": "/products/" + variant.product.slug,
                "image": next((image.url for image in variant.product.images.all()), ""),
                "price": str(variant.price),
                "condition": variant.condition,
                "warranty_months": variant.warranty_months,
                "stock": list(stock_by_store.values()),
            }
        )
    return cards


def _catalog_fallback(filters, question, product_slug, policy_only, code):
    notice = (
        "Dịch vụ AI đang tạm hết hạn mức. "
        if code == "AI_QUOTA_EXCEEDED"
        else "Dịch vụ AI đang tạm gián đoạn. "
    )
    result = _navigation(notice, "/products", "Xem danh mục sản phẩm")
    # This mode retains the customer's question for a budget/branch follow-up.
    # No generated advice or RAG citations are claimed while the provider is down.
    result["mode"] = "catalog"
    if policy_only:
        result["answer"] += "Tôi chưa thể trả lời câu hỏi chính sách lúc này. Vui lòng thử lại sau."
        return result
    if not (filters["category"] or filters["brands"] or product_slug):
        result["answer"] += (
            "Bạn muốn tìm laptop, máy tính để bàn hay thiết bị nào, và ngân sách bao nhiêu? "
            "Tôi vẫn có thể lọc sản phẩm từ danh mục theo loại máy, hãng, giá và chi nhánh."
        )
        return result
    variants = eligible(filters, product_slug)
    if re.search(r"\bgaming\b", normalize(question)):
        variants = variants.filter(product__name__icontains="gaming")
    # Return at most three distinct products; never promote inactive or over-budget items.
    selected, seen = [], set()
    for variant in variants:
        if variant.product_id not in seen:
            selected.append(variant)
            seen.add(variant.product_id)
        if len(selected) == 3:
            break
    if not selected:
        result["answer"] += (
            "Chưa tìm thấy sản phẩm theo các điều kiện lọc đã nhận diện. "
            "Bạn có thể đổi ngân sách, hãng hoặc chi nhánh để tìm lại."
        )
        return result
    result["products"] = _product_cards(selected, filters)
    result["answer"] += (
        "Dưới đây là kết quả lọc cơ bản từ danh mục, sắp theo giá tăng dần. "
        "Đây chưa phải đánh giá mức phù hợp với nhu cầu sử dụng."
    )
    if filters["min"] is None and filters["max"] is None:
        result["answer"] += " Bạn dự kiến ngân sách bao nhiêu để tôi lọc tiếp?"
    return result


def consult(question, history=None, product_slug=""):
    if not ready():
        raise BusinessError("Chức năng tư vấn AI chưa được bật.", "AI_NOT_CONFIGURED", 503)
    q = normalize(question)
    if re.search(r"\btr[a-z0-9]{8,}\b", q) or any(
        token in q
        for token in ["don hang cua toi", "tra cuu don", "kiem tra don", "ma don", "don cua toi"]
    ):
        return _navigation(
            "Bạn hãy mở Đơn hàng của tôi để xem trạng thái bằng tài khoản đã đặt đơn. "
            "Tôi không truy cập dữ liệu đơn hàng cá nhân trong cuộc trò chuyện.",
            "/orders",
            "Đơn hàng của tôi",
        )
    if any(
        token in q
        for token in ["mat khau", "password", "api key", "otp", "so tai khoan", "so the ngan hang"]
    ):
        return _navigation(
            "Bạn không cần gửi mật khẩu, API key, OTP hay thông tin ngân hàng cho chatbot. "
            "Hãy dùng trang Tài khoản để quản lý bảo mật.",
            "/profile",
            "Tài khoản",
        )
    question = redact(question)
    # Follow-ups retain only recent user questions, never client-provided assistant answers.
    followup = re.match(
        r"^(con |vay |so sanh |cai nao|mau nao|loai nao|co mau|re hon|tot hon|"
        r"(?:duoi|tren|tu|tam|khoang|ngan sach|toi da)\s+\d)",
        q,
    )
    history_questions = (
        [
            redact(item["question"])
            for item in (history or [])[-3:]
            if not any(
                token in normalize(item["question"])
                for token in [
                    "mat khau",
                    "password",
                    "api key",
                    "otp",
                    "tai khoan",
                    "don hang",
                    "ma don",
                ]
            )
            and not re.search(r"\btr[a-z0-9]{8,}\b", normalize(item["question"]))
        ]
        if followup
        else []
    )
    search_question = "\n".join(history_questions + [question])[-4000:]
    filters = criteria(search_question)
    current_filters = criteria(question)
    if followup:
        if current_filters["min"] is not None or current_filters["max"] is not None:
            for field in ("min", "max", "strict_max"):
                filters[field] = current_filters[field]
        if current_filters["category"]:
            filters["category"] = current_filters["category"]
        if current_filters["stores"]:
            filters["stores"] = current_filters["stores"]
        if current_filters["brands"]:
            filters["brands"] = current_filters["brands"]
    if product_slug and current_filters["category"]:
        context_category = (
            Product.objects.filter(slug=product_slug, is_active=True)
            .values_list("category_id", flat=True)
            .first()
        )
        if context_category != current_filters["category"]:
            product_slug = ""
    variants = list(eligible(filters, product_slug))
    policy_only = (
        not product_slug
        and not filters["category"]
        and any(
            token in q
            for token in [
                "bao hanh",
                "doi tra",
                "doi loi",
                "thanh toan",
                "vnpay",
                "dat hang",
                "ma giam",
                "voucher",
                "tra gop",
                "giao hang",
            ]
        )
    )
    pause_key = f"ai:provider-pause:{settings.GEMINI_MODEL}:{settings.GEMINI_EMBEDDING_MODEL}"

    def fallback(error):
        if error.detail.code not in ("AI_PROVIDER_UNAVAILABLE", "AI_QUOTA_EXCEEDED"):
            raise error
        cache.set(pause_key, error.detail.code, timeout=30)
        return _catalog_fallback(
            filters, search_question, product_slug, policy_only, error.detail.code
        )

    paused = cache.get(pause_key)
    if paused:
        return _catalog_fallback(filters, search_question, product_slug, policy_only, paused)
    provider = GeminiProvider()
    try:
        rows, _ = sync_index(documents(), provider)
        query_vector = provider.embed([search_question], query=True)[0]
    except BusinessError as error:
        return fallback(error)
    sources = ranked_sources(
        rows,
        query_vector,
        search_question,
        {v.product_id for v in variants},
        policy_only=policy_only,
    )
    source_products = {s["ref"] for s in sources if s["kind"] == "product"}
    candidates = [v for v in variants if v.product_id in source_products][:12]
    if not sources:
        return _navigation(
            "Tôi chưa tìm thấy thông tin phù hợp. Bạn có thể nêu loại sản phẩm, "
            "ngân sách và nhu cầu sử dụng để tôi tìm lại.",
            "/products",
            "Xem sản phẩm",
        )
    context = {
        "sources": [{k: s[k] for k in ("id", "title", "text")} for s in sources],
        "variants": [
            {
                "id": v.pk,
                "product_name": v.product.name,
                "sku": v.sku,
                "condition": v.condition,
                "warranty_months": v.warranty_months,
            }
            for v in candidates
        ],
        "constraints": {
            "budget_applied": filters["min"] is not None or filters["max"] is not None,
            "branch_applied": bool(filters["stores"]),
            "brand_applied": bool(filters["brands"]),
            "branch_names": list(
                Store.objects.filter(pk__in=filters["stores"]).values_list("name", flat=True)
            ),
            "price_and_stock_rendered_by_backend": True,
            "no_matching_products": not candidates,
        },
    }
    try:
        answer = provider.consult(search_question, context)
    except BusinessError as error:
        return fallback(error)
    allowed_variants = {v.pk: v for v in candidates}
    allowed_sources = {s["id"]: s for s in sources}
    invalid = not isinstance(answer, dict)
    if not invalid:
        text, ids, source_ids = (
            answer.get("answer"),
            answer.get("variant_ids"),
            answer.get("source_ids"),
        )
        invalid = (
            not isinstance(text, str)
            or not text.strip()
            or len(text) > 6000
            or not isinstance(ids, list)
            or len(ids) > 3
            or any(type(ident) is not int or ident not in allowed_variants for ident in ids)
            or not isinstance(source_ids, list)
            or len(source_ids) > 8
            or any(
                not isinstance(ident, str) or ident not in allowed_sources for ident in source_ids
            )
        )
        if not invalid:
            # Monetary prose is removed for validated product recommendations below.
            # A model repeating the customer's budget must not discard valid cards.
            money = re.compile(r"₫|\d[\d.,]*\s*(?:triệu|trieu|tr|VND|đồng|dong|đ)\b", re.I)
            invalid = bool(re.search(r"https?://|<[^>]+>", text, re.I)) or bool(
                not ids and money.search(text)
            )
            cited_products = {
                allowed_sources[s]["ref"]
                for s in source_ids
                if allowed_sources[s]["kind"] == "product"
            }
            invalid = invalid or bool(
                ids and any(allowed_variants[i].product_id not in cited_products for i in ids)
            )
            insufficient = any(
                phrase in normalize(text)
                for phrase in [
                    "chua co",
                    "chua tim",
                    "khong co thong tin",
                    "can them",
                    "cho biet",
                    "ngoai pham vi",
                ]
            )
            invalid = invalid or bool(
                not source_ids and (ids or not insufficient or len(text) > 600)
            )
    if invalid:
        raise BusinessError(
            "Chưa xác minh được nội dung tư vấn. Vui lòng hỏi lại cụ thể hơn.",
            "AI_INVALID_RESPONSE",
            503,
        )
    text = customer_wording(text)
    if ids:
        # The model never owns monetary or live inventory claims. Keep those in
        # server-rendered cards, including when the model repeats the user's budget.
        # Validate IDs, citations and unsafe markup before dropping any sentences.
        sentences = re.split(r"(?<=[.!?])\s+|\n", text.strip())
        text = " ".join(
            sentence
            for sentence in sentences
            if not money.search(sentence)
            and not any(
                phrase in normalize(sentence)
                for phrase in [
                    "ton kho",
                    "con hang",
                    "het hang",
                    "gia ban",
                    "gia va",
                    "tinh trang hang",
                ]
            )
        ).strip()
        if not text:
            text = "Bạn có thể tham khảo các sản phẩm dưới đây và xem thông tin hiện tại trong từng thẻ."
        text = re.sub(r"^(?:Tuy nhiên|Tuy vậy|Nhưng)[,:]?\s*", "", text, flags=re.I)
        text = text[:1].upper() + text[1:]
    elif not text:
        text = "Bạn có thể xem nội dung chi tiết trong nguồn tham khảo bên dưới."
    # Re-query after generation: price/stock/visibility can change while waiting for the provider.
    fresh = {v.pk: v for v in eligible(filters, product_slug).filter(pk__in=ids)}
    if any(ident not in fresh for ident in ids):
        raise BusinessError(
            "Dữ liệu sản phẩm vừa thay đổi. Vui lòng hỏi lại để cập nhật.",
            "AI_CONTEXT_CHANGED",
            503,
        )
    return {
        "answer": text.strip(),
        "products": _product_cards([fresh[i] for i in dict.fromkeys(ids)], filters),
        "mode": "rag",
        "actions": [],
        "sources": [
            {"id": s, "title": allowed_sources[s]["title"], "excerpt": allowed_sources[s]["text"]}
            for s in dict.fromkeys(source_ids)
        ],
        "checked_at": timezone.now().isoformat(),
    }
