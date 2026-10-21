import { useEffect, useEffectEvent, useRef, useState } from "react";

export default function CommentScrollArrow() {
    const [up, setUp] = useState(false);
    const highlightTimer = useRef(null);

    function navigate(direction, skipComments = false) {
        const comments = skipComments
            ? []
            : [...document.querySelectorAll(".comment-is-new")]
                  .filter((element) => !element.parentElement.closest(".comment-is-new"))
                  .map((element) => ({
                      element,
                      top: element.getBoundingClientRect().top,
                      margin: parseFloat(getComputedStyle(element).scrollMarginTop) || 0,
                  }))
                  .filter(({ top, margin }) => (direction === "down" ? top - margin > 2 : top < 0))
                  .sort((a, b) => Math.abs(a.top) - Math.abs(b.top));
        const target =
            comments[0]?.element ||
            (direction === "down"
                ? document.getElementById("post-comments-form") || document.getElementById("footer")
                : document.getElementById("app"));
        if (!target) return;
        if (!comments.length) setUp(direction === "down");
        document.querySelector(".comment-scroll-selected")?.classList.remove("comment-scroll-selected");
        document.querySelector(".comment-scroll-animation")?.classList.remove("comment-scroll-animation");
        clearTimeout(highlightTimer.current);
        if (comments.length) {
            target.classList.add("comment-scroll-selected", "comment-scroll-animation");
            highlightTimer.current = setTimeout(() => target.classList.remove("comment-scroll-animation"), 500);
        }
        target.scrollIntoView({
            behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "instant" : "smooth",
        });
        if (target.id) history.replaceState(null, "", `#${target.id}`);
    }

    const onKey = useEffectEvent((event) => {
        if (event.isComposing || event.target.closest?.('input, textarea, select, [contenteditable="true"]')) return;
        if (!event.ctrlKey || !["ArrowDown", "ArrowUp"].includes(event.key)) return;
        event.preventDefault();
        const direction = event.key === "ArrowUp" ? "up" : "down";
        setUp(direction === "up");
        navigate(direction);
    });

    useEffect(() => {
        let frame;
        const onScroll = () => {
            cancelAnimationFrame(frame);
            frame = requestAnimationFrame(() => {
                if (window.scrollY === 0) setUp(false);
                else if (window.scrollY + window.innerHeight >= document.documentElement.scrollHeight - 2) setUp(true);
            });
        };
        const onDate = (event) => {
            if (event.target.closest?.(".comment-header-date"))
                event.target.closest?.(".comment-scroll-selected")?.classList.remove("comment-scroll-selected");
        };
        const keyHandler = (event) => onKey(event);
        window.addEventListener("scroll", onScroll, { passive: true });
        document.addEventListener("keyup", keyHandler);
        document.addEventListener("click", onDate);
        return () => {
            cancelAnimationFrame(frame);
            clearTimeout(highlightTimer.current);
            window.removeEventListener("scroll", onScroll);
            document.removeEventListener("keyup", keyHandler);
            document.removeEventListener("click", onDate);
        };
    }, []);

    return (
        <button
            type="button"
            aria-label={up ? "Наверх" : "Перейти к комментариям"}
            className={`comment-scroll-arrow ${up ? "arrow-up" : ""}`}
            onClick={(event) =>
                navigate(event.shiftKey ? (up ? "down" : "up") : up ? "up" : "down", up && !event.shiftKey)
            }
        />
    );
}
