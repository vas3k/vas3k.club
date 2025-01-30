<template>
    <div :data-value="theme" :data-real="realTheme()">
        <label class="light"><input type="radio" v-model="theme" value="light" /></label>
        <label class="auto"><input type="radio" v-model="theme" value="auto" /></label>
        <label class="dark"><input type="radio" v-model="theme" value="dark" /></label>
    </div>
</template>

<script>
export default {
    name: "ThemeSwitcher",
    data() {
        return {
            theme: "auto",
        };
    },
    watch: {
        theme() {
            this.changeTheme();
        },
    },
    computed: {
        $media() {
            return matchMedia("(prefers-color-scheme: light)");
        },
    },
    mounted() {
        this.$media.addEventListener("change", this.changeTheme);
        const localTheme = localStorage.getItem("theme");
        if (["light", "auto", "dark"].includes(localTheme)) {
            this.theme = localTheme;
        }
    },
    methods: {
        changeTheme() {
            document.documentElement.setAttribute("theme", this.realTheme());
            this.$el.dataset.value = this.theme;
            localStorage.setItem("theme", this.theme);
            this.$forceUpdate();
        },
        realTheme() {
            return this.theme === "auto" ? (this.$media.matches ? "light" : "dark") : this.theme;
        },
    },
};
</script>

<style scoped>
div {
    display: inline-block;
    position: relative;
    height: 30px;
    line-height: 30px;
    border-radius: 17px;
    padding: 3px;

    &:before {
        content: "";
        position: absolute;
        left: 36px;
        width: 30px;
        height: 30px;
        border-radius: 15px;
        transition: ease 0.3s all;
    }
    &[data-value="light"]:before {
        transform: translateX(-33px);
    }
    &[data-value="auto"]:before {
        transform: translateX(0px);
    }
    &[data-value="dark"]:before {
        transform: translateX(33px);
    }
    &[data-real="dark"] {
        background: #ffffff22;
        &:before {
            background: #00000099;
        }
    }
    &[data-real="light"] {
        background: #30303080;
        &:before {
            background: #ffffff66;
        }
    }
    label {
        width: 30px;
        position: relative;
        display: inline-block;
        text-align: center;
        cursor: pointer;
        &:after {
            font-size: 17px;
        }
    }
    label.light:after {
        content: "☀️";
    }
    label.dark:after {
        content: "🌙";
    }
    label.auto:after {
        content: "🌗";
    }
    input {
        display: none;
    }
}
</style>
