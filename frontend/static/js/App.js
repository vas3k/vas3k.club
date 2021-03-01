import twemoji from "twemoji";
import EasyMDE from "easymde";
import Lightense from "lightense-images";

import "./inline-attachment";
import "./codemirror-4.inline-attachment";

import { findParentForm, isCommunicationForm } from "./common/domUtils";

const INITIAL_SYNC_DELAY = 50;

const imageUploadOptions = {
    uploadUrl: imageUploadUrl,
    uploadMethod: "POST",
    uploadFieldName: "media",
    jsonFieldName: "uploaded",
    progressText: "![Загружаю файл...]()",
    urlText: "![]({filename})",
    errorText: "Ошибка при загрузке файла :(",
    allowedTypes: [
        "image/jpeg",
        "image/png",
        "image/jpg",
        "image/gif",
        "video/mp4",
        "video/quicktime", // .mov (macOS' default record format)
    ],
    extraHeaders: {
        Accept: "application/json",
    },
    extraParams: {
        code: imageUploadCode,
    },
};

const defaultMarkdownEditorOptions = {
    autoDownloadFontAwesome: false,
    spellChecker: false,
    nativeSpellcheck: true,
    forceSync: true,
    status: false,
    inputStyle: "contenteditable",
    tabSize: 4,
};

/**
 * Initialize EasyMDE editor
 *
 * @param {Element} element
 * @param {EasyMDE.Options} options
 * @return {EasyMDE}
 */
function createMarkdownEditor(element, options) {
    const editor = new EasyMDE({
        element,
        ...defaultMarkdownEditorOptions,
        ...options,
    });

    // overriding default CodeMirror shortcuts
    editor.codemirror.addKeyMap({
        Home: "goLineLeft", // move the cursor to the left side of the visual line it is on
        End: "goLineRight", // move the cursor to the right side of the visual line it is on
    });

    // adding ability to fire events on the hidden element
    if (element.dataset.listen) {
        const events = element.dataset.listen.split(" ");
        events.forEach((event) => {
            try {
                editor.codemirror.on(event, (e) => e.getTextArea().dispatchEvent(new Event(event)));
            } catch (e) {
                console.warn("Invalid event provided", event);
            }
        });
    }

    return editor;
}

const App = {
    onCreate() {
        this.initializeThemeSwitcher();
        this.addTargetBlankToExternalLinks();
    },
    onMount() {
        this.initializeImageZoom();
        this.initializeEmojiForPoorPeople();
        this.blockCommunicationFormsResubmit();

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
        if (this.isMobile()) return []; // we don't need fancy features on mobiles

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

        const invisibleMarkdownEditors = [...document.querySelectorAll(".markdown-editor-invisible")].reduce(
            (editors, element) => {
                const editor = createMarkdownEditor(element, {
                    toolbar: false,
                });

                return [...editors, editor];
            },
            []
        );

        const allEditors = fullMarkdownEditors.concat(invisibleMarkdownEditors);

        allEditors.forEach((editor) => {
            editor.element.form.addEventListener("keydown", (e) => {
                const isEnter = event.key === "Enter";
                const isCtrlOrCmd = event.ctrlKey || event.metaKey;
                const isEnterAndCmd = isEnter && isCtrlOrCmd;
                if (!isEnterAndCmd) {
                    return;
                }

                const form = findParentForm(e.target);
                if (!form || !isCommunicationForm(form)) {
                    return;
                }

                form.submit();
            });

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
    isMobile() {
        const userAgent = navigator.userAgent || navigator.vendor || window.opera;

        // Windows Phone must come first because its UA also contains "Android"
        if (/windows phone/i.test(userAgent)) {
            return true;
        }

        if (/android/i.test(userAgent)) {
            return true;
        }

        // iOS detection from: http://stackoverflow.com/a/9039885/177710
        if (/iPad|iPhone|iPod/.test(userAgent) && !window.MSStream) {
            return true;
        }

        return false;
    },
};

export default App;
