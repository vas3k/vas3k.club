<template>
    <form method="post" :action="createCommentUrl" class="form reply-form-form" id="comment-reply-form" v-if="replyTo !== null">
        <input type="hidden" name="post_comment_order" :value="commentOrder">
        <input type="hidden" name="reply_to_id" :value="replyTo.commentId">

        <div class="reply-form">
            <div class="reply-form-avatar">
                <div class="avatar"><img :src="avatarUrl" :alt="avatarAlt" loading="lazy" /></div>
            </div>

            <div class="reply-form-body">
                <comment-markdown-editor
                    v-model="text"
                    :focused="isFocused"
                    v-on:blur="handleBlur"
                >
                </comment-markdown-editor>
            </div>

            <div class="reply-form-button">
                <button type="submit" class="button button-small">Отправить</button>
            </div>
        </div>
    </form>
</template>

<script>
export default {
    name: 'ReplyForm',
    props: {
        // type { commentId: string, username: string, draftKey?: string }
        replyTo: {
            type: Object
        },
        commentOrder: {
            type: String,
            required: true
        },
        avatarUrl: {
            type: String,
            required: true
        },
        username: {
            type: String,
            required: true
        },
        createCommentUrl: {
            type: String,
            required: true
        },
    },
    computed: {
        avatarAlt: function() {
            return `Аватар ${this.$props.username}`
        }
    },
    data: function () {
        return {
            drafts: {},
            editor: undefined,
            text: "",
            isFocused: false,
        }
    },
    watch: {
        replyTo: function(newReplyTo, oldReplyTo) {
            if (oldReplyTo) {
                this.saveDraft(getDraftKey(oldReplyTo));
            }

            const newDraftKey = getDraftKey(newReplyTo)
            if (newDraftKey in this.drafts) {
                this.text = this.drafts[newDraftKey]
            } else {
                this.text = "@" + newReplyTo.username + ", "
            }

            this.replyTo = newReplyTo;
            this.isFocused = true
        }
    },
    mounted: function() {
        this.isFocused = true
    },
    updated: function() {
        if (this.replyTo !== null) {
            // move the reply form under the comment
            const replyForm = document.getElementById("comment-reply-form")
            const newCommentEl = document.getElementById(`comment-${this.replyTo.commentId}`)
            if (replyForm.previousSibling !== newCommentEl) {
                newCommentEl.after(replyForm)
                replyForm.scrollIntoView({ behavior: "smooth", block: "center" })
            }
        }
    },
    methods: {
        saveDraft: function(commentId) {
            if (this.text.length > 0) {
                this.drafts[commentId] = this.text;
            }
        },
        handleBlur: function(textValue) {
            this.isFocused = false
            this.text = textValue
        }
    }
}

function getDraftKey(replyTo) {
    return replyTo?.draftKey || replyTo?.commentId
}
</script>
