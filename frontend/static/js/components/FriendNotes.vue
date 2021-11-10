<template>
    <a v-if="isNotes" class="profile-status clickable" @click="toggle">
        <span class="profile-status-icon">📋</span>
        <span class="profile-status-status">Добавить заметки</span>
    </a>
    <a v-else class="profile-status clickable" @click="toggle">
        <span class="profile-status-icon">📋</span>
        <span class="profile-status-status">Мои заметки</span>
    </a>
</template>

<script>
import ClubApi from "../common/api.service";

export default {
    name: "FriendNotes",
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
            isNotes: this.isNotesByDefault,
            isLoading: false,
        };
    },
    methods: {
        toggle() {
            this.isLoading = true;
            return ClubApi.ajaxify(this.url, (data) => {
                this.isLoading = false;

                if (data.status === "created") {
                    this.isNotes = true;
                }

                if (data.status === "deleted") {
                    this.isNotes = false;
                }
            });
        },
    },
};
</script>
