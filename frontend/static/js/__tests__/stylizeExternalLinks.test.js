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

describe("stylizeExternalLinks", () => {
    beforeEach(() => {
        document.body.innerHTML = "";
    });

    test("adds target, rel and favicon to external link", () => {
        document.body.innerHTML = '<a href="https://example.com/page">Example</a>';
        App.stylizeExternalLinks();

        const link = document.querySelector("a");
        expect(link.getAttribute("target")).toBe("_blank");
        expect(link.getAttribute("rel")).toBe("noopener");

        const img = link.querySelector("img");
        expect(img).not.toBeNull();
        expect(img.className).toBe("link-favicon");
        expect(img.loading).toBe("lazy");
        expect(img.src).toContain("example.com");
    });

    test("favicon onerror removes img from DOM", () => {
        document.body.innerHTML = '<a href="https://example.com">Ext</a>';
        App.stylizeExternalLinks();

        const img = document.querySelector("img");
        expect(img).not.toBeNull();
        img.onerror.call(img);
        expect(document.querySelector("img")).toBeNull();
    });

    test("does not modify internal link", () => {
        document.body.innerHTML = '<a href="https://vas3k.club/posts">Posts</a>';
        App.stylizeExternalLinks();

        const link = document.querySelector("a");
        expect(link.getAttribute("target")).toBeNull();
        expect(link.querySelector("img")).toBeNull();
    });

    test("does not modify internal link with www", () => {
        document.body.innerHTML = '<a href="https://www.vas3k.club/posts">Posts</a>';
        App.stylizeExternalLinks();

        const link = document.querySelector("a");
        expect(link.getAttribute("target")).toBeNull();
        expect(link.querySelector("img")).toBeNull();
    });

    test("does not modify relative links", () => {
        document.body.innerHTML = '<a href="/about">About</a>';
        App.stylizeExternalLinks();

        const link = document.querySelector("a");
        expect(link.getAttribute("target")).toBeNull();
        expect(link.querySelector("img")).toBeNull();
    });

    test("does not modify anchor links", () => {
        document.body.innerHTML = '<a href="#section">Jump</a>';
        App.stylizeExternalLinks();

        const link = document.querySelector("a");
        expect(link.getAttribute("target")).toBeNull();
        expect(link.querySelector("img")).toBeNull();
    });

    test("correctly filters mixed internal and external links", () => {
        document.body.innerHTML = `
            <a href="https://vas3k.club/posts">Internal</a>
            <a href="https://github.com/vas3k">External 1</a>
            <a href="/about">Relative</a>
            <a href="https://example.com">External 2</a>
        `;
        App.stylizeExternalLinks();

        const links = document.querySelectorAll("a");
        expect(links[0].querySelector("img")).toBeNull();
        expect(links[1].querySelector("img")).not.toBeNull();
        expect(links[2].querySelector("img")).toBeNull();
        expect(links[3].querySelector("img")).not.toBeNull();
    });

    test("strips port from domain in favicon URL", () => {
        document.body.innerHTML = '<a href="https://example.com:8080/page">Port</a>';
        App.stylizeExternalLinks();

        const img = document.querySelector("img");
        expect(img.src).toContain("example.com");
        expect(img.src).not.toContain("8080");
    });
});
