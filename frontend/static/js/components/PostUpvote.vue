<template>
    <a
        href="upvoteUrl"
        class="upvote"
        :class="{
            'upvote-voted': isVoted && !isDisabled,
            'upvote-disabled': isDisabled,
            'upvote-type-inline': isInline,
            'upvote-type-checkbox': variant === 'checkbox',
        }"
        @click.prevent="toggle"
    >
        <template v-if="variant === 'checkbox'">
            <span class="upvote-checkbox-icon">
                <i v-if="isVoted || isDisabled" class="fas fa-check-square"></i>
                <i v-else class="far fa-square"></i>
            </span>
            <span v-if="caption && !isDisabled" class="upvote-checkbox-caption">{{ caption }}</span>
        </template>
        <template v-else>
            {{ upvotes }}
        </template>
    </a>
</template>

<script>
import ClubApi from "../common/api.service";

export default {
    name: "PostUpvote",
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
        variant: {
            type: String,
            default: "upvote",
            validator: (value) => ["upvote", "checkbox"].includes(value),
        },
        caption: {
            type: String,
            default: "",
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
                    this.upvotes = parseInt(data.post.upvotes);
                    this.isVoted = true;
                    this.upvotedTimestamp = data.upvoted_timestamp;
                });
            }

            if (this.isVoted && this.getHoursSinceVote() <= this.hoursToRetractVote) {
                return ClubApi.post(this.retractVoteUrl, (data) => {
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
            return (Date.now() - this.upvotedTimestamp) / millisecondsInHour;
        },
    },
};
</script>
