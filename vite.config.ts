import { fileURLToPath, URL } from "node:url";

import react from "@vitejs/plugin-react";
import { defineConfig, loadEnv, type ProxyOptions } from "vite";

export default defineConfig(({ mode }) => {
    const env = loadEnv(mode, process.cwd(), "ANAMNESIS_");
    const api: ProxyOptions = {
        target: env.ANAMNESIS_API_TARGET || "http://127.0.0.1:8000",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api(?=\/|$)/, ""),
    };
    const proxy = { "/api/": api };

    return {
        plugins: [react()],
        resolve: { alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) } },
        server: { host: "127.0.0.1", port: 5173, proxy },
        preview: { host: "127.0.0.1", port: 4173, proxy },
    };
});
