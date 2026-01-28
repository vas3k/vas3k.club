import twemoji from "twemoji";
import EasyMDE from "easymde";
import Lightense from "lightense-images";

import { isCommunicationForm, isMobile } from "./common/utils";
import {
    createFileInput,
    createMarkdownEditor,
    handleFormSubmissionShortcuts,
    imageUploadOptions,
} from "./common/markdown-editor";
import { getCollapsedCommentThreadsSet } from "./common/comments";

const INITIAL_SYNC_DELAY = 50;

const App = {
    onCreate() {
        this.initializeThemeSwitcher();
        this.stylizeExternalLinks();
    },
    onMount() {
        this.initializeImageZoom();
        this.initializeEmojiForPoorPeople();
        this.blockCommunicationFormsResubmit();
        this.restoreCommentThreadsState();
        this.initializePostActions();

        const registeredEditors = this.initializeMarkdownEditor();

        setTimeout(function () {
            registeredEditors.forEach((editor) => {
                // textarea value after navigation might be restored after codemirror inited
                if (editor.element.value && !editor.codemirror.getValue()) {
                    editor.codemirror.setValue(editor.element.value);
                }
            });
        }, INITIAL_SYNC_DELAY);
    },
    initializeEmojiForPoorPeople() {
        const isApple = /iPad|iPhone|iPod|OS X/.test(navigator.userAgent) && !window.MSStream;
        if (!isApple) {
            document.body = twemoji.parse(document.body, {
                base: "https://cdn.jsdelivr.net/gh/twitter/twemoji@14.0.2/assets/",
            });
        }
    },
    initializeThemeSwitcher() {
        const mediaQueryList = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)");

        const setFaviconHref = (e) => {
            const svgFavicon = document.querySelector('link[type="image/svg+xml"]');
            const isDark = e.matches;
            svgFavicon.href = isDark ? "/static/images/favicon/favicon-dark.svg" : "/static/images/favicon/favicon.svg";
        };

        setFaviconHref(mediaQueryList);
        mediaQueryList.addListener(setFaviconHref);
    },
    initializeMarkdownEditor() {
        const fullMarkdownEditors = [...document.querySelectorAll(".markdown-editor-full")].reduce(
            (editors, element) => {
                const fileInputEl = createFileInput({ allowedTypes: imageUploadOptions.allowedTypes });
                const editor = createMarkdownEditor(element, {
                    autosave: {
                        enabled: false,
                    },
                    hideIcons: ["preview", "side-by-side", "fullscreen", "guide"],
                    showIcons: ["heading-2", "code"],
                    toolbar: [
                        {
                            name: "bold",
                            action: EasyMDE.toggleBold,
                            className: "fa fa-bold",
                            title: "Bold",
                        },
                        {
                            name: "italic",
                            action: EasyMDE.toggleItalic,
                            className: "fa fa-italic",
                            title: "Italic",
                        },
                        {
                            name: "header",
                            action: EasyMDE.toggleHeadingSmaller,
                            className: "fas fa-heading",
                            title: "Heading",
                        },
                        {
                            name: "quote",
                            action: EasyMDE.toggleBlockquote,
                            className: "fas fa-quote-right",
                            title: "Quote",
                        },
                        "|",
                        {
                            name: "list",
                            action: EasyMDE.toggleUnorderedList,
                            className: "fas fa-list",
                            title: "List",
                        },
                        {
                            name: "url",
                            action: EasyMDE.drawLink,
                            className: "fas fa-link",
                            title: "Insert URL",
                        },
                        {
                            name: "image",
                            action: EasyMDE.drawImage,
                            className: "fas fa-image",
                            title: "Insert an image",
                        },
                        {
                            name: "upload-file",
                            action: () => {
                                fileInputEl.click();
                            },
                            className: "fa fa-paperclip",
                            title: "Upload image",
                        },
                        {
                            name: "code",
                            action: EasyMDE.toggleCodeBlock,
                            className: "fas fa-code",
                            title: "Insert code",
                        },
                    ],
                });

                editor.element.form.addEventListener("keydown", handleFormSubmissionShortcuts);
                inlineAttachment.editors.codemirror4.attach(editor.codemirror, { ...imageUploadOptions, fileInputEl });

                return [...editors, editor];
            },
            []
        );

        return fullMarkdownEditors;
    },
    stylizeExternalLinks() {
        let internal = location.host.replace("www.", "");
        internal = new RegExp(internal, "i");

        const links = [...document.getElementsByTagName("a")];

        links.forEach((link) => {
            if (internal.test(link.host) || !link.host) return;

            // open external link in new tab
            link.setAttribute("target", "_blank");
            link.setAttribute("rel", "noopener");

            // insert favicon img
            const domain = link.host.split(":")[0];
            const img = document.createElement("img");
            img.src = `https://www.google.com/s2/favicons?domain=${domain}&sz=32`;
            img.className = "link-favicon";
            link.insertBefore(img, link.firstChild);
        });
    },
    initializeImageZoom() {
        Lightense(document.querySelectorAll(".text-body figure img"), {
            time: 100,
            padding: 40,
            offset: 40,
            keyboard: true,
            cubicBezier: "cubic-bezier(.2, 0, .1, 1)",
            background: "rgba(0, 0, 0, .4)",
            zIndex: 1e6,
        });
    },
    blockCommunicationFormsResubmit() {
        [...document.querySelectorAll("form")].filter(isCommunicationForm).forEach((form) => {
            form.addEventListener("submit", () => {
                const submitButton = form.querySelector('button[type="submit"]');

                if (!submitButton) {
                    return;
                }

                submitButton.setAttribute("disabled", true);
            });
        });
    },
    restoreCommentThreadsState() {
        const comments = document.querySelectorAll(".reply, .comment");
        const collapsedSet = getCollapsedCommentThreadsSet();
        for (const comment of comments) {
            if (collapsedSet.has(comment.id)) {
                comment.querySelector(".comment-collapse-stub, .reply-collapse-stub").click();
            }
        }
    },
    initializePostActions() {
        document.querySelectorAll(".js-post-action").forEach((link) => {
            link.addEventListener("click", async (e) => {
                e.preventDefault();

                const confirmMsg = link.dataset.confirm;
                if (confirmMsg && !confirm(confirmMsg)) {
                    return;
                }

                const response = await fetch(link.href, { method: "POST" });
                if (response.redirected) {
                    window.location.href = response.url;
                } else {
                    window.location.reload();
                }
            });
        });
    },
};

export default App;
