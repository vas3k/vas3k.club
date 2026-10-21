import { act } from "react";
import { render } from "../../test/render";
import CommentScrollArrow from "../components/CommentScrollArrow";

describe("CommentScrollArrow", () => {
    let view;
    let scroll;
    beforeEach(() => {
        document.body.innerHTML =
            '<div id="app"></div><div id="comments"><div class="comment-is-new" id="comment-one"></div><div class="comment-is-new" id="comment-two"></div></div><form id="post-comments-form"><textarea></textarea></form><footer id="footer"></footer>';
        scroll = vi.fn();
        Element.prototype.scrollIntoView = scroll;
        window.matchMedia = vi.fn(() => ({ matches: false }));
        document.getElementById("comment-one").getBoundingClientRect = () => ({ top: 100 });
        document.getElementById("comment-two").getBoundingClientRect = () => ({ top: 200 });
        view = render(CommentScrollArrow);
    });
    afterEach(() => {
        view.unmount();
        vi.restoreAllMocks();
        document.body.innerHTML = "";
    });

    it("navigates to the nearest new comment and updates the hash", () => {
        act(() => view.container.querySelector("button").click());
        expect(scroll.mock.instances[0].id).toBe("comment-one");
        expect(location.hash).toBe("#comment-one");
        expect(document.getElementById("comment-one").classList.contains("comment-scroll-selected")).toBe(true);
    });
    it("skips new replies within a new parent comment", () => {
        const reply = document.createElement("div");
        reply.className = "comment-is-new";
        reply.id = "reply";
        reply.getBoundingClientRect = () => ({ top: 50 });
        document.getElementById("comment-one").append(reply);
        act(() => view.container.querySelector("button").click());
        expect(scroll.mock.instances[0].id).toBe("comment-one");
    });
    it("moves to the form when there are no new comments, then back to the top", () => {
        document.getElementById("comments").remove();
        act(() => view.container.querySelector("button").click());
        expect(scroll.mock.instances[0].id).toBe("post-comments-form");
        expect(view.container.querySelector("button").classList.contains("arrow-up")).toBe(true);
        act(() => view.container.querySelector("button").click());
        expect(scroll.mock.instances[1].id).toBe("app");
    });
    it("uses the footer when there is no form", () => {
        document.getElementById("comments").remove();
        document.getElementById("post-comments-form").remove();
        act(() => view.container.querySelector("button").click());
        expect(scroll.mock.instances[0].id).toBe("footer");
    });
    it("supports the control-arrow shortcut", () => {
        act(() => document.dispatchEvent(new KeyboardEvent("keyup", { key: "ArrowDown", ctrlKey: true })));
        expect(scroll.mock.instances[0].id).toBe("comment-one");
    });
    it("leaves editor keyboard input alone", () => {
        act(() =>
            document
                .querySelector("textarea")
                .dispatchEvent(new KeyboardEvent("keyup", { key: "ArrowDown", ctrlKey: true, bubbles: true })),
        );
        expect(scroll).not.toHaveBeenCalled();
    });
    it("honors reduced motion", () => {
        window.matchMedia.mockReturnValue({ matches: true });
        act(() => view.container.querySelector("button").click());
        expect(scroll).toHaveBeenCalledWith({ behavior: "instant" });
    });
    it("removes keyboard handlers on unmount", () => {
        view.unmount();
        act(() => document.dispatchEvent(new KeyboardEvent("keyup", { key: "ArrowDown", ctrlKey: true })));
        expect(scroll).not.toHaveBeenCalled();
    });
});
