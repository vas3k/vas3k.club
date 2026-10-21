import useResourceToggle from "../hooks/useResourceToggle";

export default function FriendButton({ isFriendByDefault = false, url }) {
    const { active, busy, error, toggle } = useResourceToggle(url, isFriendByDefault);
    return (
        <button
            type="button"
            className="button button-inverted friend-button"
            disabled={busy}
            title={error || undefined}
            onClick={toggle}
        >
            <span className={active ? "friend-button-icon" : "friend-button-icon-big"}>{active ? "✅" : "+"}</span>
            <span className="friend-button-status">{busy ? "..." : active ? "Мой чувак" : "Подписаться"}</span>
            {error && <span role="alert"> — {error}</span>}
        </button>
    );
}
