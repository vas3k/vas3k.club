import { useEffect, useState } from "react";
import ClubApi from "../lib/api.service";
import "../../static/css/components/clicker.css";

export default function Clicker({ clickerId, text }) {
    const [data, setData] = useState({ clicks: [], count: 0, is_clicked: false });
    const [busy, setBusy] = useState(true);
    const [error, setError] = useState("");
    const url = `/clickers/${encodeURIComponent(clickerId)}.json`;
    useEffect(() => {
        let disposed = false;
        ClubApi.get(url)
            .then((result) => {
                if (!disposed) setData(result);
            })
            .catch((failure) => {
                if (!disposed) setError(failure.message);
            })
            .finally(() => {
                if (!disposed) setBusy(false);
            });
        return () => {
            disposed = true;
        };
    }, [url]);
    async function toggle(event) {
        if (event.target.closest("a")) return;
        if (busy) return;
        setBusy(true);
        try {
            setData(await ClubApi[data.is_clicked ? "delete" : "post"](url));
            setError("");
        } catch (failure) {
            setError(failure.message);
        } finally {
            setBusy(false);
        }
    }
    return (
        <div
            id={`clicker-${clickerId}`}
            className={`clicker ${data.is_clicked ? "clicker-is-clicked" : ""}`}
            onClick={toggle}
            title={error || undefined}
        >
            <button
                type="button"
                className="clicker-checkbox"
                disabled={busy}
                aria-label={text}
                aria-pressed={data.is_clicked}
            >
                {busy ? "⌛" : ""}
            </button>
            <div className="clicker-text">{text}</div>
            {data.count > 0 && <div className="clicker-counter">{data.count}</div>}
            {data.clicks.length > 0 && (
                <div className="clicker-users">
                    {data.clicks.map(({ user }) => (
                        <a
                            key={user.slug}
                            href={`/user/${user.slug}/`}
                            target="_blank"
                            rel="noreferrer"
                            className="clicker-avatar"
                            title={user.full_name}
                            style={{
                                backgroundImage: `url(${JSON.stringify(user.avatar || "https://i.vas3k.club/v.png")})`,
                            }}
                        />
                    ))}
                </div>
            )}
        </div>
    );
}
