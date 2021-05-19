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
    return words[ (count % 100 > 4 && count % 100 < 20) ? 2 : cases[ Math.min(count % 10, 5)] ];
}
