<template>
    <mobile-editor
        v-if="isMobile()"
        v-bind:value="value"
        v-on:input="$emit('input', $event)"
        v-on:blur="$emit('blur', $event)"
        :focused="focused"
    ></mobile-editor>
    <desktop-editor
        v-else
        v-bind:value="value"
        v-on:input="$emit('input', $event)"
        v-on:blur="$emit('blur', $event)"
        :focused="focused"
    ></desktop-editor>
</template>

<script>
import Vue from "vue";
import { isMobile } from "../../common/utils";

Vue.component("mobile-editor", () => import("./MobileMarkdownEditor.vue"));
Vue.component("desktop-editor", () => import("./DesktopMarkdownEditor.vue"));

/**
 * The component is a facade for external use.
 * It chooses which version of the editor to show
 */
export default {
    props: {
        value: {
            type: String
        },
        focused: {
            type: Boolean
        }
    },
    methods: {
        isMobile,
    },
};
</script>
