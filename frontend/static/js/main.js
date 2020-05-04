import Vue from "vue";

import "../css/index.css";

import App from "./App.js";
import UserTag from "./components/UserTag.vue";

function ajaxify(e, callback) {
    e.preventDefault();
    e.stopPropagation();

    const href = e.target.getAttribute("href");
    if (href == null) return;

    const params = {
        method: "POST",
        credentials: "include",
    };
    fetch(href + "?is_ajax=true", params)
        .then((response) => {
            return response.json();
        })
        .then((data) => {
            callback(e, data);
        });
}

function postUpvoted(e, data) {
    const counter = e.target;
    counter.innerHTML = data.post.upvotes;
    counter.classList.add("upvote-voted");
}

function commentUpvoted(e, data) {
    const counter = e.target;
    counter.innerHTML = data.comment.upvotes;
    counter.classList.add("upvote-voted");
}

function onExpertiseSelectionChanged(e) {
    if (e.target.value === "custom") {
        e.target.style.display = "none";
        document.getElementById("edit-expertise-custom").style.display = "block";
    }
}

function toggleUserExpertise(e, data) {
    if (data.status === "created") {
        // TODO: this
        // document.getElementById("expertises").innerHTML = "<big>" + data.expertise.name + "</big>";
    }

    if (data.status === "deleted") {
        document.getElementById("expertise-" + data.expertise.expertise).outerHTML = "";
    }
}

window.addEventListener("load", () => {
    Vue.component("user-tag", UserTag);

    new Vue({
        el: "#app",
        created() {
            App.onCreate();
        },
        mounted() {
            App.onMount();
        },
        methods: {
            closeWindow(event) {
                event.target.parentNode.parentNode.style.display = "none";
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
                    textarea.value = value;
                    textarea.focus();  // on mobile
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
            }
        }
    });
});

export {
    ajaxify, postUpvoted, commentUpvoted, toggleUserExpertise
};
