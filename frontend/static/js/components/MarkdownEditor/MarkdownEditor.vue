<template>
    <mobile-editor
        v-bind:value="value"
        v-on:input="$emit('input', $event)"
        v-on:blur="$emit('blur', $event)"
        :focused="focused"
        v-if="isMobile()"></mobile-editor>
    <desktop-editor :value="value" v-else>
        <slot></slot>
    </desktop-editor>
</template>

<script>
import Vue from "vue";
import { isMobile } from "../../common/utils";

Vue.component("mobile-editor", () => import("./MobileMarkdownEditor.vue"));
Vue.component("desktop-editor", () => import("./DesktopMarkdownEditor.vue"));

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
