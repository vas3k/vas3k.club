import EasyMDE from "easymde";
import { findParentForm, isCommunicationForm } from "./utils";

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
export function createMarkdownEditor(element, options) {
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

export const imageUploadOptions = {
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
    if (!isEnterAndCmd) {
        return;
    }

    const form = findParentForm(event.target);
    if (!form || !isCommunicationForm(form)) {
        return;
    }

    form.submit();
}
