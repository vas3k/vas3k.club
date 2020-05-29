<template>
    <a
        :href="url"
        class="upvote"
        :class="{
            'upvote-voted': isVoted && !isDisabled,
            'upvote-disabled': isDisabled,
            'upvote-type-inline': isInline,
        }"
        @click.prevent="toggle"
    >
        {{ upvotes }}
    </a>
</template>

<script>
import ClubApi from "../common/api.service";

export default {
    name: "PostUpvote",
    props: {
        post: {
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
            upvotes: this.post.upvotes,
            isVoted: this.isVotedByDefault,
        };
    },
    methods: {
        toggle() {
            return ClubApi.ajaxify(this.url, (data) => {
                this.upvotes = parseInt(data.post.upvotes);
                this.isVoted = true;
            });
        },
    },
};
</script>

<style scoped></style>
