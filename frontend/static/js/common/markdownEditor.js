import EasyMDE from "easymde";
import ClubApi from "./api.service";

const MARKDOWN_EDITOR_PREVIEW_SHORTCUT = 'Alt-P'
const PREVIEW_PLACEHOLDER_TEXT = `Превью (${MARKDOWN_EDITOR_PREVIEW_SHORTCUT})`;
const PREVIEW_PLACEHOLDER_SIZE = '0.6rem'

const defaultMarkdownEditorOptions = {
    autoDownloadFontAwesome: false,
    spellChecker: false,
    forceSync: true,
    tabSize: 4,
    shortcuts: { togglePreview: null },
}

const asyncPreviewToolbarAction = {
    name: "async-preview",
    action: EasyMDE.togglePreview,
    className: "fa fa-eye",
    title: "Custom Button",
};

/**
 * Initialize EasyMDE editor
 * @param {HTMLElement} element
 * @param {EasyMDE.Options} options
 * @return {EasyMDE}
 */
export function createMarkdownEditor(element, options) {
    const editor = new EasyMDE({
        element,
        ...defaultMarkdownEditorOptions,
        ...options,
        // override options above if the preview feature turned on for the editor
        ...(hasPreview(element) && {
            toolbar: Array.isArray(options.toolbar) ? [
                // if the toolbar is on then the preview icon will be inserted as the first one
                asyncPreviewToolbarAction, ...options.toolbar
            ] : options.toolbar,
            // by default, the preview is turned off at all
            shortcuts: { togglePreview: MARKDOWN_EDITOR_PREVIEW_SHORTCUT },
            previewRender
        }),
    });

    // add the placeholder to the editor only if the toolbar is not activated
    if (hasPreview(element) && options.toolbar === false) {
        addMarkdownEditorPreviewPlaceholder(editor);
    }

    return editor;
}

/**
 * Check whether the element has "preview" functionality or not
 * @param {Element} element
 * @return boolean
 */
function hasPreview(element) {
    return element instanceof Element && element.classList.contains('markdown-editor--preview');
}

/**
 * Add the actionable placeholder to toggle preview
 * @param {EasyMDE} editor
 */
function addMarkdownEditorPreviewPlaceholder(editor) {
    const placeholder = document.createElement('span');
    placeholder.style.position = 'absolute';
    placeholder.style.cursor = "context-menu";
    placeholder.style.fontSize = PREVIEW_PLACEHOLDER_SIZE;
    placeholder.appendChild(document.createTextNode(PREVIEW_PLACEHOLDER_TEXT))
    // allows to preview on click event as well
    placeholder.addEventListener('click', EasyMDE.togglePreview.bind(null, editor))
    editor.element.parentNode.appendChild(placeholder);
}

function previewRender(markdownPlaintext, previewEditor)  {
    // async rendering
    ClubApi.markdownPreview(markdownPlaintext,
        res => setTimeout(() => previewEditor.innerHTML = res, 500));

    return '👨‍💻...';
}
