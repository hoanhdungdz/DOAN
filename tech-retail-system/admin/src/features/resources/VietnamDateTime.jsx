import React, { useEffect, useState } from "react";

function parts(value) {
  const [date = "", time = "00:00"] = String(value || "").split("T");
  const [hour, minute] = time.split(":");
  return { date, hour, minute };
}
export default function VietnamDateTime({ label, value, onChange, required }) {
  const [draft, setDraft] = useState(() => parts(value));
  useEffect(() => setDraft(parts(value)), [value]);
  function update(key, value) {
    const next = { ...draft, [key]: value };
    setDraft(next);
    onChange(next.date ? `${next.date}T${next.hour}:${next.minute}` : "");
  }
  return (
    <div className="voucher-date-time">
      <div className="voucher-date-controls">
        <input
          type="date"
          aria-label={`Ngày ${label.toLowerCase()}`}
          required={required}
          value={draft.date}
          onChange={(e) => update("date", e.target.value)}
        />
        <select
          aria-label={`Giờ ${label.toLowerCase()}`}
          value={draft.hour}
          onChange={(e) => update("hour", e.target.value)}
        >
          {Array.from({ length: 24 }, (_, hour) => (
            <option key={hour} value={String(hour).padStart(2, "0")}>
              {String(hour).padStart(2, "0")}
            </option>
          ))}
        </select>
        <span aria-hidden="true">:</span>
        <select
          aria-label={`Phút ${label.toLowerCase()}`}
          value={draft.minute}
          onChange={(e) => update("minute", e.target.value)}
        >
          {Array.from({ length: 60 }, (_, minute) => (
            <option key={minute} value={String(minute).padStart(2, "0")}>
              {String(minute).padStart(2, "0")}
            </option>
          ))}
        </select>
      </div>
      <p className="fine">Giờ Việt Nam (UTC+7) · Định dạng 24 giờ</p>
    </div>
  );
}
