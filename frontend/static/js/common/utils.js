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

export const debounce = (func, wait, immediate) => {
    let timeout;
    return function () {
        let context = this;
        let args = arguments;

        clearTimeout(timeout);

        timeout = setTimeout(function () {
            timeout = null;

            if (!immediate) {
                func.apply(context, args);
            }
        }, wait);

        if (immediate && !timeout) {
            func.apply(context, args);
        }
    };
}
