// Fictional store policy for the graduation-project demo. Never overwrites catalog data.
export const WARRANTY_DEMO = {
  version: "TR-BH-2026.01",
  effectiveDate: "18/10/2026",
  hours: "08:30–20:00 hằng ngày",
  response: "Trong 1 ngày làm việc kể từ khi tiếp nhận",
  repair:
    "Dự kiến 3–7 ngày làm việc; tối đa 15 ngày làm việc. Nếu cần thêm thời gian, Tech Retail thông báo và thống nhất phương án với khách hàng.",
  locations: [
    "Quầy dịch vụ Tech Retail Cầu Giấy — Hà Nội",
    "Quầy dịch vụ Tech Retail Thanh Xuân — Hà Nội",
    "Quầy dịch vụ Tech Retail Hoàng Diệu — Hải Phòng",
  ],
};

const scopes = [
  [
    "laptop",
    "Laptop",
    "Bo mạch, CPU/GPU, RAM, ổ lưu trữ, màn hình, bàn phím tích hợp, hệ thống tản nhiệt và cổng kết nối khi có lỗi kỹ thuật.",
  ],
  [
    "dien thoai",
    "Điện thoại",
    "Bo mạch, nguồn, màn hình/cảm ứng, camera, loa, micro, kết nối và cổng sạc khi có lỗi kỹ thuật.",
  ],
  [
    "may tinh bang",
    "Máy tính bảng",
    "Bo mạch, nguồn, màn hình/cảm ứng, camera, loa, micro và kết nối. Bút hoặc bàn phím mua riêng có chính sách riêng.",
  ],
  [
    "may tinh de ban",
    "Máy tính để bàn / Mac mini",
    "Thân máy, bo mạch, CPU/GPU, RAM, ổ lưu trữ, nguồn và cổng kết nối. Không bao gồm màn hình, bàn phím hoặc chuột mua riêng.",
  ],
  [
    "man hinh",
    "Màn hình PC",
    "Tấm nền, nguồn, bo mạch, cổng tín hiệu và các chức năng tích hợp khi có lỗi kỹ thuật. Trong mô hình đồ án, màn hình có từ 3 điểm sáng hoặc 5 điểm tối được tiếp nhận đánh giá thay tấm nền.",
  ],
  [
    "am thanh",
    "Âm thanh và đồng hồ thông minh",
    "Tai nghe/loa: âm thanh, kết nối, điều khiển và hộp sạc đi kèm. Đồng hồ: màn hình, cảm ứng, nút bấm, cảm biến và sạc khi có lỗi kỹ thuật. Kháng nước không đồng nghĩa mọi hư hỏng do chất lỏng đều được bảo hành.",
  ],
  [
    "gia dung",
    "Gia dụng và Smarthome",
    "Tivi: tấm nền, nguồn, bo mạch và âm thanh. Robot hút bụi: động cơ, cảm biến, bo mạch, sạc và trạm vệ sinh nếu có trong bộ bán. Hỗ trợ kiểm tra tivi tại nhà trong phạm vi 15 km từ điểm tiếp nhận.",
  ],
  [
    "phu kien",
    "Phụ kiện công nghệ",
    "Bàn phím, chuột, sạc và phụ kiện: lỗi phím, bảng mạch, kết nối, nguồn hoặc chức năng theo đúng cấu hình được bán. Không bao gồm hư hỏng do sử dụng nguồn điện hoặc thiết bị không tương thích.",
  ],
];

function normalize(value = "") {
  return value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/đ/gi, "d")
    .toLowerCase()
    .replace(/_/g, " ");
}

export function productWarranty(product, variant) {
  const raw = variant?.warranty_months;
  const months =
    raw !== null &&
    raw !== undefined &&
    raw !== "" &&
    Number.isInteger(Number(raw)) &&
    Number(raw) >= 0
      ? Number(raw)
      : null;
  const isNew = normalize(variant?.condition).startsWith("moi 100%");
  const provider = isNew ? "chính hãng" : "tại Tech Retail";
  const scope = scopes.find(([key]) =>
    normalize(product?.category_name).includes(key),
  );
  const hasBattery =
    ["laptop", "dien thoai", "may tinh bang", "am thanh"].includes(
      scope?.[0],
    ) ||
    (scope?.[0] === "gia dung" && normalize(product?.name).includes("robot")) ||
    (scope?.[0] === "phu kien" &&
      /khong day|magic keyboard/.test(normalize(product?.name)));
  const consumables =
    scope?.[0] === "gia dung"
      ? "chổi, khăn lau, bộ lọc và túi bụi (nếu có)"
      : scope?.[0] === "am thanh"
        ? "pin, đệm tai, nút tai và dây đeo (nếu có)"
        : hasBattery
          ? "pin và các chi tiết hao mòn trong sử dụng"
          : "các chi tiết hao mòn trong sử dụng";
  return {
    months,
    isNew,
    provider,
    hasBattery,
    consumables,
    summary:
      months === null
        ? "Chưa có thời hạn bảo hành."
        : months === 0
          ? "Sản phẩm không áp dụng bảo hành."
          : `Bảo hành ${months} tháng ${provider}.`,
    category: scope?.[1] || product?.category_name || "Thiết bị công nghệ",
    coverage:
      scope?.[2] ||
      "Lỗi kỹ thuật ở phần cứng và các chức năng theo cấu hình đã bán.",
    batteryMonths: months === null ? null : Math.min(months, isNew ? 12 : 6),
    accessoryMonths: months === null ? null : Math.min(months, 6),
  };
}

// Keep scraped marketing copy consistent with the selected variant's duration.
export function warrantyDescription(description, warranty) {
  if (!description || warranty.months === null) return description;
  return description.replace(
    /bảo hành\s+\d+\s*(?:[-–]\s*\d+\s*)?tháng/giu,
    warranty.summary.replace(/\.$/, ""),
  );
}
