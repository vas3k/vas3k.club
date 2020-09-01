import EasyMDE from "easymde";
import ClubApi from "./api.service";

const MARKDOWN_EDITOR_PREVIEW_SHORTCUT = 'Alt-P';
const PREVIEW_PLACEHOLDER_TEXT = `Превью (${MARKDOWN_EDITOR_PREVIEW_SHORTCUT})`;
const PREVIEW_PLACEHOLDER_SIZE = 0.6;
const PREVIEW_PLACEHOLDER_SIZE_UNIT = 'rem';

const defaultMarkdownEditorOptions = {
    autoDownloadFontAwesome: false,
    spellChecker: false,
    forceSync: true,
    status: false,
    inputStyle: "textarea",
    tabSize: 4,
    shortcuts: { togglePreview: null },
};

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

    // overriding default CodeMirror shortcuts
    editor.codemirror.addKeyMap({
        'Home': 'goLineLeft', // move the cursor to the left side of the visual line it is on
        'End': 'goLineRight', // move the cursor to the right side of the visual line it is on
    });

    // adding ability to fire events on the hidden element
    if (element.dataset.listen) {
        const events = element.dataset.listen.split(' ');
        events.forEach(event => {
            try {
                editor.codemirror.on(event, e => e.getTextArea().dispatchEvent(new Event(event)));
            } catch (e) {
                console.warn('Invalid event provided', event);
            }
        });
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
    placeholder.style.cursor = "pointer";
    placeholder.style.fontSize = String(PREVIEW_PLACEHOLDER_SIZE+PREVIEW_PLACEHOLDER_SIZE_UNIT);
    placeholder.style.lineHeight = String(PREVIEW_PLACEHOLDER_SIZE * 2 + PREVIEW_PLACEHOLDER_SIZE_UNIT);
    placeholder.appendChild(document.createTextNode(PREVIEW_PLACEHOLDER_TEXT));
    // allows to preview on click event as well
    placeholder.addEventListener('click', EasyMDE.togglePreview.bind(null, editor));
    editor.element.parentNode.appendChild(placeholder);
}

function previewRender(markdownPlaintext, previewEditor)  {
    // async rendering
    ClubApi.markdownPreview(markdownPlaintext,
        res => setTimeout(() => previewEditor.innerHTML = res, 500));

    return '👨‍💻...';
}
