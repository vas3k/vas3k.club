<template>
    <a v-if="isLoading" class="button button-inverted friend-button">
        <span class="friend-button-status">...</span>
    </a>
    <a v-else-if="isFriend" class="button button-inverted friend-button" @click="toggle">
        <span class="friend-button-icon">✅</span>
        <span class="friend-button-status">Мой чувак</span>
    </a>
    <a v-else class="button button-inverted friend-button" @click="toggle">
        <span class="friend-button-icon-big">+</span>
        <span class="friend-button-status">Подписаться</span>
    </a>
</template>

<script>
import ClubApi from "../common/api.service";

export default {
    name: "FriendButton",
    props: {
        isFriendByDefault: {
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
            isFriend: this.isFriendByDefault,
            isLoading: false,
        };
    },
    methods: {
        toggle() {
            this.isLoading = true;
            return ClubApi.post(this.url, (data) => {
                this.isLoading = false;
                if (data.status === "created") this.isFriend = true;
                if (data.status === "deleted") this.isFriend = false;
            });
        },
    },
};
</script>
