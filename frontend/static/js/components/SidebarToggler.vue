<template>
    <button
        class="button feed-sidebar-toggler"
        @click.prevent="toggle"
    >{{ isShown ? "←" : "→"}} </button>
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
            console.log('toggle!', this.isShown);
            document.getElementById('app').classList.toggle('mobile-menu-opened', this.isShown)
        },
    }
};
</script>
