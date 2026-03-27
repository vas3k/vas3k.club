import { pluralize, isCommunicationForm, findParentForm, throttle, debounce, isMobile } from "../common/utils";

describe("pluralize", () => {
    const words = ["пост", "поста", "постов"];

    test.each([
        [0, "постов"],
        [1, "пост"],
        [2, "поста"],
        [3, "поста"],
        [4, "поста"],
        [5, "постов"],
        [10, "постов"],
        [11, "постов"],
        [12, "постов"],
        [13, "постов"],
        [14, "постов"],
        [19, "постов"],
        [20, "постов"],
        [21, "пост"],
        [22, "поста"],
        [24, "поста"],
        [25, "постов"],
        [30, "постов"],
        [101, "пост"],
        [102, "поста"],
        [111, "постов"],
        [112, "постов"],
    ])("pluralize(%i) => %s", (count, expected) => {
        expect(pluralize(count, words)).toBe(expected);
    });
});

describe("isCommunicationForm", () => {
    test("returns true for comment-form-form", () => {
        const form = document.createElement("form");
        form.classList.add("comment-form-form");
        expect(isCommunicationForm(form)).toBe(true);
    });

    test("returns true for reply-form-form", () => {
        const form = document.createElement("form");
        form.classList.add("reply-form-form");
        expect(isCommunicationForm(form)).toBe(true);
    });

    test("returns false for other class", () => {
        const form = document.createElement("form");
        form.classList.add("some-other-form");
        expect(isCommunicationForm(form)).toBe(false);
    });

    test("returns false for no classes", () => {
        const form = document.createElement("form");
        expect(isCommunicationForm(form)).toBe(false);
    });
});

describe("findParentForm", () => {
    test("returns parent form element", () => {
        const form = document.createElement("form");
        const button = document.createElement("button");
        form.appendChild(button);
        expect(findParentForm(button)).toBe(form);
    });

    test("returns null when no parent form", () => {
        const div = document.createElement("div");
        const button = document.createElement("button");
        div.appendChild(button);
        expect(findParentForm(button)).toBeNull();
    });

    test("returns closest form for nested forms", () => {
        const outerForm = document.createElement("form");
        const innerForm = document.createElement("form");
        const button = document.createElement("button");
        outerForm.appendChild(innerForm);
        innerForm.appendChild(button);
        expect(findParentForm(button)).toBe(innerForm);
    });
});

describe("throttle", () => {
    beforeEach(() => jest.useFakeTimers());
    afterEach(() => jest.useRealTimers());

    test("calls immediately on first invocation", () => {
        const fn = jest.fn();
        const throttled = throttle(fn, 100);
        throttled();
        expect(fn).toHaveBeenCalledTimes(1);
    });

    test("ignores calls within wait period", () => {
        const fn = jest.fn();
        const throttled = throttle(fn, 100);
        throttled();
        throttled();
        throttled();
        expect(fn).toHaveBeenCalledTimes(1);
    });

    test("executes trailing call after wait", () => {
        const fn = jest.fn();
        const throttled = throttle(fn, 100);
        throttled();
        throttled();
        jest.advanceTimersByTime(100);
        expect(fn).toHaveBeenCalledTimes(2);
    });
});

describe("debounce", () => {
    beforeEach(() => jest.useFakeTimers());
    afterEach(() => jest.useRealTimers());

    test("delays execution by wait ms", () => {
        const fn = jest.fn();
        const debounced = debounce(fn, 100);
        debounced();
        expect(fn).not.toHaveBeenCalled();
        jest.advanceTimersByTime(100);
        expect(fn).toHaveBeenCalledTimes(1);
    });

    test("resets timer on repeated calls", () => {
        const fn = jest.fn();
        const debounced = debounce(fn, 100);
        debounced();
        jest.advanceTimersByTime(50);
        debounced();
        jest.advanceTimersByTime(50);
        expect(fn).not.toHaveBeenCalled();
        jest.advanceTimersByTime(50);
        expect(fn).toHaveBeenCalledTimes(1);
    });

    test("immediate flag suppresses trailing call", () => {
        const fn = jest.fn();
        const debounced = debounce(fn, 100, true);
        debounced();
        jest.advanceTimersByTime(100);
        expect(fn).not.toHaveBeenCalled();
    });
});

describe("isMobile", () => {
    const originalNavigator = navigator;

    function setUserAgent(ua) {
        Object.defineProperty(window, "navigator", {
            value: { userAgent: ua, vendor: "" },
            writable: true,
            configurable: true,
        });
        window.MSStream = undefined;
        window.opera = undefined;
    }

    afterEach(() => {
        Object.defineProperty(window, "navigator", {
            value: originalNavigator,
            writable: true,
            configurable: true,
        });
    });

    test("returns true for Android", () => {
        setUserAgent("Mozilla/5.0 (Linux; Android 10; Pixel 3)");
        expect(isMobile()).toBe(true);
    });

    test("returns true for iPhone", () => {
        setUserAgent("Mozilla/5.0 (iPhone; CPU iPhone OS 14_0)");
        expect(isMobile()).toBe(true);
    });

    test("returns true for Windows Phone", () => {
        setUserAgent("Mozilla/5.0 (Windows Phone 10.0; Android 6.0.1)");
        expect(isMobile()).toBe(true);
    });

    test("returns false for desktop", () => {
        setUserAgent("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)");
        expect(isMobile()).toBe(false);
    });
});
