import { useEffect, useState } from "react";
import "../../static/css/components/theme-switcher.css";

export default function ThemeSwitcher() {
    const [theme, setTheme] = useState(() => {
        let saved;
        try { saved = localStorage.getItem("theme"); } catch {}
        return ["light", "auto", "dark"].includes(saved) ? saved : "auto";
    });
    const [prefersLight, setPrefersLight] = useState(() => matchMedia("(prefers-color-scheme: light)").matches);
    const realTheme = theme === "auto" ? (prefersLight ? "light" : "dark") : theme;

    useEffect(() => {
        const query = matchMedia("(prefers-color-scheme: light)");
        const update = () => {
            setPrefersLight(query.matches);
            document.documentElement.setAttribute("theme", theme === "auto" ? (query.matches ? "light" : "dark") : theme);
        };
        update();
        try { localStorage.setItem("theme", theme); } catch {}
        query.addEventListener("change", update);
        return () => query.removeEventListener("change", update);
    }, [theme]);

    return (
        <div className="theme-switcher" data-value={theme} data-real={realTheme}>
            <button type="button" onClick={() => setTheme("light")}>☀️</button>
            <button type="button" onClick={() => setTheme("auto")}>🌗</button>
            <button type="button" onClick={() => setTheme("dark")}>🌙</button>
        </div>
    );
}
