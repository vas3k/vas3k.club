<template>
    <div>
        <div :class="`battle-comment-prefix battle-comment-prefix-side-${comment.sideSlug}`">
            за «{{ comment.side }}»
        </div>
        <div :class="`block comment comment-type-battle comment-type-battle-side-${comment.sideSlug}`" :id="wrapperId">
            <div class="comment-header">
                <div class="comment-title" v-html="title"></div>
                <a :href="comment.author.profileUrl" class="user user-tiny">
                    <span
                        class="avatar user-avatar"
                        :style="{ backgroundImage: `url(${comment.author.avatar})` }"
                    ></span>
                    <span class="user-name" :class="{ 'user-name-is-banned': comment.author.isBanned }">
                        {{ comment.author.fullName }}
                    </span>
                </a>
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
                <reply-action
                    v-if="canReply"
                    :comment-id="id"
                    :username="comment.author.slug"
                    v-on:reply="$root.showReplyForm"
                />
            </div>
        </div>
        <div class="clearfix"></div>
    </div>
</template>

<script>
import EditAction from "./actions/EditAction.vue";
import DeleteAction from "./actions/DeleteAction.vue";
import ReplyAction from "./actions/ReplyAction.vue";

export default {
    name: "BattleComment",
    components: { EditAction, DeleteAction, ReplyAction },
    props: {
        id: {
            type: String,
            required: true,
        },
        content: {
            type: String,
            required: true,
        },
        title: {
            type: String,
            required: true,
        },
        comment: {
            type: Object,
            required: true,
        },
        canReply: {
            type: Boolean,
            default: true,
        },
        editUrl: String,
        deleteUrl: String,
    },
    computed: {
        wrapperId: function () {
            return `comment-${this.id}`;
        },
    },
};
</script>

<style></style>
