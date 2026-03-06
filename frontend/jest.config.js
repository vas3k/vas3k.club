module.exports = {
    testEnvironment: "jsdom",
    testEnvironmentOptions: {
        url: "https://vas3k.club",
        customExportConditions: ["node"],
    },
    roots: ["<rootDir>/static/js"],
    testMatch: ["**/__tests__/**/*.test.js"],
    transform: {
        "^.+\\.js$": "babel-jest",
        "^.+\\.vue$": "@vue/vue3-jest",
    },
    moduleFileExtensions: ["js", "json", "vue"],
    collectCoverageFrom: [
        "static/js/**/*.js",
        "static/js/components/**/*.vue",
        "!static/js/__tests__/**",
        "!static/js/inline-attachment.js",
        "!static/js/codemirror-4.inline-attachment.js",
        "!static/js/main.js",
    ],
    coverageDirectory: "<rootDir>/coverage",
};
