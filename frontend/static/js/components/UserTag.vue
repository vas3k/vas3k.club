<template>
    <a
        :href="url"
        :class="{ 'user-tag-active': isActive }"
        :style="{ 'background-color': isActive ? tagColor : null }"
        @click.prevent="toggle"
    >
        {{ tagName }}
    </a>
</template>

<script>
import ClubApi from "../common/api.service";

export default {
    name: "UserTag",
    props: {
        tagName: {
            type: String,
            required: true,
        },
        tagColor: {
            type: String,
            required: true,
        },
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
        };
    },
    methods: {
        toggle() {
            return ClubApi.ajaxify(this.url, (data) => {
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
