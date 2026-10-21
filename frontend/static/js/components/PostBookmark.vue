<template>
    <a :href="bookmarkUrl" @click.prevent="toggle">
        <span v-if="isLoading">🤔</span>
        <span v-if="isBookmarked"><i class="fas fa-bookmark"></i>&nbsp;Убрать из закладок</span>
        <span v-else><i class="far fa-bookmark"></i>&nbsp;В закладки</span>
    </a>
</template>

<script>
import ClubApi from "../common/api.service";

export default {
    name: "PostBookmark",
    props: {
        initialIsBookmarked: {
            type: Boolean,
            default() {
                return false;
            },
        },
        bookmarkUrl: {
            type: String,
            required: true,
        },
    },
    data() {
        return {
            isBookmarked: this.initialIsBookmarked,
            isLoading: false,
        };
    },
    methods: {
        toggle() {
            this.isLoading = true;
            const method = this.isBookmarked ? "delete" : "post";
            return ClubApi[method](this.bookmarkUrl, (data) => {
                this.isLoading = false;
                if (!data.error) this.isBookmarked = data.is_bookmarked;
            });
        },
    },
};
</script>
