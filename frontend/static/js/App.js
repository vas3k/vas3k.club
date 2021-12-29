import twemoji from "twemoji";
import EasyMDE from "easymde";
import Lightense from "lightense-images";

import { isCommunicationForm, isMobile } from "./common/utils";
import { imageUploadOptions, createMarkdownEditor, handleFormSubmissionShortcuts } from "./common/markdown-editor";
import { getCollapsedCommentThreadsSet } from "./common/comments";

const INITIAL_SYNC_DELAY = 50;

const App = {
    onCreate() {
        this.initializeThemeSwitcher();
        this.addTargetBlankToExternalLinks();
    },
    onMount() {
        this.initializeImageZoom();
        this.initializeEmojiForPoorPeople();
        this.blockCommunicationFormsResubmit();
        this.restoreCommentThreadsState();

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
            document.body = twemoji.parse(document.body);
        }
    },
    initializeThemeSwitcher() {
        const themeSwitch = document.querySelector('.theme-switcher input[type="checkbox"]');
        const mediaQueryList = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)");

        themeSwitch.addEventListener(
            "change",
            function (e) {
                let theme = "light";
                if (e.target.checked) {
                    theme = "dark";
                }
                document.documentElement.setAttribute("theme", theme);
                localStorage.setItem("theme", theme);
            },
            false
        );

        const theme = localStorage.getItem("theme");
        themeSwitch.checked = theme ? theme === "dark" : mediaQueryList.matches;

        const setFaviconHref = (e) => {
            const svgFavicon = document.querySelector('link[type="image/svg+xml"]');
            const isDark = e.matches;

            if (!theme) {
                themeSwitch.checked = isDark;
            }

            svgFavicon.href = isDark ? "/static/images/favicon/favicon-dark.svg" : "/static/images/favicon/favicon.svg";
        };

        setFaviconHref(mediaQueryList);
        mediaQueryList.addListener(setFaviconHref);
    },

    initializeMarkdownEditor() {
        if (isMobile()) return []; // we don't need fancy features on mobiles

        const fullMarkdownEditors = [...document.querySelectorAll(".markdown-editor-full")].reduce(
            (editors, element) => {
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
                            name: "code",
                            action: EasyMDE.toggleCodeBlock,
                            className: "fas fa-code",
                            title: "Insert code",
                        },
                    ],
                });

                return [...editors, editor];
            },
            []
        );

        const allEditors = fullMarkdownEditors;

        allEditors.forEach((editor) => {
            editor.element.form.addEventListener("keydown", handleFormSubmissionShortcuts);

            inlineAttachment.editors.codemirror4.attach(editor.codemirror, imageUploadOptions);
        });

        return allEditors;
    },
    addTargetBlankToExternalLinks() {
        let internal = location.host.replace("www.", "");
        internal = new RegExp(internal, "i");

        const links = [...document.getElementsByTagName("a")];
        links.forEach((link) => {
            if (internal.test(link.host)) return;

            link.setAttribute("target", "_blank");
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
};

export default App;
