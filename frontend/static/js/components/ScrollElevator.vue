<template>
    <div class="elevator" 
        @click="toggle"
        :title="isDown ? 'вниз' : 'вверх'"
        :class="{
            'down': isDown,
            'hidden': !isVisible,
           }">
        <svg class="icon-scroll-up" width="32" height="32" viewBox="0 0 32 32" aria-hidden="true" version="1.1" role="img">
            <path d="M16 0C7.164 0 0 7.164 0 16s7.164 16 16 16 16-7.164 16-16S24.836 0 16 0zm8.412 19.523c-.517.512-1.355.512-1.872 0L16 13.516l-6.54 6.01c-.518.51-1.356.51-1.873 0-.516-.513-.517-1.343 0-1.855l7.476-7.326c.517-.512 1.356-.512 1.873 0l7.476 7.327c.516.513.516 1.342 0 1.854z"></path>
        </svg>
    </div>
</template>

<script>

const minVisibilityScroll = 200;

export default {
    name: "ScrollElevator",
    data() {
        return {
            savedPosition: 0,
            isDown: false,
            isVisible: false,
        }
    },
    created: function () {
        window.addEventListener('scroll', this.onWindowScroll);
        this.isVisible = window.scrollY > minVisibilityScroll;
    },
    destroyed () {
        window.removeEventListener('scroll', this.onWindowScroll);
    },
    methods: {
        toggle() {
            let scrollTo = this.savedPosition;
            if (!this.isDown) {
                this.savedPosition = window.scrollY;
                scrollTo = 0;
            }
            window.scrollTo({
                top: scrollTo,
            });
            this.isDown = !this.isDown;
        },
        onWindowScroll(event) {
            // handle case when window scrolled up by elevator and then scrolled down by user
            if (window.scrollY > 0) {
                this.savedPosition = 0;
                this.isDown = false;
            }
            this.isVisible = window.scrollY > minVisibilityScroll || this.savedPosition != 0;
        }
    }
};
</script>

<style scoped>
    .elevator {
        position: fixed;
        left: 0;
        bottom: 0;
        top: 0;
        width: 40px;
        text-align: center;
    }

    .elevator:hover {
        background-color: rgba(0, 0, 0, 0.05);
        cursor: pointer;
    }

    html[theme="dark"] .elevator:hover {
        background-color: rgba(255, 255, 255, 0.05);
        cursor: pointer;
    }

    .elevator .icon-scroll-up {
		position: relative;
        display: inline-block;
        top: 50%;
        margin-top: -15px;
        width: 30px;
        height: 30px;
        background-color: transparent;
        color: inherit;
        vertical-align: middle;
        stroke-width: 0;
        pointer-events: none;
        fill: var(--opposite-bg-color);
        opacity: 0.3;
        width: 30px;
    }

    .elevator.down .icon-scroll-up {
        height: 32px;
        transform: rotate(180deg);
    }

    .elevator.hidden {
        display: none;
    }
    @media only screen and (max-width : 1024px) {
        .elevator {
            display: none;
        }
    }
</style>
