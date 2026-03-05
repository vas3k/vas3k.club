<template>
    <div :data-value="theme" :data-real="realTheme">
        <label class="light" aria-label="Светлая тема"><input type="radio" v-model="theme" value="light" /></label>
        <label class="auto" aria-label="Автоматически определять тему"><input type="radio" v-model="theme" value="auto" /></label>
        <label class="dark" aria-label="Тёмная тема"><input type="radio" v-model="theme" value="dark" /></label>
    </div>
</template>

<script>
export default {
    name: "ThemeSwitcher",
    data() {
        return {
            theme: "auto",
            prefersLight: matchMedia("(prefers-color-scheme: light)").matches,
        };
    },
    computed: {
        realTheme() {
            // if you change this code, update the similar code in `html/layout.html`
            // run on initialization to avoid background flickering
            return this.theme === "auto" ? (this.prefersLight ? "light" : "dark") : this.theme;
        },
    },
    watch: {
        realTheme(val) {
            document.documentElement.setAttribute("theme", val);
            localStorage.setItem("theme", this.theme);
        },
    },
    mounted() {
        this._mediaQuery = matchMedia("(prefers-color-scheme: light)");
        this.prefersLight = this._mediaQuery.matches;
        this._mediaQuery.addEventListener("change", this.onMediaChange);

        const localTheme = localStorage.getItem("theme");
        if (["light", "auto", "dark"].includes(localTheme)) {
            this.theme = localTheme;
        }
    },
    beforeDestroy() {
        this._mediaQuery.removeEventListener("change", this.onMediaChange);
    },
    methods: {
        onMediaChange(e) {
            this.prefersLight = e.matches;
        },
    },
};
</script>

<style scoped>
div {
    --padding: 4px;
    display: flex;
    flex-wrap: nowrap;
    position: relative;
    height: 2rem;
    line-height: 2rem;
    border-radius: calc(var(--block-border-radius) + var(--padding));
    padding: var(--padding);

    &:before {
        content: "";
        position: absolute;
        left: 2.25rem;
        width: 2rem;
        height: 2rem;
        border-radius: var(--block-border-radius);
        transition: ease 0.3s all;
    }

    &[data-value="light"]:before {
        transform: translateX(-2rem);
    }
    &[data-value="auto"]:before {
        transform: translateX(0);
    }
    &[data-value="dark"]:before {
        transform: translateX(2rem);
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
        width: 2rem;
        position: relative;
        display: inline-block;
        text-align: center;
        cursor: pointer;
        &:after {
            font-size: 1rem;
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
