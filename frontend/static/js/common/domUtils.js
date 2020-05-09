export const findParentForm = (element) => {
    let form = element.parentElement;

    while (form && form.nodeName !== "FORM") {
        form = form.parentElement;
    }

    return form;
};
