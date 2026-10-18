import { defineConfig } from "vite";
import { fileURLToPath } from "node:url";
import react from "@vitejs/plugin-react";
import tailwind from "@tailwindcss/vite";
export default defineConfig({
  publicDir: fileURLToPath(new URL("../shared/public", import.meta.url)),
  plugins: [react(), tailwind()],
  server: {
    fs: {
      strict: true,
      allow: [".", "../shared", "../node_modules"].map((path) =>
        fileURLToPath(new URL(path, import.meta.url)),
      ),
    },
    proxy: {
      "/api": {
        target: process.env.API_PROXY_TARGET || "http://127.0.0.1:8000",
        changeOrigin: false,
      },
    },
  },
});
