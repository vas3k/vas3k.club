import { act, createElement, createRef } from "react";
import { createRoot } from "react-dom/client";

export function render(Component, props = {}) {
    const container = document.createElement("div");
    document.body.appendChild(container);
    const root = createRoot(container);
    const ref = createRef();
    const componentProps = Component.prototype?.isReactComponent ? { ...props, ref } : props;
    act(() => root.render(createElement(Component, componentProps)));
    return {
        container,
        instance: ref.current,
        unmount() {
            act(() => root.unmount());
            container.remove();
        },
    };
}
