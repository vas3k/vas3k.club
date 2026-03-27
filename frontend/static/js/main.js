import Vue from "vue";

import "../css/index.css";

import "./inline-attachment";
import "./codemirror-4.inline-attachment";

import App from "./App.js";
import ClubApi from "./common/api.service.js";
import { handleCommentThreadCollapseToggle, collapseCommentThread } from "./common/comments.js";
import vSelect from "vue-select";

Vue.component("post-upvote", () => import("./components/PostUpvote.vue"));
Vue.component("post-bookmark", () => import("./components/PostBookmark.vue"));
Vue.component("post-rsvp", () => import("./components/PostRSVP.vue"));
Vue.component("post-toc", () => import("./components/PostToC.vue"));
Vue.component("comment-upvote", () => import("./components/CommentUpvote.vue"));
Vue.component("user-tag", () => import("./components/UserTag.vue"));
Vue.component("people-map", () => import("./components/PeopleMap.vue"));
Vue.component("user-avatar-input", () => import("./components/UserAvatarInput.vue"));
//Vue.component("stripe-checkout-button", () => import("./components/StripeCheckoutButton.vue"));
Vue.component("input-length-counter", () => import("./components/InputLengthCounter.vue"));
Vue.component("friend-button", () => import("./components/FriendButton.vue"));
Vue.component("comment-scroll-arrow", () => import("./components/CommentScrollArrow.vue"));
Vue.component("comment-markdown-editor", () => import("./components/MarkdownEditor/MarkdownEditor.vue"));
Vue.component("toggle", () => import("./components/Toggle.vue"));
Vue.component("clicker", () => import("./components/Clicker.vue"));
Vue.component("v-select", vSelect);
Vue.component("tag-select", () => import("./components/TagSelect.vue"));
Vue.component("simple-select", () => import("./components/SimpleSelect.vue"));
Vue.component("reply-form", () => import("./components/ReplyForm.vue"));
Vue.component("theme-switcher", () => import("./components/ThemeSwitcher.vue"));
Vue.component("location-select", () => import("./components/LocationSelect.vue"));

// Since our pages have user-generated content, any fool can insert "{{" on the page and break it.
// We have no other choice but to completely turn off template matching and leave it on only for components.
const noDelimiter = { replace: function () {} };

new Vue({
    el: "#app",
    delimiters: [noDelimiter, noDelimiter], // disable templates
    created() {
        App.onCreate();
    },
    mounted() {
        App.onMount();
    },
    data: {
        shownWindow: null,
        replyTo: null,
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

// Отдельный инстанс для футера
new Vue({
    el: "#footer",
});
