<template>
    <a  v-show="Enabled"
        href="favouriteUrl"
        class="favourite"
        @click.prevent="toggle">

        <span v-if="isFavourite"><i class="fas fa-bookmark"></i>&nbsp;Убрать из закладок&nbsp;&nbsp;&nbsp;</span>
        <span v-else><i class="far fa-bookmark"></i>&nbsp;В закладки&nbsp;&nbsp;&nbsp;</span>
    </a>
</template>

<script>
import ClubApi from "../common/api.service";

export default {
    name: "PostFavourite",
    props: {
        post: {
            type: Object,
            required: true,
        },
        initialIsFavourite: {
            type: Boolean,
            default() {
                return false;
            },
        },
        InitialIsEnabled: {
            type: Boolean,
            default() {
                return false;
            },
        },
        FavouriteUrl: {
            type: String,
            required: true,
        },
    },
    data() {
        return {
            Enabled: this.InitialIsEnabled,
            isFavourite: this.initialIsFavourite,
        };
    },
    methods: {
        toggle() {
            return ClubApi.ajaxify(this.FavouriteUrl, (data) => {
                this.isFavourite = !this.isFavourite;
            });
        },
    },
};
</script>

<style scoped></style>
