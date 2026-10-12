jest.mock("easymde", () => ({}));
jest.mock("lightense-images", () => jest.fn());
jest.mock("../common/markdown-editor", () => ({
    createFileInput: jest.fn(),
    createMarkdownEditor: jest.fn(),
    handleFormSubmissionShortcuts: jest.fn(),
    imageUploadOptions: { allowedTypes: [] },
}));
jest.mock("../common/comments", () => ({
    getCollapsedCommentThreadsSet: jest.fn(() => new Set()),
}));

import App from "../App";

describe("initializeCodeCopyButtons", () => {
    beforeEach(() => {
        document.body.innerHTML = "";
        navigator.clipboard = { writeText: jest.fn(() => Promise.resolve()) };
    });

    test("adds copy button to code blocks only", () => {
        document.body.innerHTML =
            '<div class="text-body"><p><code>inline</code></p><pre><code>print(1)\n</code></pre></div>';
        App.initializeCodeCopyButtons();

        const buttons = document.querySelectorAll(".code-copy-button");
        expect(buttons.length).toBe(1);
        expect(buttons[0].parentElement.tagName).toBe("PRE");
        expect(buttons[0].querySelector("i").className).toBe("far fa-copy");
    });

    test("copies code without trailing newline and shows check icon", async () => {
        document.body.innerHTML = '<div class="text-body"><pre><code>a = 1\nb = 2\n</code></pre></div>';
        App.initializeCodeCopyButtons();

        const button = document.querySelector(".code-copy-button");
        button.click();
        await Promise.resolve();
        await Promise.resolve();

        expect(navigator.clipboard.writeText).toHaveBeenCalledWith("a = 1\nb = 2");
        expect(button.querySelector("i").className).toBe("fas fa-check");
    });

    test("does nothing when clipboard API is unavailable", () => {
        navigator.clipboard = undefined;
        document.body.innerHTML = '<div class="text-body"><pre><code>x</code></pre></div>';
        App.initializeCodeCopyButtons();

        expect(document.querySelector(".code-copy-button")).toBeNull();
    });
});
