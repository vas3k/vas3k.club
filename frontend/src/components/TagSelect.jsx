import { useEffect, useState } from "react";
import ClubApi from "../lib/api.service";
import SearchSelect from "./SearchSelect";

export default function TagSelect({ id, initialValue = "", searchUrl }) {
    const [selected, setSelected] = useState(() =>
        initialValue ? { value: initialValue, label: initialValue } : null,
    );
    const [query, setQuery] = useState("");
    const [results, setResults] = useState({ query: "", items: [] });
    const [error, setError] = useState("");
    const [loading, setLoading] = useState(false);
    const text = query.trim();
    const [emoji, ...words] = text.split(" ");
    const first = [...new Intl.Segmenter(undefined, { granularity: "grapheme" }).segment(emoji || "")];
    const valid =
        first.length === 1 &&
        /[\p{Extended_Pictographic}\p{Regional_Indicator}\u20e3]/u.test(emoji) &&
        words.join(" ").trim() &&
        [...text].length <= 32;
    const items = results.query === query ? results.items : [];
    const options =
        valid && !items.some((item) => item.value === text)
            ? [...items, { value: text, label: text, create: true }]
            : items;

    useEffect(() => {
        let disposed = false;
        setError("");
        setLoading(text.length >= 3);
        if (text.length < 3) return;
        const timer = setTimeout(async () => {
            try {
                const data = await ClubApi.get(`${searchUrl}${encodeURIComponent([...text].slice(0, 15).join(""))}`);
                if (!disposed)
                    setResults({
                        query,
                        items: (data.tags || []).map((tag) => ({ value: tag.name, label: tag.name })),
                    });
            } catch (failure) {
                if (!disposed) setError(failure.message);
            } finally {
                if (!disposed) setLoading(false);
            }
        }, 250);
        return () => {
            disposed = true;
            clearTimeout(timer);
        };
    }, [query, text, searchUrl]);

    return (
        <SearchSelect
            id={`id_${id}`}
            name={id}
            label="Коллекционный тег"
            placeholder="Найти тег или ввести 🎉 Новый тег"
            selected={selected}
            onChange={setSelected}
            items={options}
            query={query}
            onQueryChange={setQuery}
            hint={
                text && !valid
                    ? "Для нового тега: emoji, пробел и название. Не больше 32 символов."
                    : text.length < 3
                      ? "Введите минимум 3 символа для поиска"
                      : ""
            }
            error={error}
            loading={loading}
        />
    );
}
