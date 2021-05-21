<template>
    <span>
        <button class="button friend-button" @click="toggle">
            <span v-if="isFriend" class="friend-button-text">✅ Мой чувак</span>
            <span v-else class="friend-button-text">🤝 Добавить в мои чуваки</span>
        </button>
    </span>
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
