import twemoji from "twemoji";
import SimpleMDE from "simplemde";
import Lightense from "lightense-images";

import "./inline-attachment"
import "./codemirror-4.inline-attachment"

const INITIAL_SYNC_DELAY = 50;

const imageUploadOptions = {
    uploadUrl: imageUploadUrl,
    uploadMethod: "POST",
    uploadFieldName: "media",
    jsonFieldName: "uploaded",
    progressText: "![Загружаю файл...]()",
    urlText: "![]({filename})",
    errorText: "Ошибка при загрузке файла :(",
    extraParams: {
        code: imageUploadCode,
        convert_to: "jpg",
        quality: 90,
    },
};

const App = {
    onCreate() {
        this.initializeThemeSwitcher();
        this.addTargetBlankToExternalLinks();
        this.bindCommentsHotkey();
    },
    onMount() {
        this.initializeImageZoom();
        this.initializeEmojiForPoorPeople();
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
        if (theme !== null) {
            themeSwitch.checked = theme === "dark";
        } else if (window.matchMedia) {
            themeSwitch.checked = window.matchMedia("(prefers-color-scheme: dark)").matches;
        }
    },
    initializeMarkdownEditor() {
        if (this.isMobile()) return; // we don't need fancy features on mobiles
        let allEditors = [];
        const fullMarkdownEditors = document.querySelectorAll(".markdown-editor-full");
        for (let i = 0; i < fullMarkdownEditors.length; i++) {
            let editor = new SimpleMDE({
                element: fullMarkdownEditors[i],
                autoDownloadFontAwesome: false,
                autosave: {
                    enabled: true,
                    delay: 10000, // 10 sec
                    uniqueId: location.pathname,
                },
                hideIcons: ["preview", "side-by-side", "fullscreen", "guide"],
                showIcons: ["heading-2", "code"],
                toolbar: [
                    {
                        name: "bold",
                        action: SimpleMDE.toggleBold,
                        className: "fa fa-bold",
                        title: "Bold",
                    },
                    {
                        name: "italic",
                        action: SimpleMDE.toggleItalic,
                        className: "fa fa-italic",
                        title: "Italic",
                    },
                    {
                        name: "header",
                        action: SimpleMDE.toggleHeadingSmaller,
                        className: "fas fa-heading",
                        title: "Heading",
                    },
                    {
                        name: "quote",
                        action: SimpleMDE.toggleBlockquote,
                        className: "fas fa-quote-right",
                        title: "Quote",
                    },
                    "|",
                    {
                        name: "list",
                        action: SimpleMDE.toggleUnorderedList,
                        className: "fas fa-list",
                        title: "List",
                    },
                    {
                        name: "url",
                        action: SimpleMDE.drawLink,
                        className: "fas fa-link",
                        title: "Insert URL",
                    },
                    {
                        name: "image",
                        action: SimpleMDE.drawImage,
                        className: "fas fa-image",
                        title: "Insert an image",
                    },
                    {
                        name: "code",
                        action: SimpleMDE.toggleCodeBlock,
                        className: "fas fa-code",
                        title: "Insert code",
                    },
                ],
                spellChecker: false,
                forceSync: true,
                tabSize: 4,
            });
            allEditors.push(editor);
            inlineAttachment.editors.codemirror4.attach(editor.codemirror, imageUploadOptions);
        }

        const invisibleMarkdownEditors = document.querySelectorAll(".markdown-editor-invisible");
        for (let i = 0; i < invisibleMarkdownEditors.length; i++) {
            let editor = new SimpleMDE({
                element: invisibleMarkdownEditors[i],
                autoDownloadFontAwesome: false,
                toolbar: false,
                status: false,
                spellChecker: false,
                forceSync: true,
                tabSize: 4,
            });
            allEditors.push(editor);
            inlineAttachment.editors.codemirror4.attach(editor.codemirror, imageUploadOptions);
        }
        return allEditors;
    },
    addTargetBlankToExternalLinks() {
        let internal = location.host.replace("www.", "");
        internal = new RegExp(internal, "i");

        const links = [...document.getElementsByTagName("a")];
        links.forEach(link => {
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
            zIndex: 2147483647,
        });
    },
    bindCommentsHotkey() {
        const commentForm  = document.querySelector('.comment-form-form');
        if (this.isMobile() || !commentForm) { return; }

        commentForm.addEventListener('keydown', (event) => this.handleCommentHotkey(event, commentForm));
    },
    handleCommentHotkey(event, controlElement) {
        if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
            controlElement.submit();
        }
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
    }
};

export default App;
