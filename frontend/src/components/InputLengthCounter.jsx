import { useEffect, useState } from "react";

export default function InputLengthCounter({ minLength = 0, element, label = "", className = "" }) {
    const [count, setCount] = useState(0);
    useEffect(() => {
        const input = document.querySelector(element);
        if (!input) return;
        const update = () => setCount(input.value.length);
        update();
        input.addEventListener("input", update);
        return () => {
            input.removeEventListener("input", update);
        };
    }, [element]);
    return (
        <span className={`${className} ${count < minLength ? "bad" : "good"}`}>
            {label}
            {count < minLength
                ? "💩"
                : count < minLength + 100
                ? "🙂"
                : count < minLength + 300
                ? "😎"
                : count < minLength + 500
                ? "🚀"
                : "💎🚀👍"}{" "}
            {count}
            {count < minLength && ` / ${minLength}`}
        </span>
    );
}
