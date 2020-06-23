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

/**
 * Generate button DOM element
 * @param {string|Element} child
 * @param {Array<string>}classList
 * @return {HTMLButtonElement}
 */
export const generateButton = (child, classList) => {
    const previewBtn = document.createElement('button');
    previewBtn.setAttribute('type', 'button')
    previewBtn.classList.add(...classList)
    previewBtn.appendChild(typeof child === "string" ? document.createTextNode(child) : child);
    return previewBtn;
}
