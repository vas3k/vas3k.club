import useResourceToggle from "../hooks/useResourceToggle";
import "../../static/css/components/toggle.css";

export default function Toggle({ isActiveByDefault = false, isInverted = false, url, label, className = "", variant }) {
    const { active, busy, error, toggle } = useResourceToggle(url, isActiveByDefault, isInverted);
    return (
        <label
            className={`toggle-control ${className} ${active ? "is-active" : ""} ${
                variant === "rsvp" ? "button event-rsvp-button" : ""
            }`}
            title={error || undefined}
        >
            <input
                type="checkbox"
                checked={active}
                disabled={busy}
                onChange={toggle}
                style={variant === "rsvp" ? { display: "none" } : undefined}
            />
            {variant === "rsvp" ? (
                <>
                    <span className="event-rsvp-button-icon">
                        <i className={active ? "fas fa-check-square" : "far fa-square"} />
                    </span>
                    <span className="event-rsvp-button-text">{active ? "Я в деле!" : "Я приду"}</span>
                </>
            ) : (
                label
            )}
            {error && <span role="alert"> — {error}</span>}
        </label>
    );
}
