import { useState } from "react";
import ClubApi from "../lib/api.service";

export default function PostBookmark({ initialIsBookmarked = false, bookmarkUrl, className = "" }) {
    const [active, setActive] = useState(initialIsBookmarked);
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState("");
    async function toggle(event) {
        event.preventDefault();
        if (busy) return;
        setBusy(true);
        try {
            const data = await ClubApi[active ? "delete" : "post"](bookmarkUrl);
            setActive(data.is_bookmarked);
            setError("");
        } catch (failure) {
            setError(failure.message);
        } finally {
            setBusy(false);
        }
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
