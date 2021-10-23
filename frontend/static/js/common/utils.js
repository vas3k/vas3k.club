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
}

const COLLAPSED_COMMENTS_LOCAL_STORAGE_KEY = "collapsed-comments";
const WEEK_LENGTH_IN_MS = 7 * 24 * 60 * 60 * 1000;

export const getCollapsedCommentThreadsForTwoWeeks = () => {
    const currentValue = localStorage[COLLAPSED_COMMENTS_LOCAL_STORAGE_KEY];
    const thisWeek = Math.floor(new Date() / WEEK_LENGTH_IN_MS);
    let parsed = {};
    try {
        parsed = JSON.parse(currentValue);
    } catch {}
    return [parsed[thisWeek - 1] ?? [], parsed[thisWeek] ?? []];
};

export const getCollapsedCommentThreadsSet = () => {
    const [lastWeekCollapsedComments, thisWeekCollapsedComments] = getCollapsedCommentThreadsForTwoWeeks();
    return new Set([...lastWeekCollapsedComments, ...thisWeekCollapsedComments]);
};

export const handleCommentThreadCollapseToggle = (wasCollapsed, commentId) => {
    const thisWeek = Math.floor(new Date() / WEEK_LENGTH_IN_MS);
    const lastWeek = thisWeek - 1;
    const [lastWeekCollapsedComments, thisWeekCollapsedComments] = getCollapsedCommentThreadsForTwoWeeks();
    const thisWeekSet = new Set(thisWeekCollapsedComments);
    let lastWeekSet;
    if (wasCollapsed) {
        thisWeekSet.add(commentId);
    } else {
        lastWeekSet = new Set(lastWeekCollapsedComments);
        thisWeekSet.delete(commentId);
        lastWeekSet.delete(commentId);
    }
    localStorage[COLLAPSED_COMMENTS_LOCAL_STORAGE_KEY] = JSON.stringify({
        [thisWeek]: Array.from(thisWeekSet),
        [lastWeek]: lastWeekSet ? Array.from(lastWeekSet) : lastWeekCollapsedComments,
    });
};