<template>
    <a
        :href="upvoteUrl"
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
        hoursToRetractVote: {
            type: Number,
            default: 0,
        },
        initialUpvotes: {
            type: Number,
            default: 0,
            required: true,
        },
        initialIsVoted: {
            type: Boolean,
            default() {
                return false;
            },
        },
        initialUpvoteTimestamp: {
            type: String,
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
        retractVoteUrl: {
            type: String,
            required: true,
        },
        upvoteUrl: {
            type: String,
            required: true,
        },
    },
    data() {
        return {
            upvotes: this.initialUpvotes,
            isVoted: this.initialIsVoted,
            upvotedTimestamp: this.initialUpvoteTimestamp && parseInt(this.initialUpvoteTimestamp),
        };
    },
    methods: {
        toggle() {
            if (!this.isVoted) {
                return ClubApi.post(this.upvoteUrl, (data) => {
                    this.upvotes = parseInt(data.comment.upvotes);
                    this.isVoted = true;
                    this.upvotedTimestamp = data.upvoted_timestamp;
                });
            }

            if (this.isVoted && this.getHoursSinceVote() <= this.hoursToRetractVote) {
                return ClubApi.post(this.retractVoteUrl, (data) => {
                    this.upvotes = parseInt(data.comment.upvotes);
                    if (data.success) {
                        this.isVoted = false;
                        this.upvotedTimestamp = undefined;
                    }
                });
            }
        },

        getHoursSinceVote() {
            if (!this.upvotedTimestamp) {
                return false;
            }

            const millisecondsInHour = 60 * 60 * 1000;
            return (Date.now() - this.upvotedTimestamp) / millisecondsInHour;
        },
    },
};
</script>
