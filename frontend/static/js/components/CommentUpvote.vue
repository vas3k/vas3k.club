<template>
    <a
        :href="voteUrl"
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
        voteUrl: {
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
            if (this.isDisabled || (this.isVoted && this.getHoursSinceVote() > this.hoursToRetractVote)) {
                return;
            }

            const method = this.isVoted ? "delete" : "post";
            return ClubApi[method](this.voteUrl, (data) => {
                if (data.error) {
                    return;
                }

                this.upvotes = parseInt(data.comment.upvotes);
                this.isVoted = data.is_voted;
                this.upvotedTimestamp = data.upvoted_timestamp || undefined;
            });
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
