<template>
    <a v-bind::href="url"
       class="user-tag"
       v-bind:class="{'user-tag-active': isActive}"
       v-bind:style="{'background-color': isActive ? tag.color : null}"
       v-on:click.prevent="toggle">
        {{ tag.name }}
    </a>
</template>

<script>
import ClubApi from "../common/api.service";

export default {
    name: "UserTag",
    props: {
        tag: {
            type: Object,
            required: true,
        },
        isActiveByDefault: {
            type: Boolean,
            default() {
                return false
            }
        },
        url: {
            type: String,
            required: true,
        }
    },
    data() {
        return {
            isActive: this.isActiveByDefault,
        }
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
    }
};
</script>
