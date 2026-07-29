const CARD_SELECTOR = ".user-achievement";

function resetCard(el) {
    el.__achRaf = 0;
    el.style.setProperty("--shine-x", "50%");
    el.style.setProperty("--shine-y", "50%");
    el.style.setProperty("--tilt-x", "0deg");
    el.style.setProperty("--tilt-y", "0deg");
}

document.addEventListener(
    "mousemove",
    (e) => {
        const el = e.target && e.target.closest ? e.target.closest(CARD_SELECTOR) : null;
        if (!el) return;
        if (el.__achRaf) return;

        const { clientX, clientY } = e;
        el.__achRaf = requestAnimationFrame(() => {
            el.__achRaf = 0;
            if (!el.isConnected) return;

            const r = el.getBoundingClientRect();
            const w = r.width || 1;
            const h = r.height || 1;
            const x = Math.min(1, Math.max(0, (clientX - r.left) / w));
            const y = Math.min(1, Math.max(0, (clientY - r.top) / h));

            el.style.setProperty("--shine-x", `${(x * 100).toFixed(2)}%`);
            el.style.setProperty("--shine-y", `${(y * 100).toFixed(2)}%`);
            el.style.setProperty("--tilt-x", `${((0.5 - y) * 18).toFixed(2)}deg`);
            el.style.setProperty("--tilt-y", `${((x - 0.5) * 26).toFixed(2)}deg`);
        });
    },
    { passive: true }
);

document.addEventListener("mouseout", (e) => {
    const el = e.target && e.target.closest ? e.target.closest(CARD_SELECTOR) : null;
    if (!el) return;

    const to = e.relatedTarget;
    if (to && el.contains(to)) return; // moving between children

    resetCard(el);
});

