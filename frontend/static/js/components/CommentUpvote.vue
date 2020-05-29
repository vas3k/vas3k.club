<template>
    <a
        :href="url"
        class="upvote"
        :class="{
            'upvote-voted': isVoted && !isDisabled,
            'upvote-disabled': isDisabled,
            'upvote-type-inline': isInline,
            'upvote-type-small': isSmall,
        }"
        @click.prevent="toggle"
    >
        {{ upvotes }}
    </a>
</template>

<script>
import ClubApi from "../common/api.service";

export default {
    name: "CommentUpvote",
    props: {
        comment: {
            type: Object,
            required: true,
        },
        isVotedByDefault: {
            type: Boolean,
            default() {
                return false;
            },
        },
        isInline: {
            type: Boolean,
            default() {
                return false;
            },
        },
        isSmall: {
            type: Boolean,
            default() {
                return false;
            },
        },
        isDisabled: {
            type: Boolean,
            default() {
                return false;
            },
        },
        url: {
            type: String,
            required: true,
        },
    },
    data() {
        return {
            upvotes: this.comment.upvotes,
            isVoted: this.isVotedByDefault,
        };
    },
    methods: {
        toggle() {
            return ClubApi.ajaxify(this.url, (data) => {
                this.upvotes = parseInt(data.comment.upvotes);
                this.isVoted = true;
            });
        },
    },
};
</script>

<style scoped></style>
