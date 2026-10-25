import React, { useEffect, useId, useRef, useState } from "react";
import { Search, X } from "lucide-react";
import "./SearchSelect.css";

export const searchText = (text) =>
  String(text ?? "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/đ/g, "d")
    .replace(/Đ/g, "D")
    .toLowerCase();

export default function SearchSelect({
  label,
  options = [],
  value = "",
  onChange,
  placeholder = "Nhập tên để tìm…",
  emptyLabel = "Không chọn",
  required = false,
  disabled = false,
}) {
  const id = useId(),
    input = useRef(null);
  const [open, setOpen] = useState(false),
    [query, setQuery] = useState(""),
    [active, setActive] = useState(-1);
  const selected = options.find(
    (option) => String(option.value) === String(value),
  );
  const matches = options.filter((option) =>
    searchText(option.label).includes(searchText(query)),
  );
  const shown = matches.slice(0, 40);
  useEffect(() => {
    input.current?.setCustomValidity(
      required && !selected
        ? "Vui lòng chọn một giá trị trong kết quả tìm kiếm."
        : "",
    );
  }, [selected, required]);
  function choose(option) {
    onChange(String(option.value));
    setQuery("");
    setOpen(false);
    setActive(-1);
  }
  return (
    <div className="search-select">
      <Search size={15} className="search-select-icon" aria-hidden="true" />
      <input
        ref={input}
        role="combobox"
        aria-label={label}
        aria-expanded={open}
        aria-controls={`${id}-results`}
        aria-autocomplete="list"
        aria-activedescendant={
          open && active >= 0 ? `${id}-${active}` : undefined
        }
        required={required}
        disabled={disabled}
        placeholder={selected ? selected.label : placeholder}
        value={open ? query : selected?.label || ""}
        autoComplete="off"
        onFocus={() => {
          setOpen(true);
          setQuery("");
          setActive(-1);
        }}
        onBlur={() => {
          setOpen(false);
          setQuery("");
          setActive(-1);
        }}
        onChange={(event) => {
          setQuery(event.target.value);
          setOpen(true);
          setActive(-1);
          if (value !== "") onChange("");
        }}
        onKeyDown={(event) => {
          if (event.key === "ArrowDown" || event.key === "ArrowUp") {
            event.preventDefault();
            setOpen(true);
            if (!shown.length) {
              setActive(-1);
              return;
            }
            setActive((index) =>
              Math.max(
                0,
                Math.min(
                  shown.length - 1,
                  index + (event.key === "ArrowDown" ? 1 : -1),
                ),
              ),
            );
          }
          if (event.key === "Escape") {
            setOpen(false);
            setQuery("");
            setActive(-1);
          }
          if (event.key === "Enter" && open) {
            event.preventDefault();
            if (active >= 0 && shown[active]) choose(shown[active]);
          }
        }}
      />
      {value !== "" && !disabled && (
        <button
          type="button"
          className="search-select-clear"
          aria-label={`Bỏ chọn ${label.toLowerCase()}`}
          onMouseDown={(event) => event.preventDefault()}
          onClick={() => {
            onChange("");
            setQuery("");
            setActive(-1);
          }}
        >
          <X size={15} />
        </button>
      )}
      {open && !disabled && (
        <div className="search-select-dropdown">
          <ul
            id={`${id}-results`}
            role="listbox"
            aria-label={`Kết quả ${label.toLowerCase()}`}
          >
            {!required && !query && (
              <li
                role="option"
                aria-selected={!value}
                onMouseDown={(event) => event.preventDefault()}
                onClick={() => choose({ value: "" })}
              >
                {emptyLabel}
              </li>
            )}
            {shown.map((option, index) => (
              <li
                key={option.value}
                id={`${id}-${index}`}
                role="option"
                aria-selected={String(option.value) === String(value)}
                className={active === index ? "highlighted" : ""}
                onMouseDown={(event) => event.preventDefault()}
                onClick={() => choose(option)}
              >
                {option.label}
              </li>
            ))}
          </ul>
          {!shown.length && (
            <p role="status">Không tìm thấy kết quả phù hợp.</p>
          )}
          {matches.length > shown.length && (
            <p className="fine">
              Nhập thêm tên để thu hẹp {matches.length} kết quả.
            </p>
          )}
        </div>
      )}
    </div>
  );
}
