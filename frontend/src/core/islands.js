const roots = new Map();
const islands = import.meta.glob("../islands/*.jsx");

export async function mountIslands(root = document) {
    const elements = [...root.querySelectorAll("[data-island]:not([data-island-mounted])")];
    if (!elements.length) return;

    const [{ createElement }, { createRoot }, { flushSync }] = await Promise.all([
        import("react"), import("react-dom/client"), import("react-dom"),
    ]);

    await Promise.all(
        elements.map(async (element) => {
            const name = element.dataset.island;
            const load = islands[`../islands/${name}.jsx`];
            if (!load) {
                console.error(`Unknown island: ${name}`);
                return;
            }

            element.dataset.islandMounted = "";
            try {
                const props = JSON.parse(element.dataset.props || "{}");
                for (const { name, value } of element.attributes) {
                    const match = name.match(/^data-(prop|json)-(.+)$/);
                    if (!match) continue;
                    const key = match[2].replace(/-([a-z])/g, (_, letter) => letter.toUpperCase());
                    props[key] = match[1] === "json" ? JSON.parse(value) : value;
                }
                if (!props.label) props.label = element.textContent.trim();
                const { default: Component } = await load();
                const reactRoot = createRoot(element);
                roots.set(element, reactRoot);
                flushSync(() => reactRoot.render(createElement(Component, props)));
            } catch (error) {
                delete element.dataset.islandMounted;
                console.error(`Unable to mount ${name}`, error);
            }
        })
    );
}

if (import.meta.hot) {
    import.meta.hot.dispose(() => {
        for (const [element, root] of roots) {
            root.unmount();
            delete element.dataset.islandMounted;
        }
    });
}
