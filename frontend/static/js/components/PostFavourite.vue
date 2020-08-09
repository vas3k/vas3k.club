<template>
    <a  v-show="IsEnabled"
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
            IsEnabled: this.InitialIsEnabled,
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
