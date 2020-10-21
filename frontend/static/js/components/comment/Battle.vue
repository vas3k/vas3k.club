<template>
    <div
        class="comment"
        :id="wrapperId"
        :class="{
            'comment-layout-normal': !isPinned,
            'comment-is-pinned comment-layout-block': isPinned,
            'comment-is-new': isNew,
        }"
    >
        <div class="comment-header">
            <author-section
                :avatar-url="comment.author.avatar"
                :profile-url="comment.author.profileUrl"
                :display-name="comment.author.fullName"
                :description="comment.author.position"
                :hat="comment.author.hat"
            >
                <template v-slot:footer>
                    <a :href="anchor">{{ comment.createdAt }}</a>
                </template>
            </author-section>
        </div>
        <div class="comment-rating">
            <comment-upvote
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
        <div class="comment-body">
            <div class="text-body text-body-type-comment" v-html="content"></div>
        </div>
        <div class="comment-footer">
            <delete-action v-if="deleteUrl" :url="deleteUrl" />
            <edit-action v-if="editUrl" :url="editUrl" />
            <reply-action :comment-id="id" :username="comment.author.slug" v-on:reply="$root.showReplyForm" />
        </div>
    </div>
</template>

<script>
import EditAction from "./actions/EditAction.vue";
import DeleteAction from "./actions/DeleteAction.vue";
import ReplyAction from "./actions/ReplyAction.vue";
import AuthorSection from "./author/AuthorSection.vue";

export default {
    name: "BattleComment",
    components: { EditAction, DeleteAction, ReplyAction, AuthorSection },
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
        editUrl: String,
        deleteUrl: String,
        canReply: String,
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

<style></style>
