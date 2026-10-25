export function vietnamLocal(value) {
  if (!value || Number.isNaN(new Date(value).getTime())) return "";
  const parts = Object.fromEntries(
    new Intl.DateTimeFormat("en-GB", {
      timeZone: "Asia/Ho_Chi_Minh",
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      hourCycle: "h23",
    })
      .formatToParts(new Date(value))
      .map((part) => [part.type, part.value]),
  );
  return `${parts.year}-${parts.month}-${parts.day}T${parts.hour}:${parts.minute}`;
}
export function vietnamIso(value) {
  if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/.test(value))
    throw new Error("Vui lòng chọn đủ ngày, giờ và phút.");
  const date = new Date(`${value}:00+07:00`);
  if (Number.isNaN(date.getTime()) || vietnamLocal(date) !== value)
    throw new Error("Ngày hoặc giờ không hợp lệ.");
  return date.toISOString();
}
