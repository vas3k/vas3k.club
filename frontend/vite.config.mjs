import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig({
    plugins: [react()],
    base: "/static/dist/",
    server: { host: "0.0.0.0", port: Number(process.env.VITE_DEV_SERVER_PORT || 5173), strictPort: true },
    test: {
        globals: true,
        environment: "jsdom",
        environmentOptions: { jsdom: { url: "https://vas3k.club" } },
        setupFiles: ["./test/setup.js"],
        include: ["src/__tests__/**/*.test.js"],
    },
    build: {
        outDir: "static/dist",
        emptyOutDir: true,
        manifest: true,
        rolldownOptions: { input: ["src/main.js", "static/css/index.css"] },
    },
});
