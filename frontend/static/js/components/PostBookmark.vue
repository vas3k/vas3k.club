<template>
    <a  href="bookmarkUrl"
        class="bookmark"
        @click.prevent="toggle">
        <span v-if="isBookmark"><i class="fas fa-bookmark"></i>&nbsp;Убрать из закладок&nbsp;&nbsp;&nbsp;</span>
        <span v-else><i class="far fa-bookmark"></i>&nbsp;В закладки&nbsp;&nbsp;&nbsp;</span>
    </a>
</template>

<script>
import ClubApi from "../common/api.service";

export default {
    name: "PostBookmark",
    props: {
        initialIsBookmark: {
            type: Boolean,
            default() {
                return false;
            },
        },
        BookmarkUrl: {
            type: String,
            required: true,
        },
    },
    data() {
        return {
            isBookmark: this.initialIsBookmark,
        };
    },
    methods: {
        toggle() {
            return ClubApi.ajaxify(this.BookmarkUrl, (data) => {
                this.isBookmark = !this.isBookmark;
            });
        },
    },
};
</script>

<style scoped></style>
