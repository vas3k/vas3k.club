<template>
    <mobile-editor
        v-if="isMobile()"
        :value="value"
        :focused="focused"
        @blur="$emit('blur', $event)"
    ></mobile-editor>
    <desktop-editor
        v-else
        :value="value"
        :focused="focused"
        @blur="$emit('blur', $event)"
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
 *
 * The value passed via prop used as the value setter for the editor.
 * When the user moves the focus from the editor, `blur` event with an updated value is sent
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
