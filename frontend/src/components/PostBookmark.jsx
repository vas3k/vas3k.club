import { useState } from "react";
import ClubApi from "../lib/api.service";

export default function PostBookmark({ initialIsBookmarked = false, bookmarkUrl, className = "", removeOnly = false }) {
    const [active, setActive] = useState(initialIsBookmarked);
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState("");
    async function toggle(event) {
        event.preventDefault();
        if (busy) return;
        const post = event.currentTarget.closest(".feed-post");
        setBusy(true);
        try {
            const data = await ClubApi[active ? "delete" : "post"](bookmarkUrl);
            setActive(data.is_bookmarked);
            setError("");
            if (removeOnly && !data.is_bookmarked) post?.setAttribute("hidden", "");
        } catch (failure) {
            setError(failure.message);
        } finally {
            setBusy(false);
        }
    }
    if (removeOnly) {
        return (
            <button
                type="button"
                className={`bookmark-remove ${className}`}
                onClick={toggle}
                disabled={busy}
                aria-label="Убрать из закладок"
                aria-busy={busy}
                title={error || "Убрать из закладок"}
            >
                <i className="fas fa-times" aria-hidden="true" />
            </button>
        );
    }

    return (
        <a href={bookmarkUrl} className={className} onClick={toggle} title={error || undefined}>
            {busy ? (
                "🤔"
            ) : (
                <>
                    <i className={active ? "fas fa-bookmark" : "far fa-bookmark"} />
                    &nbsp;{active ? "Убрать из закладок" : "В закладки"}
                </>
            )}
        </a>
    );
}
