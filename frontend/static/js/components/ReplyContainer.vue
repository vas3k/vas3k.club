<template>
    <div>
        <form method="post" :action="createCommentUrl" class="form reply-form-form" id="comment-reply-form" v-if="replyTo !== null">
            <input type="hidden" name="post_comment_order" :value="commentOrder">
            <input type="hidden" name="reply_to_id" :value="replyTo.commentId">

            <div class="reply-form">
                <div class="reply-form-avatar">
                    <div class="avatar"><img :src="avatarUrl" :alt="avatarAlt" loading="lazy" /></div>
                </div>

                <div class="reply-form-body">
                    <comment-markdown-editor>
                        <textarea name="text" maxlength="20000" placeholder="Напишите ответ..." class="markdown-editor-invisible" required>
                        </textarea>
                    </comment-markdown-editor>
                </div>

                <div class="reply-form-button">
                    <button type="submit" class="button button-small">Отправить</button>
                </div>
            </div>
        </form>

        <slot></slot>
    </div>
</template>

<script>
export default {
    name: 'ReplyContainer',
    props: ["replyTo", "commentOrder", "avatarUrl", "username", "createCommentUrl"],
    computed: {
        avatarAlt: function() {
            return `Аватар ${this.$props.username}`
        }
    },
    data: function () {
        return {
            drafts: {},
            editor: undefined
        }
    },
    watch: {
        replyTo: async function(newReplyTo, oldReplyTo) {
            this.replyTo = newReplyTo;
            if (oldReplyTo) {
                this.saveDraft(oldReplyTo.commentId);
            }
        }
    },
    updated: function() {
        if (this.replyTo !== null && this.getEditor()) {
            // move the reply form under the comment
            const replyForm = this.$el.querySelector("#comment-reply-form")
            const newCommentEl = this.$el.querySelector(`#comment-${this.replyTo.commentId}`)
            newCommentEl.after(replyForm)
            const editor = this.getEditor()

            if (this.replyTo.commentId in this.drafts) {
                const text = this.drafts[this.replyTo.commentId]
                const textarea = replyForm.querySelector("textarea")
                textarea.value = text
                editor.setValue(text)
            } else {
                this.getEditor().setValue("")
                // Add username to reply
                const username = this.replyTo.username
                if (username !== null && username !== "") {
                    this.appendMarkdownTextareaValue("@" + username + ", ");
                }

                // Add selected text as quote
                const withSelection = this.replyTo.withSelection
                if (withSelection) {
                    const selectedText = window.getSelection().toString();
                    if (selectedText !== null && selectedText !== "") {
                        this.appendMarkdownTextareaValue("\n> " + selectedText + "\n\n");
                    }
                }

                this.appendMarkdownTextareaValue("");
            }

            editor.focus()
            editor.execCommand("goDocEnd")

            replyForm.scrollIntoView({behavior: "smooth", block: "center"})
        }
    },
    methods: {
        appendMarkdownTextareaValue: function(value) {
            const textarea = this.$el.querySelector("#comment-reply-form textarea")
            textarea.focus(); // on mobile
            textarea.value = textarea.value + value;

            const editor = this.getEditor()
            if (editor) {
                editor.setValue(editor.getValue() + value);
            }
        },
        saveDraft: function(commentId) {
            const editor = this.getEditor()
            const text = editor.getValue()
            if (editor && text.length > 0) {
                this.drafts[commentId] = editor.getValue();
            }
        },
        getEditor: function() {
            if (!this.editor) {
                const textarea = this.$el.querySelector("#comment-reply-form textarea")

                textarea.focus(); // on mobile
                if (!textarea.nextElementSibling) {
                    console.error(`Couldn't find CodeMirror editor for ${textarea}`)
                    return
                }

                const codeMirrorEditor = textarea.nextElementSibling.CodeMirror ||
                    textarea.nextElementSibling.querySelector(".CodeMirror").CodeMirror;

                if (codeMirrorEditor === undefined) {
                    console.error(`Couldn't find CodeMirror editor for ${textarea}`)
                }

                this.editor = codeMirrorEditor
            }

            return this.editor
        }
    }
}
</script>
