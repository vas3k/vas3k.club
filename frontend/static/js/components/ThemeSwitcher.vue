<template>
    <label style="width: 6.25em">
        <span class="sr-only">Выберите тему</span>
        <select :value="theme" width="6.25em" @input="setTheme" ref="themeSelect">
            <option value="dark">Темная тема</option>
            <option value="light">Светлая тема</option>
            <option value="auto">Системная тема</option>
        </select>
    </label>
</template>

<script>
const storageKey = "theme";

const parseTheme = (theme) => (theme === "auto" || theme === "dark" || theme === "light" ? theme : "auto");

const loadTheme = () => parseTheme(typeof localStorage !== "undefined" && localStorage.getItem(storageKey));

function storeTheme(theme) {
    if (typeof localStorage !== "undefined") {
        localStorage.setItem(storageKey, theme === "light" || theme === "dark" ? theme : "");
    }
}

const getPreferredColorScheme = () => (matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark");

function onThemeChange(theme) {
    document.documentElement.setAttribute("theme", theme === "auto" ? getPreferredColorScheme() : theme);
    storeTheme(theme);
}

export default {
    name: "ThemeSwitcher",
    props: {},
    mounted() {
        matchMedia(`(prefers-color-scheme: light)`).addEventListener("change", () => {
            if (loadTheme() === "auto") onThemeChange("auto");
        });
    },
    data() {
        const theme = loadTheme();
        onThemeChange(theme);
        return { theme };
    },
    methods: {
        setTheme(event) {
            if (!event.currentTarget) {
                return;
            }

            const theme = parseTheme(event.currentTarget.value);

            onThemeChange(theme);
            this.theme = theme;
        },
    },
};
</script>
