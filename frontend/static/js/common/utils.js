import EasyMDE from "easymde";

export const findParentForm = (element) => {
    let form = element.parentElement;

    while (form && form.nodeName !== "FORM") {
        form = form.parentElement;
    }

    return form;
};

export const isCommunicationForm = (form) =>
    ["comment-form-form", "reply-form-form"].reduce(
        (_canSubmit, formClass) => form.classList.contains(formClass) || _canSubmit,
        false
    );

export const pluralize = (count, words) => {
    const cases = [2, 0, 1, 1, 1, 2];
    return words[count % 100 > 4 && count % 100 < 20 ? 2 : cases[Math.min(count % 10, 5)]];
};

export const throttle = (fn, wait) => {
    let inThrottle, lastFn, lastTime;
    return function () {
        const context = this,
            args = arguments;
        if (!inThrottle) {
            fn.apply(context, args);
            lastTime = Date.now();
            inThrottle = true;
        } else {
            clearTimeout(lastFn);
            lastFn = setTimeout(function () {
                if (Date.now() - lastTime >= wait) {
                    fn.apply(context, args);
                    lastTime = Date.now();
                }
            }, Math.max(wait - (Date.now() - lastTime), 0));
        }
    };
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

export function isMobile() {
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
