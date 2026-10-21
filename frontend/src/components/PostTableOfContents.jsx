import { useEffect, useRef, useState } from "react";

export default function PostTableOfContents({ commentsCount = 0 }) {
    const [headlines] = useState(() =>
        [
            ...document.querySelectorAll(
                "article.post .text-body h1, article.post .text-body h2, article.post .text-body h3"
            ),
        ]
            .filter((element) => !element.classList.contains("post-title"))
            .map((element) => ({ element, text: element.textContent, level: Number(element.tagName.slice(-1)) }))
    );
    const [open, setOpen] = useState(false);
    const [active, setActive] = useState();
    const container = useRef(null);
    useEffect(() => {
        const update = () => {
            const text = document.querySelector("section.post-text");
            if (!text || text.getBoundingClientRect().bottom < 0) {
                setActive(undefined);
                return;
            }
            let index;
            headlines.forEach((headline, i) => {
                if (headline.element.getBoundingClientRect().top < window.innerHeight) index = i;
            });
            setActive(index);
        };
        const outside = (event) => {
            if (!container.current?.contains(event.target)) setOpen(false);
        };
        const observer = new IntersectionObserver(update, { threshold: [0, 1] });
        headlines.forEach(({ element }) => observer.observe(element));
        const text = document.querySelector("section.post-text");
        if (text) observer.observe(text);
        document.addEventListener("click", outside);
        update();
        return () => {
            observer.disconnect();
            document.removeEventListener("click", outside);
        };
    }, [headlines]);
    if (!headlines.length) return null;
    return (
        <div ref={container} className="post-toc">
            {open ? (
                <ul className="post-toc-opened-list" onMouseLeave={() => setOpen(false)}>
                    {headlines.map((headline, index) => (
                        <li
                            key={headline.element.id || index}
                            className={`post-toc-item post-toc-item-level-${headline.level} ${
                                index === active ? "post-toc-item-active" : ""
                            }`}
                        >
                            <a
                                href={`#${headline.element.id}`}
                                onClick={(event) => {
                                    event.preventDefault();
                                    headline.element.scrollIntoView({ behavior: "smooth" });
                                    history.replaceState(null, "", `#${headline.element.id}`);
                                }}
                            >
                                {headline.text}
                            </a>
                        </li>
                    ))}
                    <li className="post-toc-item-level-1 post-toc-item-comments">
                        <a href="#comments">Комментарии {Number(commentsCount) > 0 ? `(${commentsCount})` : ""}</a>
                    </li>
                </ul>
            ) : (
                <ul className="post-toc-collapsed-list" onMouseOver={() => setOpen(true)} onClick={() => setOpen(true)}>
                    {headlines.map((headline, index) => (
                        <li
                            key={index}
                            className={`post-toc-collapsed-item post-toc-collapsed-level-${headline.level} ${
                                index === active ? "post-toc-collapsed-active" : ""
                            }`}
                        />
                    ))}
                </ul>
            )}
        </div>
    );
}
