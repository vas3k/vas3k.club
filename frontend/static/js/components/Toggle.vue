<template>
    <div :class="{ 'is-active': isActive }" @click.prevent="toggle">
        <span v-if="isLoading">🤔 думаю...</span>
        <label v-else style="cursor: pointer;">
            <input type="checkbox" v-model="isActive" @change.prevent="toggle" />
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
