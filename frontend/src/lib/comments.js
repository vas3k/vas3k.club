import { pluralize } from "./utils";

const COLLAPSED_COMMENTS_LOCAL_STORAGE_KEY = "collapsed-comments";
const WEEK_LENGTH_IN_MS = 7 * 24 * 60 * 60 * 1000;
const COMMENT_PLURAL_FORMS = ["комментарий", "комментария", "комментариев"];

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

export const collapseCommentThread = (comment) => {
    comment.classList.add("thread-collapsed");
    const collapseStub = comment.querySelector(".comment-collapse-stub, .reply-collapse-stub");
    if (collapseStub) {
        const threadLength = comment.querySelectorAll(".reply").length + 1;
        const pluralForm = pluralize(threadLength, COMMENT_PLURAL_FORMS);
        collapseStub.querySelector(".thread-collapse-length").innerHTML = `${threadLength} ${pluralForm}`;
    }
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
