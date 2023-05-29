<template>
    <a v-if="isFriend" class="profile-status clickable" @click="toggle">
        <span class="profile-status-icon">✅</span>
        <span class="profile-status-status">Мой чувак</span>
    </a>
    <a v-else class="profile-status clickable" @click="toggle">
        <span class="profile-status-icon">🤝</span>
        <span class="profile-status-status">Добавить в мои чуваки</span>
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
            return ClubApi.ajaxify(this.url, (data) => {
                this.isLoading = false;

                if (data.status === "created") {
                    this.isFriend = true;
                }

                if (data.status === "deleted") {
                    this.isFriend = false;
                }
            });
        },
    },
};
</script>
