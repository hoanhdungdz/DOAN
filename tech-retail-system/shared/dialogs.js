let handler = null;
export function registerDialog(next) {
  handler = next;
  return () => {
    if (handler === next) handler = null;
  };
}
function show(kind, message) {
  return new Promise((resolve) => {
    if (!handler) {
      resolve(kind === "reason" ? null : false);
      return;
    }
    handler({ kind, message, resolve });
  });
}
export const confirmAction = (message) => show("confirm", message);
export const promptReason = (message) => show("reason", message);
