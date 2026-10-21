import { useEffect, useId, useState } from "react";
import ClubApi from "../lib/api.service";
import "../../static/css/components/search-select.css";

export default function TagSelect({
    id,
    initialValue = "",
    allowCreateNew = false,
    allowMultiple = false,
    validationRegExp,
    searchUrl,
    labelPrefixInput = "",
    labelInvalidInput,
    labelValidInput,
}) {
    const listId = useId();
    const [selected, setSelected] = useState(() =>
        initialValue ? (allowMultiple ? initialValue.split(",") : [initialValue]) : [],
    );
    const [query, setQuery] = useState("");
    const [options, setOptions] = useState([]);
    const [error, setError] = useState("");
    const valid = query.trim() && (!validationRegExp || new RegExp(validationRegExp).test(query));

    useEffect(() => {
        let disposed = false;
        setOptions([]);
        setError("");
        if (query.length < 3) return;
        const timer = setTimeout(async () => {
            try {
                const data = await ClubApi.get(`${searchUrl}${encodeURIComponent(query)}`);
                if (!disposed) setOptions((data.tags || []).map((tag) => tag.name));
            } catch (failure) {
                if (!disposed) setError(failure.message);
            }
        }, 300);
        return () => {
            disposed = true;
            clearTimeout(timer);
        };
    }, [query, searchUrl]);

    function choose(value) {
        if (!value.trim() || (!options.includes(value) && !(allowCreateNew && valid))) return;
        setSelected((values) => (allowMultiple ? [...new Set([...values, value])] : [value]));
        setQuery("");
        setOptions([]);
    }

    return (
        <div className="search-select">
            <input type="hidden" name={id} value={selected.join(",")} />
            <div className="search-select-values">
                {selected.map((value) => (
                    <button
                        key={value}
                        type="button"
                        className="button button-small"
                        aria-label={`Убрать ${value}`}
                        onClick={() => setSelected(selected.filter((item) => item !== value))}
                    >
                        {value} ×
                    </button>
                ))}
            </div>
            <input
                type="text"
                id={`id_${id}`}
                list={listId}
                value={query}
                autoComplete="off"
                placeholder="Найти или добавить тег"
                onChange={(event) => {
                    const value = event.target.value;
                    setQuery(value);
                    if (options.includes(value)) choose(value);
                }}
                onKeyDown={(event) => {
                    if (event.key === "Enter" && !event.nativeEvent.isComposing) {
                        event.preventDefault();
                        choose(query);
                    }
                }}
            />
            <datalist id={listId}>
                {options.map((value) => (
                    <option key={value} value={value} />
                ))}
            </datalist>
            {query && allowCreateNew && (
                <>
                    <span className="form-row-help">{valid ? labelValidInput : labelInvalidInput}</span>
                    <button
                        type="button"
                        className="button button-small"
                        disabled={!valid}
                        onClick={() => choose(query)}
                    >
                        {labelPrefixInput}
                        {query}
                    </button>
                </>
            )}
            {error && <span role="alert">{error}</span>}
        </div>
    );
}
