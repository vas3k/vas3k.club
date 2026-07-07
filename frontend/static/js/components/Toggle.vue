<template>
    <div :class="{ 'is-active': isActive }">
        <span v-if="isLoading">🤔 думаю...</span>
        <label v-else style="cursor: pointer;">
            <input type="checkbox" :checked="isActive" @change.prevent="toggle" />
            <slot></slot>
        </label>
    </div>
</template>

<script>
import ClubApi from "../common/api.service";

export default {
    name: "Toggle",
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
        isInverted: {
            type: Boolean,
            default() {
                return false;
            },
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
            return ClubApi.post(this.url, (data) => {
                this.isLoading = false;

                if (data.status === "created") {
                    this.isActive = !this.isInverted;
                }

                if (data.status === "deleted") {
                    this.isActive = this.isInverted;
                }
            });
        },
    },
};
</script>
