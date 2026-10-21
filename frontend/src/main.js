import "./vendor/inline-attachment";
import App from "./App";
import { mountIslands } from "./core/islands";
import { collapseCommentThread, handleCommentThreadCollapseToggle } from "./lib/comments";

const platform = navigator.userAgentData?.platform || navigator.platform;
if (/^(Win|Linux)/i.test(platform) && !/Android|Mobi|iPhone|iPad|iPod|CrOS/i.test(navigator.userAgent)) {
    import("../static/css/emoji.css").catch((error) => console.warn("Could not load emoji font", error));
}

App.onCreate();
App.onMount();

document.addEventListener("click", (event) => {
    const toggle = event.target.closest("[data-comment-collapse]");
    if (!toggle) return;
    const comment = toggle.closest(".reply, .comment");
    if (!comment) return;
    event.preventDefault();
    const collapsed = !comment.classList.contains("thread-collapsed");
    if (collapsed) collapseCommentThread(comment);
    else comment.classList.remove("thread-collapsed");
    handleCommentThreadCollapseToggle(collapsed, comment.id);
    const top = comment.getBoundingClientRect().top;
    if (top < 0) window.scrollBy(0, top);
});

// Cached Markdown can still contain the old clicker element.
for (const element of document.querySelectorAll("clicker")) {
    element.dataset.island = "Clicker";
    element.dataset.props = JSON.stringify({
        clickerId: element.getAttribute("clicker-id"),
        text: element.getAttribute("text"),
    });
}
// Preserve a reply click while its editor chunk is still loading.
let pendingReply;
const rememberReply = (event) => {
    const button = event.target.closest("[data-reply-to]");
    if (button) {
        event.preventDefault();
        pendingReply = button;
    }
};
document.addEventListener("click", rememberReply);
mountIslands().finally(() => {
    document.removeEventListener("click", rememberReply);
    if (pendingReply?.isConnected) pendingReply.click();
});
