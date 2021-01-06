<template>
    <span class="feed-sidebar-toggler" @click.prevent="toggle">{{ isShown ? "&#8249;" : "&#8250;" }}</span>
</template>

<script>
export default {
    name: "SidebarToggler",
    data() {
        return {
            isShown: false,
        };
    },
    methods: {
        toggle() {
            this.isShown = !this.isShown;
            document.getElementById("app").classList.toggle("mobile-menu-opened", this.isShown);
            document.querySelector(".feed-main").classList.toggle("feed-main-closed", this.isShown);
        },
    },
};
</script>
