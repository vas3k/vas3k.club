import Vue from "vue";

import "../css/index.css";

import App from "./App.js";
import ClubApi from "./common/api.service";

Vue.component("post-upvote", () => import("./components/PostUpvote.vue"));
Vue.component("post-bookmark", () => import("./components/PostBookmark.vue"));
Vue.component("post-subscription", () => import("./components/PostSubscription.vue"));
Vue.component("post-rsvp", () => import("./components/PostRSVP.vue"));
Vue.component("comment-upvote", () => import("./components/CommentUpvote.vue"));
Vue.component("user-expertise-window", () => import("./components/UserExpertiseWindow.vue"));
Vue.component("user-tag", () => import("./components/UserTag.vue"));
Vue.component("people-map", () => import("./components/PeopleMap.vue"));
Vue.component("user-avatar-input", () => import("./components/UserAvatarInput.vue"));
Vue.component("sidebar-toggler", () => import("./components/SidebarToggler.vue"));
Vue.component("stripe-checkout-button", () => import("./components/StripeCheckoutButton.vue"));
Vue.component("input-length-counter", () => import("./components/InputLengthCounter.vue"));

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
    },
    methods: {
        deleteExpertise(event) {
            // FIXME: please refactor this code to a proper list component with ajax CRUD actions
            const href = event.target.getAttribute("href");
            if (href == null) return;
            return ClubApi.ajaxify(href, (data) => {
                if (data.status === "deleted") {
                    document.getElementById("expertise-" + data.expertise.expertise).outerHTML = "";
                }
            });
        },
        showReplyForm(commentId, username, withSelection) {
            // First, hide all other reply forms
            const replyForms = document.querySelectorAll(".reply-form-form");
            for (let i = 0; i < replyForms.length; i++) {
                // replyForms[i].removeEventListener('keydown', handleCommentHotkey); // FIXME???
                replyForms[i].style.display = "none";
            }

            // Then show one for commentId
            const commentReplyForm = document.getElementById("reply-form-" + commentId);
            // commentReplyForm.addEventListener('keydown', (event) => handleCommentHotkey(event, commentReplyForm));  // FIXME???
            commentReplyForm.style.display = null;

            // Define helper function
            function appendMarkdownTextareaValue(textarea, value) {
                textarea.focus(); // on mobile
                textarea.value = textarea.value + value;

                // On mobile the next element sibling is undefined
                if (textarea.nextElementSibling) {
                    const codeMirrorEditor =
                        textarea.nextElementSibling.CodeMirror ||
                        textarea.nextElementSibling.querySelector(".CodeMirror").CodeMirror;
                    if (codeMirrorEditor !== undefined) {
                        codeMirrorEditor.setValue(codeMirrorEditor.getValue() + value);
                        codeMirrorEditor.focus();
                        codeMirrorEditor.setCursor(codeMirrorEditor.lineCount(), 0);
                    }
                }
            }

            // Add username to reply
            const commentReplyTextarea = commentReplyForm.querySelector("textarea");
            if (username !== null && username !== "") {
                appendMarkdownTextareaValue(commentReplyTextarea, "@" + username + ", ");
            }

            // Add selected text as quote
            if (withSelection) {
                const selectedText = window.getSelection().toString();
                if (selectedText !== null && selectedText !== "") {
                    appendMarkdownTextareaValue(commentReplyTextarea, "\n> " + selectedText + "\n\n");
                }
            }

            appendMarkdownTextareaValue(commentReplyTextarea, "");
        },
    },
});
