<template>
    <span>
        <span v-if="isLoading">🤔</span>
        <input v-else type="checkbox" id="post-subscribed" v-model="isActive" @change.prevent="toggle" />
        <label for="post-subscribed">подписка</label>
    </span>
</template>

<script>
import ClubApi from "../common/api.service";

export default {
    name: "PostSubscription",
    props: {
        isActiveByDefault: {
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
            isActive: this.isActiveByDefault,
            isLoading: false,
        };
    },
    methods: {
        toggle() {
            this.isLoading = true;
            return ClubApi.ajaxify(this.url, (data) => {
                this.isLoading = false;

                if (data.status === "created") {
                    this.isActive = true;
                }

                if (data.status === "deleted") {
                    this.isActive = false;
                }
            });
        },
    },
};
</script>
