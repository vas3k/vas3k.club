<template>
    <mobile-editor v-if="isMobile">
        <slot></slot>
    </mobile-editor>
    <desktop-editor v-else>
        <slot></slot>
    </desktop-editor>
</template>

<script>
import Vue from "vue";
import { isMobile } from "../../common/utils";

Vue.component("mobile-editor", () => import("./MobileMarkdownEditor.vue"));
Vue.component("desktop-editor", () => import("./DesktopMarkdownEditor.vue"));

export default {
    methods: {
        isMobile,
    },
};
</script>
