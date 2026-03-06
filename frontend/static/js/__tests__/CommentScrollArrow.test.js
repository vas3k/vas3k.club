import { shallowMount } from "@vue/test-utils";
import CommentScrollArrow from "../components/CommentScrollArrow.vue";

describe("CommentScrollArrow.vue", () => {
    let wrapper;
    let commentsContainer;

    beforeEach(() => {
        // Create #comments element needed by initSelectedClassCleanerListener
        commentsContainer = document.createElement("div");
        commentsContainer.id = "comments";
        document.body.appendChild(commentsContainer);

        wrapper = shallowMount(CommentScrollArrow);
    });

    afterEach(() => {
        wrapper.destroy();
        commentsContainer.remove();
        jest.restoreAllMocks();
    });

    describe("getBodyTop", () => {
        it("returns negative scrollY", () => {
            Object.defineProperty(window, "scrollY", { value: 200, writable: true, configurable: true });
            expect(wrapper.vm.getBodyTop()).toBe(-200);
        });

        it("returns 0 when at top of page", () => {
            Object.defineProperty(window, "scrollY", { value: 0, writable: true, configurable: true });
            // -window.scrollY produces -0; verify it equals 0 numerically
            expect(wrapper.vm.getBodyTop() === 0).toBe(true);
        });
    });

    describe("getElementMargin", () => {
        it("parses scrollMarginTop from computed style", () => {
            const el = document.createElement("div");
            el.style.scrollMarginTop = "60px";
            document.body.appendChild(el);

            const margin = wrapper.vm.getElementMargin(el);
            expect(margin).toBe(60);

            document.body.removeChild(el);
        });

        it("returns NaN for element without scrollMarginTop", () => {
            const el = document.createElement("div");
            document.body.appendChild(el);

            const margin = wrapper.vm.getElementMargin(el);
            expect(Number.isNaN(margin)).toBe(true);

            document.body.removeChild(el);
        });
    });

    describe("scrollToComment", () => {
        let testComments;

        function setupComments(positions) {
            testComments = positions.map((top, i) => {
                const el = document.createElement("div");
                el.className = "comment comment-is-new";
                el.id = `comment-${i}`;
                el.style.scrollMarginTop = "0px";
                el.getBoundingClientRect = () => ({ top });
                commentsContainer.appendChild(el);
                return el;
            });

            return testComments;
        }

        afterEach(() => {
            if (testComments) {
                testComments.forEach((el) => el.remove());
                testComments = null;
            }
            const footer = document.getElementById("footer");
            if (footer) footer.remove();
        });

        it("scrolls to nearest comment below when direction is Down", () => {
            const comments = setupComments([100, 300, 500]);

            wrapper.vm.scrollToElement = jest.fn();
            Object.defineProperty(window, "scrollY", { value: 0, writable: true, configurable: true });

            wrapper.vm.scrollToComment("Down");

            expect(wrapper.vm.scrollToElement).toHaveBeenCalled();
            const scrolledTo = wrapper.vm.scrollToElement.mock.calls[0][0];
            expect(scrolledTo.id).toBe("comment-0");
            expect(scrolledTo.classList.contains("comment-scroll-selected")).toBe(true);
        });

        it("scrolls to nearest comment above when direction is Up", () => {
            const comments = setupComments([-200, -100, 300]);

            wrapper.vm.scrollToElement = jest.fn();
            Object.defineProperty(window, "scrollY", { value: 500, writable: true, configurable: true });

            wrapper.vm.scrollToComment("Up");

            expect(wrapper.vm.scrollToElement).toHaveBeenCalled();
            const scrolledTo = wrapper.vm.scrollToElement.mock.calls[0][0];
            // Should pick a comment with top < 0
            expect(["comment-0", "comment-1"]).toContain(scrolledTo.id);
        });

        it("calls scrollExtreme when no matching comments found", () => {
            // No comments in DOM besides the container
            wrapper.vm.scrollExtreme = jest.fn();

            wrapper.vm.scrollToComment("Down");

            expect(wrapper.vm.scrollExtreme).toHaveBeenCalledWith("Down");
        });

        it("calls getBoundingClientRect once per comment (batched layout read)", () => {
            const spies = [];
            const comments = [100, 300, 500].map((top, i) => {
                const el = document.createElement("div");
                el.className = "comment comment-is-new";
                el.id = `comment-${i}`;
                el.style.scrollMarginTop = "0px";
                const spy = jest.fn(() => ({ top }));
                el.getBoundingClientRect = spy;
                spies.push(spy);
                commentsContainer.appendChild(el);
                return el;
            });

            wrapper.vm.scrollToElement = jest.fn();
            Object.defineProperty(window, "scrollY", { value: 0, writable: true, configurable: true });

            wrapper.vm.scrollToComment("Down");

            // Each element's getBoundingClientRect should be called exactly once —
            // all positions are read in a single batch before filtering/reducing
            spies.forEach((spy) => {
                expect(spy).toHaveBeenCalledTimes(1);
            });

            comments.forEach((el) => el.remove());
        });

        it("removes comment-scroll-selected from previously selected comment", () => {
            const comments = setupComments([100, 300]);
            // Simulate that comment-1 was previously selected
            comments[1].classList.add("comment-scroll-selected");

            wrapper.vm.scrollToElement = jest.fn();
            Object.defineProperty(window, "scrollY", { value: 0, writable: true, configurable: true });

            wrapper.vm.scrollToComment("Down");

            // comment-1 should have lost comment-scroll-selected
            expect(comments[1].classList.contains("comment-scroll-selected")).toBe(false);
            // comment-0 (nearest) should now be selected
            expect(comments[0].classList.contains("comment-scroll-selected")).toBe(true);
        });
    });

    describe("initOnPageScroll", () => {
        it("sets arrowDirection to Up at bottom of page", () => {
            Object.defineProperty(document.documentElement, "scrollHeight", {
                value: 1000,
                writable: true,
                configurable: true,
            });
            Object.defineProperty(window, "innerHeight", { value: 500, writable: true, configurable: true });
            Object.defineProperty(window, "pageYOffset", { value: 500, writable: true, configurable: true });

            wrapper.vm.initOnPageScroll();
            wrapper.vm.onPageScrollHandler();

            expect(wrapper.vm.arrowDirection).toBe("Up");
        });

        it("sets arrowDirection to Down at top of page", () => {
            Object.defineProperty(window, "pageYOffset", { value: 0, writable: true, configurable: true });

            wrapper.vm.arrowDirection = "Up";
            wrapper.vm.initOnPageScroll();
            wrapper.vm.onPageScrollHandler();

            expect(wrapper.vm.arrowDirection).toBe("Down");
        });
    });

    describe("beforeDestroy", () => {
        it("removes event listeners on destroy", () => {
            const removeWindowListener = jest.spyOn(window, "removeEventListener");
            const removeDocListener = jest.spyOn(document, "removeEventListener");

            const keyUpHandler = wrapper.vm.keyUpHandler;
            const scrollHandler = wrapper.vm.onPageScrollHandler;

            wrapper.destroy();

            expect(removeDocListener).toHaveBeenCalledWith("keyup", keyUpHandler);
            expect(removeWindowListener).toHaveBeenCalledWith("scroll", scrollHandler);
        });
    });

    describe("rendering", () => {
        it("renders a button with comment-scroll-arrow class", () => {
            expect(wrapper.find("button.comment-scroll-arrow").exists()).toBe(true);
        });

        it("applies arrow-up class when arrowDirection is Up", async () => {
            wrapper.setData({ arrowDirection: "Up" });
            await wrapper.vm.$nextTick();

            expect(wrapper.classes()).toContain("arrow-up");
        });

        it("does not apply arrow-up class when arrowDirection is Down", () => {
            expect(wrapper.classes()).not.toContain("arrow-up");
        });
    });
});
