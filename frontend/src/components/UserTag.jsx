import useResourceToggle from "../hooks/useResourceToggle";

export default function UserTag({ tagName, tagColor, isActiveByDefault = false, url, className = "" }) {
    const { active, busy, error, toggle } = useResourceToggle(url, isActiveByDefault);
    return (
        <a
            href={url}
            className={`${className} ${active ? "user-tag-active" : ""}`}
            style={{ backgroundColor: active ? tagColor : undefined }}
            title={error || undefined}
            onClick={(event) => { event.preventDefault(); toggle(); }}
        >
            {tagName}
            {error && <span role="alert"> — {error}</span>}
        </a>
    );
}
