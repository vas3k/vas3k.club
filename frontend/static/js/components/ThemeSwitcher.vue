<template>
    <label style="width: 6.25em">
        <span class="sr-only">Выберите тему</span>
        <select value="auto" width="6.25em" @input="setTheme">
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

matchMedia(`(prefers-color-scheme: light)`).addEventListener("change", () => {
    if (loadTheme() === "auto") onThemeChange("auto");
});

// class ThemeProvider {
//     storedTheme = loadTheme();

//     constructor() {
//         const theme =
//             this.storedTheme || (window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark");
//         document.documentElement.dataset.theme = theme === "light" ? "light" : "dark";
//     }

//     updatePickers(theme = this.storedTheme || "auto") {
//         document.querySelectorAll("starlight-theme-select").forEach((picker) => {
//             console.log("picker", picker);
//             const select = picker.querySelector("select");
//             if (select) select.value = theme;

//             /** @type {HTMLTemplateElement | null} */
//             const tmpl = document.querySelector(`#theme-icons`);
//             const newIcon = tmpl && tmpl.content.querySelector("." + theme);
//             if (newIcon) {
//                 const oldIcon = picker.querySelector("starlight-theme-select i.label-icon");
//                 if (oldIcon) {
//                     oldIcon.replaceChildren(...newIcon.cloneNode(true).childNodes);
//                 }
//             }
//         });
//     }
// }

// const themeProvider = new ThemeProvider();

export default {
    name: "PostUpvote",
    props: {},
    data() {
        const theme = loadTheme();
        onThemeChange(theme);
        // themeProvider.updatePickers(theme);
    },
    methods: {
        setTheme(option) {
            if (!option) {
                return;
            }

            const theme = parseTheme(option.value);

            onThemeChange(theme);
            // themeProvider.updatePickers(theme);
            document.documentElement.setAttribute("theme", theme === "auto" ? getPreferredColorScheme() : theme);
            storeTheme(theme);
        },
    },
};
</script>
