import { useEffect, useState } from "react";
import ClubApi from "../lib/api.service";
import SearchSelect from "./SearchSelect";

export default function CoauthorsSelect({ id, searchUrl, initialUsers = [], initialSlugs = "", excludeSlug = "" }) {
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
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        let disposed = false;
        setOptions([]);
        setError("");
        setLoading(query.trim().length >= 3);
        if (query.trim().length < 3) return;
        const timer = setTimeout(async () => {
            try {
                const data = await ClubApi.get(`${searchUrl}${encodeURIComponent(query.trim())}`);
                if (!disposed) setOptions(data.users || []);
            } catch (failure) {
                if (!disposed) setError(failure.message);
            } finally {
                if (!disposed) setLoading(false);
            }
        }, 300);
        return () => {
            disposed = true;
            clearTimeout(timer);
        };
    }, [query, searchUrl]);

    const items = options
        .filter((user) => user.slug !== excludeSlug && !selected.some((item) => item.slug === user.slug))
        .map((user) => ({ value: user.slug, label: user.full_name, image: user.avatar, detail: `@${user.slug}` }));

    return (
        <SearchSelect
            id={`id_${id}`}
            name={id}
            label="Соавторы"
            placeholder="Найти по имени или нику"
            multiple
            selected={selected.map((user) => ({ value: user.slug, label: user.full_name, image: user.avatar }))}
            onChange={(users) =>
                setSelected(users.map((user) => ({ slug: user.value, full_name: user.label, avatar: user.image })))
            }
            items={items}
            query={query}
            onQueryChange={setQuery}
            hint={
                selected.length >= 10
                    ? "Можно добавить не больше 10 соавторов"
                    : query.length < 3
                      ? "Введите минимум 3 символа для поиска"
                      : ""
            }
            error={error}
            loading={loading}
        />
    );
}
