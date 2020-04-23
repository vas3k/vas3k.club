function redirect(url) {
    location.href = url;
}

function ajaxify(e, callback) {
    e.preventDefault();
    e.stopPropagation();

    const href = e.target.getAttribute("href");
    if (href == null) return;

    const params = {
        method: "POST",
        credentials: "include",
    };
    fetch(href + "?is_ajax=true", params)
        .then((response) => {
            return response.json();
        })
        .then((data) => {
            callback(e, data);
        });
}

function postUpvoted(e, data) {
    const counter = e.target;
    counter.innerHTML = data.post.upvotes;
    counter.classList.add("upvote-voted");
}

function commentUpvoted(e, data) {
    const counter = e.target;
    counter.innerHTML = data.comment.upvotes;
    counter.classList.add("upvote-voted");
}

function toggleUserTag(e, data) {
    const tag = e.target;
    if (data.status === "created") {
        tag.classList.add("user-tag-active");
        tag.style.backgroundColor = data.tag.color;
    }

    if (data.status === "deleted") {
        tag.classList.remove("user-tag-active");
        tag.style.backgroundColor = null;
    }
}

function onExpertiseSelectionChanged(e) {
    if (e.target.value === "custom") {
        e.target.style.display = "none";
        document.getElementById("edit-expertise-custom").style.display = "block";
    }
}

function toggleUserExpertise(e, data) {
    if (data.status === "created") {
        // TODO: this
        // document.getElementById("expertises").innerHTML = "<big>" + data.expertise.name + "</big>";
    }

    if (data.status === "deleted") {
        document.getElementById("expertise-" + data.expertise.expertise).outerHTML = "";
    }
}

function isMobile() {
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

function closeWindow(e) {
    e.target.parentNode.parentNode.style.display = "none";
}

function showReplyForm(commentId, username, withSelection) {
    // First, hide all other reply forms
    const replyForms = document.querySelectorAll(".reply-form");
    for (let i = 0; i < replyForms.length; i++) {
        replyForms[i].style.display = "none";
    }

    // Then show one for commentId
    const commentReplyForm = document.getElementById("reply-form-" + commentId);
    commentReplyForm.style.display = null;

    // Add username to reply
    const commentReplyTextarea = commentReplyForm.querySelector("textarea");
    if (username !== null && username !== "") {
        appendMarkdownTextareaValue(commentReplyTextarea, "@" + username + ", ");
    }

    // Add selected text as quote
    if (withSelection) {
        const selectedText = window.getSelection().toString();
        if (selectedText !== null && selectedText !== "") {
            appendMarkdownTextareaValue(commentReplyTextarea, "\n> " + selectedText + "\n\n");
        }
    }

    appendMarkdownTextareaValue(commentReplyTextarea, "");
}

function appendMarkdownTextareaValue(textarea, value) {
    const codeMirrorEditor = textarea.nextElementSibling.CodeMirror;
    codeMirrorEditor.setValue(codeMirrorEditor.getValue() + value);
    codeMirrorEditor.focus();
    codeMirrorEditor.setCursor(codeMirrorEditor.lineCount(), 0);
}

function initializeThemeSwitcher() {
    const themeSwitch = document.querySelector('.theme-switcher input[type="checkbox"]');

    themeSwitch.addEventListener("change", function (e) {
        let theme = 'light';
        if (e.target.checked) {
            theme = 'dark';
        }
        document.documentElement.setAttribute('theme', theme);
        localStorage.setItem('theme', theme);
    }, false);

    const theme = localStorage.getItem('theme');
    if (theme !== null) {
        themeSwitch.checked = (theme === 'dark');
    }
}

function initializeMarkdownEditor() {
    if (isMobile()) return; // we don't need fancy features on mobiles

    const imageUploadOptions = {
        uploadUrl: document.currentScript.getAttribute("imageUploadUrl"),
        uploadMethod: "POST",
        uploadFieldName: "media",
        jsonFieldName: "uploaded",
        progressText: "![Загружаю файл...]()",
        urlText: "![]({filename})",
        errorText: "Ошибка при загрузке файла :(",
        extraParams: {
            "code": document.currentScript.getAttribute("imageUploadCode")
        }
    };

    const fullMarkdownEditors = document.querySelectorAll(".markdown-editor-full");
    for (let i = 0; i < fullMarkdownEditors.length; i++) {
        let editor = new SimpleMDE({
            element: fullMarkdownEditors[i],
            autoDownloadFontAwesome: false,
            autosave: {
                enabled: true,
                delay: 10000, // 10 sec
                uniqueId: location.pathname
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
            tabSize: 4
        });
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
            tabSize: 4
        });
        inlineAttachment.editors.codemirror4.attach(editor.codemirror, imageUploadOptions);
    }
}

function addTargetBlankToExternalLinks() {
    let internal = location.host.replace("www.", "");
    internal = new RegExp(internal, "i");

    let a = document.getElementsByTagName('a');
    for (let i = 0; i < a.length; i++) {
        let href = a[i].host;
        if (!internal.test(href)) {
            a[i].setAttribute('target', '_blank');
        }
    }
}

function initializeImageZoom() {
    Lightense(document.querySelectorAll(".post figure img"), {
        time: 100,
        padding: 40,
        offset: 40,
        keyboard: true,
        cubicBezier: 'cubic-bezier(.2, 0, .1, 1)',
        background: 'rgba(0, 0, 0, .4)',
        zIndex: 2147483647
    });
}

addTargetBlankToExternalLinks();
initializeThemeSwitcher();
initializeMarkdownEditor();
initializeImageZoom();
