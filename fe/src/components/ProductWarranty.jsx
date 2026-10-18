import React, { useEffect, useId, useRef, useState } from "react";
import { ShieldCheck, X } from "lucide-react";
import { createPortal } from "react-dom";
import { productWarranty, WARRANTY_DEMO } from "../../../shared/warranty";

export default function ProductWarranty({ product, variant }) {
  const [open, setOpen] = useState(false);
  const dialogRef = useRef(null);
  const titleId = useId();
  const policy = productWarranty(product, variant);
  useEffect(() => {
    if (!open) return;
    const dialog = dialogRef.current;
    const overflow = document.body.style.overflow;
    dialog.showModal();
    document.body.style.overflow = "hidden";
    return () => {
      if (dialog.open) dialog.close();
      document.body.style.overflow = overflow;
    };
  }, [open]);
  if (!variant) return null;
  return (
    <>
      <div className="product-warranty">
        <span className="warranty-icon" aria-hidden="true">
          <ShieldCheck size={23} />
        </span>
        <p>
          {policy.summary}{" "}
          <button
            type="button"
            className="warranty-detail-link"
            aria-haspopup="dialog"
            onClick={() => setOpen(true)}
          >
            Xem chi tiết
          </button>
        </p>
      </div>
      {createPortal(
        <dialog
          ref={dialogRef}
          className="warranty-dialog"
          aria-labelledby={titleId}
          onClose={() => setOpen(false)}
          onCancel={() => setOpen(false)}
          onClick={(event) => {
            if (event.target === event.currentTarget) {
              const bounds = event.currentTarget.getBoundingClientRect();
              if (
                event.clientX < bounds.left ||
                event.clientX > bounds.right ||
                event.clientY < bounds.top ||
                event.clientY > bounds.bottom
              )
                setOpen(false);
            }
          }}
        >
          <header className="warranty-dialog-header">
            <div>
              <span className="eyebrow">TECH RETAIL</span>
              <h2 id={titleId}>Chính sách bảo hành</h2>
            </div>
            <button
              type="button"
              aria-label="Đóng chính sách bảo hành"
              onClick={() => setOpen(false)}
              autoFocus
            >
              <X size={22} />
            </button>
          </header>
          <div className="warranty-dialog-body">
            <div className="warranty-product-summary">
              <strong>{product.name}</strong>
              <p>
                SKU: {variant.sku} · {variant.condition}
              </p>
              <b>{policy.summary}</b>
            </div>
            <p className="warranty-demo-note">
              Chính sách và điểm tiếp nhận được mô phỏng cho đồ án tốt nghiệp.
            </p>
            {policy.months > 0 ? (
              <>
                <section>
                  <h3>1. Thời hạn và đơn vị bảo hành</h3>
                  <p>
                    Thân máy được bảo hành{" "}
                    <strong>
                      {policy.months} tháng {policy.provider}
                    </strong>
                    , tính từ ngày khách nhận hàng hoặc nhận máy tại quầy. Thời
                    hạn đi theo sản phẩm, không tính lại khi chuyển cơ sở tiếp
                    nhận.
                  </p>
                  <p>
                    {policy.isNew
                      ? "Tech Retail tiếp nhận và phối hợp với hãng xử lý bảo hành. Trong mô hình đồ án, thời hạn công bố được bảo đảm đủ kể từ ngày bàn giao."
                      : "Tech Retail chịu trách nhiệm bảo hành trong thời hạn công bố cho hàng cũ, đã kích hoạt và hàng đổi bảo hành. Thời hạn này không được hiểu là thời gian bảo hành hãng còn lại."}
                  </p>
                  <p>
                    {policy.hasBattery && (
                      <>
                        Pin tích hợp (nếu có):{" "}
                        <strong>{policy.batteryMonths} tháng</strong>;{" "}
                      </>
                    )}
                    Sạc, cáp và phụ kiện trong bộ bán:{" "}
                    <strong>{policy.accessoryMonths} tháng</strong> đối với lỗi
                    kỹ thuật. Phụ kiện mua riêng áp dụng thời hạn trên trang của
                    phụ kiện đó.
                  </p>
                </section>
                <section>
                  <h3>2. Phạm vi bảo hành — {policy.category}</h3>
                  <p>{policy.coverage}</p>
                  <p>
                    Bảo hành miễn phí gồm kiểm tra, công sửa và linh kiện cần
                    thay cho lỗi thuộc phạm vi bảo hành. Hao mòn tự nhiên của{" "}
                    {policy.consumables} không thuộc phạm vi thay miễn phí; lỗi
                    kỹ thuật được đánh giá riêng.
                  </p>
                </section>
                <section>
                  <h3>3. Đổi sản phẩm bị lỗi</h3>
                  <p>
                    Trong <strong>30 ngày từ khi nhận hàng</strong>, nếu xác
                    nhận lỗi phần cứng thuộc phạm vi bảo hành, khách được đổi
                    sản phẩm cùng mẫu, cấu hình và tình trạng tương đương, không
                    thu phí đổi lỗi.
                  </p>
                  <p>
                    Nếu hết sản phẩm phù hợp, khách được chọn chờ hàng, đổi mẫu
                    khác và thanh toán/nhận lại chênh lệch, hoặc hoàn số tiền
                    thực trả của sản phẩm sau khi thu hồi hàng. Ghi nhận đầy đủ
                    máy, phụ kiện và quà tặng khi đổi/hoàn; thống nhất cách xử
                    lý nếu thiếu.
                  </p>
                  <p>
                    Sau 30 ngày, ưu tiên sửa chữa hoặc thay linh kiện miễn phí
                    trong thời hạn bảo hành. Chính sách này không áp dụng đổi vì
                    thay đổi nhu cầu khi sản phẩm không lỗi.
                  </p>
                </section>
              </>
            ) : (
              <section>
                <h3>Thông tin thời hạn</h3>
                <p>
                  {policy.months === 0
                    ? "Biến thể này có thời hạn bảo hành bằng 0 tháng. Không áp dụng quyền lợi bảo hành miễn phí hoặc đổi lỗi theo gói bảo hành; cửa hàng vẫn hỗ trợ kiểm tra và báo giá sửa chữa."
                    : "Biến thể này chưa có thời hạn bảo hành. Vui lòng xác nhận với cơ sở tiếp nhận trước khi mua; không áp dụng mặc định một thời hạn khác."}
                </p>
              </section>
            )}
            <section>
              <h3>4. Điều kiện tiếp nhận</h3>
              <p>
                Cung cấp mã đơn hàng hoặc thông tin mua hàng để đối chiếu; không
                bắt buộc hóa đơn giấy nếu đã tra được giao dịch. Thiết bị có
                serial/IMEI được ghi nhận khi bàn giao và khi tiếp nhận.
              </p>
              <p>
                Vết xước hoặc khuyết điểm đã ghi nhận lúc bán không tự làm mất
                quyền bảo hành lỗi chức năng khác. Hư hỏng do va đập, chất lỏng,
                nguồn điện sai hoặc sửa chữa gây ra lỗi được kiểm tra và giải
                thích trước khi đề xuất dịch vụ có phí.
              </p>
              <p>
                Khách nên sao lưu dữ liệu, tháo SIM/thẻ nhớ và tự xử lý khóa tài
                khoản khi cần. Nhân viên không yêu cầu mật khẩu tài khoản cá
                nhân; chỉ khôi phục hoặc xóa dữ liệu sau khi được đồng ý.
              </p>
            </section>
            <section>
              <h3>5. Tiếp nhận và thời gian xử lý</h3>
              <ol>
                <li>
                  Mang sản phẩm tới quầy dịch vụ, cung cấp thông tin mua hàng và
                  mô tả lỗi.
                </li>
                <li>
                  Nhân viên lập phiếu, ghi nhận ngoại hình, serial/IMEI, phụ
                  kiện và cấp mã tiếp nhận.
                </li>
                <li>
                  Kiểm tra và phản hồi: {WARRANTY_DEMO.response.toLowerCase()}.
                </li>
                <li>{WARRANTY_DEMO.repair}</li>
                <li>
                  Bàn giao kết quả, linh kiện đã thay và thời hạn còn lại. Sửa
                  hoặc đổi lỗi không làm giảm thời hạn bảo hành ban đầu.
                </li>
              </ol>
              <p>
                Hết hạn hoặc ngoài phạm vi miễn phí: chỉ sửa sau khi khách đồng
                ý báo giá. Thời gian sửa có phí được ghi trên phiếu tiếp nhận.
              </p>
            </section>
            <section>
              <h3>6. Vận chuyển và tiếp nhận tại cơ sở</h3>
              <p>
                Miễn phí vận chuyển hai chiều khi xác nhận lỗi thuộc phạm vi bảo
                hành. Ngoài phạm vi này, báo phí thực tế và xin đồng ý trước khi
                gửi. Khách có thể tiếp nhận tại bất kỳ quầy dịch vụ nào trong hệ
                thống.
              </p>
              <ul>
                {WARRANTY_DEMO.locations.map((location) => (
                  <li key={location}>{location}</li>
                ))}
              </ul>
              <p>
                Giờ tiếp nhận: <strong>{WARRANTY_DEMO.hours}</strong>. Cung cấp
                mã đơn hàng tại quầy để được hỗ trợ.
              </p>
            </section>
            <section>
              <h3>7. Sau sửa chữa và bảo hành mở rộng</h3>
              <p>
                Với sản phẩm có bảo hành, linh kiện thay thế được bảo hành trong
                thời gian còn lại hoặc 3 tháng từ ngày trả máy, tùy thời gian
                nào dài hơn. Thiết bị đổi lỗi tiếp tục thời hạn ban đầu.
              </p>
              <p>
                Chưa cung cấp gói bảo hành mở rộng có phí. Tình trạng “Đổi bảo
                hành” của sản phẩm không phải gói bảo hành mở rộng.
              </p>
            </section>
            <section>
              <h3>8. Thông tin áp dụng</h3>
              <p>
                Phiên bản <strong>{WARRANTY_DEMO.version}</strong> · Hiệu lực từ{" "}
                <strong>{WARRANTY_DEMO.effectiveDate}</strong>. Số tháng thân
                máy lấy theo biến thể đang chọn; thời hạn pin và phụ kiện không
                vượt quá thời hạn thân máy. Thông tin bảo hành được xác nhận
                trên phiếu mua hàng và phiếu tiếp nhận trong mô hình đồ án.
              </p>
            </section>
          </div>
        </dialog>,
        document.body,
      )}
    </>
  );
}
