<template>
    <div class="reply" :id="wrapperId" :class="{ 'comment-is-new': isNew }">
        <div class="reply-author">
            <a :href="comment.author.profileUrl">
                <span class="avatar user-avatar" :style="{ backgroundImage: `url(${comment.author.avatar})` }"></span>
            </a>
        </div>
        <div class="reply-body">
            <div class="text-body text-body-type-comment" v-html="content"></div>
        </div>
        <div class="reply-rating">
            <comment-upvote
                is-inline
                :initial-upvotes="comment.upvote.count"
                :hours-to-retract-vote="comment.upvote.hoursToRetract"
                :upvote-url="comment.upvote.upvoteUrl"
                :retract-vote-url="comment.upvote.retractVoteUrl"
                :initial-is-voted="comment.upvote.isVoted"
                :initial-upvote-timestamp="comment.upvote.upvotedAt"
                :is-disabled="comment.upvote.isDisabled"
            >
            </comment-upvote>
        </div>
        <div class="reply-footer">
            <span
                class="comment-reply-button"
                v-on:click="$root.showReplyForm(comment.replyTo, comment.author.slug, true)"
            >
                <span v-if="comment.author.isBanned" class="user-name-is-banned">
                    —&nbsp;&nbsp;{{ comment.author.slug }}&nbsp;&nbsp;<i class="fas fa-reply"></i>
                </span>
            </span>

            <a :href="anchor" class="comment-reply-date">
                {{ comment.createdAt }}
            </a>

            <delete-action v-if="deleteUrl" :url="deleteUrl" />
            <edit-action v-if="editUrl" :url="editUrl" />
        </div>
    </div>
</template>

<script>
import EditAction from "./actions/EditAction.vue";
import DeleteAction from "./actions/DeleteAction.vue";

export default {
    name: "Reply",
    components: { EditAction, DeleteAction },
    props: {
        id: {
            type: String,
            required: true,
        },
        content: {
            type: String,
            required: true,
        },
        comment: {
            type: Object,
            required: true,
        },
        isNew: {
            type: Boolean,
            default: false,
        },
        isBanned: {
            type: Boolean,
            default: false,
        },
        pinUrl: String,
        editUrl: String,
        deleteUrl: String,
    },
    computed: {
        wrapperId: function () {
            return `comment-${this.id}`;
        },
        anchor: function () {
            return this.id && `#${this.wrapperId}`;
        },
    },
};
</script>
