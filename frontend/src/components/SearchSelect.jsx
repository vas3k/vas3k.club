import { useRef } from "react";
import { Combobox, ComboboxButton, ComboboxInput, ComboboxOptions, ComboboxOption } from "@headlessui/react";
import "../../static/css/components/search-select.css";

export default function SearchSelect({
    id,
    name,
    label,
    placeholder,
    selected,
    onChange,
    items,
    query,
    onQueryChange,
    multiple = false,
    maxItems = 10,
    hint = "",
    error = "",
    loading = false,
    className = "",
}) {
    const input = useRef(null);
    const trigger = useRef(null);
    const values = multiple ? selected : selected ? [selected] : [];
    const full = multiple && values.length >= maxItems;

    return (
        <div className={`search-select ${className}`}>
            <input type="hidden" name={name} value={values.map((item) => item.value).join(",")} />
            <Combobox
                value={selected}
                by="value"
                multiple={multiple}
                immediate
                onChange={(value) => {
                    onChange(value);
                    onQueryChange("");
                }}
                onClose={() => onQueryChange("")}
            >
                {({ open }) => (
                    <>
                        {multiple && (
                            <div className="search-select-values">
                                {values.map((item) => (
                                    <span className="search-select-chip" key={item.value}>
                                        {item.image && <img src={item.image} alt="" />}
                                        <span title={item.label}>{item.label}</span>
                                        <button
                                            type="button"
                                            aria-label={`Убрать ${item.label}`}
                                            onClick={() => {
                                                onChange(values.filter((value) => value.value !== item.value));
                                                input.current?.focus();
                                            }}
                                        >
                                            ×
                                        </button>
                                    </span>
                                ))}
                            </div>
                        )}
                        <ComboboxButton ref={trigger} hidden aria-hidden="true" />
                        <div className="search-select-control">
                            <div
                                className={`search-select-entry${!multiple && selected?.image && !open ? " search-select-image-selected" : ""}`}
                            >
                                {!multiple && selected?.image && !open && (
                                    <span className="search-select-selected" aria-hidden="true">
                                        <img className="search-select-avatar" src={selected.image} alt="" />
                                        <span>{selected.label}</span>
                                    </span>
                                )}
                                <ComboboxInput
                                    ref={input}
                                    id={id}
                                    type="text"
                                    aria-label={label}
                                    aria-describedby={hint || error ? `${id}-hint` : undefined}
                                    autoComplete="off"
                                    autoCapitalize="none"
                                    spellCheck={false}
                                    placeholder={full ? "Добавлено 10 соавторов" : placeholder}
                                    value={open ? query : multiple ? "" : selected?.label || ""}
                                    onChange={(event) => onQueryChange(event.target.value)}
                                    onClick={() => {
                                        if (!open) trigger.current?.click();
                                    }}
                                    onKeyDown={(event) => {
                                        if (event.key === "Enter" && !open && !event.nativeEvent.isComposing)
                                            event.preventDefault();
                                    }}
                                />
                                {!multiple && selected && (
                                    <button
                                        type="button"
                                        className="search-select-clear"
                                        aria-label={`Очистить: ${label}`}
                                        onClick={() => {
                                            onChange(null);
                                            onQueryChange("");
                                            input.current?.focus();
                                        }}
                                    >
                                        ×
                                    </button>
                                )}
                                {loading && <span className="search-select-loading" role="status" aria-label="Ищем…" />}
                            </div>
                        </div>
                        <ComboboxOptions
                            className={`search-select-options${!items.length && (hint || loading || error) ? " search-select-options-empty" : ""}`}
                            modal={false}
                            aria-busy={loading}
                        >
                            {items.map((item) => (
                                <ComboboxOption
                                    key={item.value}
                                    value={item}
                                    disabled={full && !values.some((value) => value.value === item.value)}
                                    className="search-select-option"
                                >
                                    {item.emoji && (
                                        <span className="search-select-icon" aria-hidden="true">
                                            {item.emoji}
                                        </span>
                                    )}
                                    {!item.emoji && item.image && (
                                        <img className="search-select-avatar" src={item.image} alt="" loading="lazy" />
                                    )}
                                    <span className="search-select-option-text">
                                        {item.create ? `Создать «${item.label}»` : item.label}
                                        {item.detail && <small>{item.detail}</small>}
                                    </span>
                                    <span className="search-select-check" aria-hidden="true">
                                        ✓
                                    </span>
                                </ComboboxOption>
                            ))}
                            {!items.length && !hint && !loading && !error && (
                                <div className="search-select-empty">Ничего не найдено</div>
                            )}
                        </ComboboxOptions>
                    </>
                )}
            </Combobox>
            {(hint || error) && (
                <div id={`${id}-hint`} className="search-select-hint" role={error ? "alert" : undefined}>
                    {error || hint}
                </div>
            )}
        </div>
    );
}
