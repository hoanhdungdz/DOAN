# Tích hợp để sau

Google, Facebook, Gemini: **DEFERRED**. Flags mặc định false, không gọi dịch vụ, không SDK bắt buộc, không key/session/tư vấn giả. Bật flag hiện tại báo cấu hình chưa triển khai thay vì giả thành công.

Google cần client ID, callback/redirect và secret nếu flow cần. Facebook cần app ID/secret/redirect. Dự kiến Authorization Code backend, state/nonce và PKCE theo provider; xác minh token issuer/audience/signature/expiry ở backend. SocialIdentity unique(provider, subject). Không auto-link theo email trùng; yêu cầu user xác thực tài khoản hiện hữu trước khi liên kết.

Gemini cần key và model còn hỗ trợ tại thời điểm tích hợp. Luồng: validate câu hỏi/context giới hạn -> retrieval DB top candidates -> provider -> validate schema, candidate IDs và structured claims -> render giá/thông số/tồn từ DB. Không gửi PII, không SQL/tool actions từ model, không lưu lịch sử chat. Interface hiện tại chỉ disabled; kiểm thử nó không chứng minh Gemini chạy thật.

Email local dùng console backend, reset token chỉ trong thư mô phỏng ở terminal; production bắt buộc SMTP thật, TLS, from-address. SMS local ghi development inbox bên ngoài webroot được bảo vệ bằng quyền filesystem; OTP không trả API hoặc log production. Cần SMS provider adapter/key trước khi delivery production. Chưa kiểm thử gửi email/SMS thật. Production từ chối debug/development delivery.
