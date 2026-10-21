import { useEffect, useId, useState } from "react";
import ClubApi from "../lib/api.service";
import "../../static/css/components/search-select.css";

export default function CoauthorsSelect({ id, searchUrl, initialUsers = [], initialSlugs = "", excludeSlug = "" }) {
    const listId = useId();
    const [selected, setSelected] = useState(() =>
        initialSlugs
            ? initialSlugs
                  .split(",")
                  .map((slug) => slug.trim())
                  .filter(Boolean)
                  .map((slug) => ({ slug, full_name: slug }))
            : initialUsers,
    );
    const [query, setQuery] = useState("");
    const [options, setOptions] = useState([]);
    const [error, setError] = useState("");

    useEffect(() => {
        let disposed = false;
        setOptions([]);
        setError("");
        if (query.length < 3) return;
        const timer = setTimeout(async () => {
            try {
                const data = await ClubApi.get(`${searchUrl}${encodeURIComponent(query.slice(0, 15))}`);
                if (!disposed) setOptions(data.users || []);
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
        const user = options.find((option) => option.slug === value);
        if (
            !user ||
            user.slug === excludeSlug ||
            selected.some((item) => item.slug === user.slug) ||
            selected.length >= 10
        )
            return;
        setSelected((users) => [...users, user]);
        setQuery("");
        setOptions([]);
    }

    return (
        <div className="search-select">
            <input type="hidden" name={id} value={selected.map((user) => user.slug).join(",")} />
            <div className="search-select-values">
                {selected.map((user) => (
                    <button
                        key={user.slug}
                        type="button"
                        className="button button-small"
                        aria-label={`Убрать ${user.full_name}`}
                        onClick={() => setSelected(selected.filter((item) => item.slug !== user.slug))}
                    >
                        {user.full_name} ×
                    </button>
                ))}
            </div>
            <input
                type="text"
                id={`id_${id}`}
                list={listId}
                value={query}
                autoComplete="off"
                autoCapitalize="none"
                spellCheck={false}
                disabled={selected.length >= 10}
                placeholder="Имя или ник, минимум 3 символа"
                onChange={(event) => {
                    setQuery(event.target.value);
                    choose(event.target.value);
                }}
                onKeyDown={(event) => {
                    if (event.key === "Enter" && !event.nativeEvent.isComposing) {
                        event.preventDefault();
                        choose(query);
                    }
                }}
            />
            <datalist id={listId}>
                {options
                    .filter((user) => user.slug !== excludeSlug && !selected.some((item) => item.slug === user.slug))
                    .map((user) => (
                        <option key={user.slug} value={user.slug}>
                            {user.full_name}
                        </option>
                    ))}
            </datalist>
            {error && <span role="alert">{error}</span>}
        </div>
    );
}
