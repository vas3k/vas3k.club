import { createApp, defineAsyncComponent } from "vue";

import "../css/index.css";

import App from "./App.js";
import { handleCommentThreadCollapseToggle, collapseCommentThread } from "./common/comments.js";
import vSelect from "vue-select";

const app = createApp({
    data() {
        return {
            shownWindow: null,
            replyTo: null,
        };
    },
    created() {
        App.onCreate();
    },
    mounted() {
        App.onMount();
    },
    methods: {
        toggleCommentThread(event) {
            const comment = event.target.closest(".reply") || event.target.closest(".comment");
            if (comment === null) {
                return;
            }

            // toggle thread visibility via CSS class (no forced reflows)
            const wasCollapsed = !comment.classList.contains("thread-collapsed");
            if (wasCollapsed) {
                collapseCommentThread(comment);
            } else {
                comment.classList.remove("thread-collapsed");
            }

            handleCommentThreadCollapseToggle(wasCollapsed, comment.id);
            // scroll back to comment if it's outside of the screen
            const commentPosition = comment.getBoundingClientRect();
            if (commentPosition.top < 0) {
                window.scrollBy(0, commentPosition.top);
            }
        },
        showReplyForm(commentId, username, draftKey) {
            this.replyTo = { commentId, username, draftKey };
        },
    },
});

app.config.compilerOptions.delimiters = ["[[", "]]"];

app.component(
    "post-upvote",
    defineAsyncComponent(() => import("./components/PostUpvote.vue"))
);
app.component(
    "post-bookmark",
    defineAsyncComponent(() => import("./components/PostBookmark.vue"))
);
app.component(
    "post-rsvp",
    defineAsyncComponent(() => import("./components/PostRSVP.vue"))
);
app.component(
    "post-toc",
    defineAsyncComponent(() => import("./components/PostToC.vue"))
);
app.component(
    "comment-upvote",
    defineAsyncComponent(() => import("./components/CommentUpvote.vue"))
);
app.component(
    "user-tag",
    defineAsyncComponent(() => import("./components/UserTag.vue"))
);
app.component(
    "people-map",
    defineAsyncComponent(() => import("./components/PeopleMap.vue"))
);
app.component(
    "user-avatar-input",
    defineAsyncComponent(() => import("./components/UserAvatarInput.vue"))
);
app.component(
    "stripe-checkout-button",
    defineAsyncComponent(() => import("./components/StripeCheckoutButton.vue"))
);
app.component(
    "input-length-counter",
    defineAsyncComponent(() => import("./components/InputLengthCounter.vue"))
);
app.component(
    "friend-button",
    defineAsyncComponent(() => import("./components/FriendButton.vue"))
);
app.component(
    "comment-scroll-arrow",
    defineAsyncComponent(() => import("./components/CommentScrollArrow.vue"))
);
app.component(
    "comment-markdown-editor",
    defineAsyncComponent(() => import("./components/MarkdownEditor/MarkdownEditor.vue"))
);
app.component(
    "toggle",
    defineAsyncComponent(() => import("./components/Toggle.vue"))
);
app.component(
    "clicker",
    defineAsyncComponent(() => import("./components/Clicker.vue"))
);
app.component("v-select", vSelect);
app.component(
    "tag-select",
    defineAsyncComponent(() => import("./components/TagSelect.vue"))
);
app.component(
    "simple-select",
    defineAsyncComponent(() => import("./components/SimpleSelect.vue"))
);
app.component(
    "reply-form",
    defineAsyncComponent(() => import("./components/ReplyForm.vue"))
);
app.component(
    "theme-switcher",
    defineAsyncComponent(() => import("./components/ThemeSwitcher.vue"))
);
app.component(
    "location-select",
    defineAsyncComponent(() => import("./components/LocationSelect.vue"))
);

app.mount("#app");

const footer = createApp({});
footer.component(
    "theme-switcher",
    defineAsyncComponent(() => import("./components/ThemeSwitcher.vue"))
);
footer.mount("#footer");
