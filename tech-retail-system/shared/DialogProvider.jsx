import React, { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { registerDialog } from "./dialogs";
export default function DialogProvider({ children }) {
  const [dialog, setDialog] = useState(null),
    [value, setValue] = useState(""),
    pending = useRef(null);
  useEffect(() => {
    const unregister = registerDialog((next) => {
      if (pending.current)
        pending.current.resolve(
          pending.current.kind === "reason" ? null : false,
        );
      pending.current = next;
      setValue("");
      setDialog(next);
    });
    return () => {
      unregister();
      pending.current?.resolve(false);
    };
  }, []);
  function finish(result) {
    const current = pending.current;
    pending.current = null;
    setDialog(null);
    current?.resolve(result);
  }
  return (
    <>
      {children}
      {dialog &&
        createPortal(
          <div
            className="modal-backdrop"
            onKeyDown={(e) => {
              if (e.key === "Escape")
                finish(dialog.kind === "reason" ? null : false);
            }}
          >
            <section
              className="modal confirmation-dialog"
              role="dialog"
              aria-modal="true"
              aria-labelledby="confirmation-title"
            >
              <h2 id="confirmation-title">
                {dialog.kind === "reason" ? "Nhập lý do" : "Xác nhận thao tác"}
              </h2>
              <p className="subtle">{dialog.message}</p>
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  finish(dialog.kind === "reason" ? value.trim() : true);
                }}
              >
                {dialog.kind === "reason" && (
                  <label className="field">
                    <span>Lý do</span>
                    <textarea
                      autoFocus
                      required
                      maxLength={500}
                      value={value}
                      onChange={(e) => setValue(e.target.value)}
                    />
                  </label>
                )}
                <div className="actions">
                  <button
                    type="button"
                    autoFocus={dialog.kind !== "reason"}
                    onClick={() =>
                      finish(dialog.kind === "reason" ? null : false)
                    }
                  >
                    Quay lại
                  </button>
                  <button
                    className="button primary"
                    disabled={dialog.kind === "reason" && !value.trim()}
                  >
                    Tiếp tục
                  </button>
                </div>
              </form>
            </section>
          </div>,
          document.body,
        )}
    </>
  );
}
