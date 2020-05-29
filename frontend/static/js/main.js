import Vue from "vue";

import "../css/index.css";

import App from "./App.js";
import PostUpvote from "./components/PostUpvote.vue";
import PostSubscription from "./components/PostSubscription.vue";
import CommentUpvote from "./components/CommentUpvote.vue";
import UserTag from "./components/UserTag.vue";
import PeopleMap from "./components/PeopleMap.vue";
import SidebarToggler from "./components/SidebarToggler.vue";
import UserExpertiseWindow from "./components/UserExpertiseWindow.vue";
import UserAvatarInput from "./components/UserAvatarInput.vue";
import ClubApi from "./common/api.service";
Vue.component("post-upvote", PostUpvote);
Vue.component("post-subscription", PostSubscription);
Vue.component("comment-upvote", CommentUpvote);
Vue.component("user-expertise-window", UserExpertiseWindow);
Vue.component("user-tag", UserTag);
Vue.component("people-map", PeopleMap);
Vue.component("user-avatar-input", UserAvatarInput);
Vue.component("sidebar-toggler", SidebarToggler);

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
                textarea.value = value;
                const codeMirrorEditor = textarea.nextElementSibling.CodeMirror;
                codeMirrorEditor.setValue(codeMirrorEditor.getValue() + value);
                codeMirrorEditor.focus();
                codeMirrorEditor.setCursor(codeMirrorEditor.lineCount(), 0);
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
