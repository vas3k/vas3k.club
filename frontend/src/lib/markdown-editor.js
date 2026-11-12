import EasyMDE from "easymde";
import { findParentForm, isCommunicationForm, isMobile } from "./utils";

const defaultMarkdownEditorOptions = {
    autoDownloadFontAwesome: false,
    previewImagesInEditor: true,
    spellChecker: false,
    forceSync: true,
    status: false,
    tabSize: 4,
};
export function createMarkdownEditor(element, options) {
    const mobile = isMobile();
    const editor = new EasyMDE({
        element,
        ...defaultMarkdownEditorOptions,
        inputStyle: mobile ? "contenteditable" : "textarea",
        nativeSpellcheck: true,
        styleSelectedText: !mobile,
        ...options,
    });

    if (mobile) {
        editor.codemirror.setOption("autocorrect", true);
        editor.codemirror.setOption("autocapitalize", "sentences");
    }

    editor.codemirror.setOption("singleCursorHeightPerLine", false);
    editor.codemirror.on("change", () => {
        element.dispatchEvent(new Event("input", { bubbles: true }));
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

export const imageUploadOptions = {
    uploadUrl: window.imageUploadUrl,
    uploadMethod: "POST",
    uploadFieldName: "media",
    jsonFieldName: "uploaded",
    progressText: "![Загружаю файл...]()",
    urlText: "![]({filename})",
    errorText: "Ошибка при загрузке файла :(",
    allowedTypes: [
        "image/jpeg",
        "image/png",
        "image/webp",
        "image/jpg",
        "image/gif",
        "video/mp4",
        "video/quicktime", // .mov (macOS' default record format)
    ],
    extraHeaders: {
        Accept: "application/json",
    },
    extraParams: {
        code: window.imageUploadCode,
    },
};

export function createFileInput({ allowedTypes = [] }) {
    const fileInput = document.createElement("input");
    fileInput.type = "file";
    fileInput.name = "attach-image"
    if (allowedTypes) {
        fileInput.accept = allowedTypes.join();
    }

    return fileInput;
}

export function handleFormSubmissionShortcuts(event) {
    const isEnter = event.key === "Enter";
    const isCtrlOrCmd = event.ctrlKey || event.metaKey;
    const isEnterAndCmd = isEnter && isCtrlOrCmd;
    if (!isEnterAndCmd || event.isComposing) {
        return;
    }

    const form = findParentForm(event.target);
    if (!form || !isCommunicationForm(form)) {
        return;
    }

    event.preventDefault();
    const submitButton = form.querySelector('button[type="submit"], input[type="submit"]');
    if (submitButton?.disabled) return;

    form.requestSubmit(submitButton || undefined);
}
