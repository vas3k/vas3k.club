<template>
    <button
        class="upvote button"
        :class="{
            'upvote-voted': isVoted && !isDisabled,
            'upvote-disabled': isDisabled,
            'upvote-type-inline': isInline,
        }"
        @click.prevent="toggle"
    >
        {{ upvotes }}
    </button>
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
        initialIsVoted: {
            type: Boolean,
            default() {
                return false;
            },
        },
        initialUpvoteTimestamp: {
            type: String
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
        upvoteUrl: {
            type: String,
            required: true,
        },
        retractVoteUrl: {
            type: String,
            required: true,
        }
    },
    data() {
        return {
            upvotes: this.post.upvotes,
            isVoted: this.initialIsVoted,
            upvotedTimestamp: this.initialUpvoteTimestamp && parseInt(this.initialUpvoteTimestamp)
        };
    },
    methods: {
        toggle() {
            if (!this.isVoted) {
                return ClubApi.ajaxify(this.upvoteUrl, (data) => {
                    this.upvotes = parseInt(data.post.upvotes);
                    this.isVoted = true;
                    this.upvotedTimestamp = data.upvoted_timestamp
                });
            }

            if (this.isVoted && this.getHoursSinceVote() <= 3) {
                return ClubApi.ajaxify(this.retractVoteUrl, (data) => {
                    this.upvotes = parseInt(data.post.upvotes);
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
            return (Date.now() - this.upvotedTimestamp)  / millisecondsInHour;
        }

    },
};
</script>

<style scoped></style>
