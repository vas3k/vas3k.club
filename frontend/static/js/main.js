import Vue from "vue";

import "../css/index.css";

import "./inline-attachment";
import "./codemirror-4.inline-attachment";

import App from "./App.js";
import ClubApi from "./common/api.service.js";
import { pluralize } from "./common/utils.js";
import { handleCommentThreadCollapseToggle } from "./common/comments.js";
import vSelect from "vue-select";

Vue.component("post-upvote", () => import("./components/PostUpvote.vue"));
Vue.component("post-bookmark", () => import("./components/PostBookmark.vue"));
Vue.component("post-subscription", () => import("./components/PostSubscription.vue"));
Vue.component("post-rsvp", () => import("./components/PostRSVP.vue"));
Vue.component("comment-upvote", () => import("./components/CommentUpvote.vue"));
Vue.component("user-tag", () => import("./components/UserTag.vue"));
Vue.component("people-map", () => import("./components/PeopleMap.vue"));
Vue.component("user-avatar-input", () => import("./components/UserAvatarInput.vue"));
Vue.component("stripe-checkout-button", () => import("./components/StripeCheckoutButton.vue"));
Vue.component("input-length-counter", () => import("./components/InputLengthCounter.vue"));
Vue.component("friend-button", () => import("./components/FriendButton.vue"));
Vue.component("comment-scroll-arrow", () => import("./components/CommentScrollArrow.vue"));
Vue.component("comment-markdown-editor", () => import("./components/MarkdownEditor/MarkdownEditor.vue"));
Vue.component("v-select", vSelect);
Vue.component("tag-select", () => import("./components/TagSelect.vue"));
Vue.component("simple-select", () => import("./components/SimpleSelect.vue"));
Vue.component("reply-form", () => import("./components/ReplyForm.vue"));

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

            // toggle thread visibility
            const collapseItems = comment.querySelectorAll(".thread-collapse-toggle");
            for (let i = 0; i < collapseItems.length; i++) {
                const isVisible = window.getComputedStyle(collapseItems[i]).display !== "none";
                collapseItems[i].style.display = isVisible ? "none" : null;
            }

            // show/hide placeholder with thread length
            const collapseStub =
                comment.querySelector(".comment-collapse-stub") || comment.querySelector(".reply-collapse-stub");
            const wasCollapsed = collapseStub.style.display !== "block";
            collapseStub.style.display = wasCollapsed ? "block" : "none";
            const threadLength = comment.querySelectorAll(".reply").length + 1;
            const pluralForm = pluralize(threadLength, ["комментарий", "комментария", "комментариев"]);
            collapseStub.querySelector(".thread-collapse-length").innerHTML = `${threadLength} ${pluralForm}`;

            handleCommentThreadCollapseToggle(wasCollapsed, comment.id);
            // scroll back to comment if it's outside of the screen
            const commentPosition = comment.getBoundingClientRect();
            if (commentPosition.top < 0) {
                window.scrollBy(0, commentPosition.top);
            }
        },
        showReplyForm(commentId, username, draftKey) {
            this.replyTo = { commentId, username, draftKey }
        },
    },
});
