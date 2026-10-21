import { useRef, useState } from "react";
import ClubApi from "../lib/api.service";

export default function Vote({
    resource = "post",
    initialUpvotes = 0,
    initialIsVoted = false,
    initialUpvoteTimestamp,
    hoursToRetractVote = 0,
    isDisabled = false,
    isInline = false,
    isSmall = false,
    voteUrl,
    variant = "upvote",
    caption = "",
}) {
    const [count, setCount] = useState(initialUpvotes);
    const [voted, setVoted] = useState(initialIsVoted || Boolean(initialUpvoteTimestamp));
    const [timestamp, setTimestamp] = useState(Number(initialUpvoteTimestamp));
    const busy = useRef(false);
    const [error, setError] = useState("");
    async function toggle(event) {
        event.preventDefault();
        if (
            isDisabled ||
            busy.current ||
            (voted && timestamp && (Date.now() - timestamp) / 3600000 > hoursToRetractVote)
        )
            return;
        busy.current = true;
        try {
            const data = await ClubApi[voted ? "delete" : "post"](voteUrl);
            setCount(Number(data[resource].upvotes));
            setVoted(data.is_voted);
            setTimestamp(data.upvoted_timestamp);
            setError("");
        } catch (failure) {
            setError(failure.message);
        } finally {
            busy.current = false;
        }
    }
    return (
        <a
            href={voteUrl}
            title={error || undefined}
            aria-disabled={isDisabled}
            onClick={toggle}
            className={`upvote ${voted && !isDisabled ? "upvote-voted" : ""} ${isDisabled ? "upvote-disabled" : ""} ${
                isInline ? "upvote-type-inline" : ""
            } ${isSmall ? "upvote-type-small" : ""} ${variant === "checkbox" ? "upvote-type-checkbox" : ""}`}
        >
            {variant === "checkbox" ? (
                <>
                    <span className="upvote-checkbox-icon">
                        <i className={voted || isDisabled ? "fas fa-check-square" : "far fa-square"} />
                    </span>
                    {caption && !isDisabled && <span className="upvote-checkbox-caption">{caption}</span>}
                </>
            ) : (
                count
            )}
        </a>
    );
}
