import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  build: {
    outDir: "../src/whub/webapp/dist",
    emptyOutDir: true,
  },
  test: {
    environment: "jsdom",
  },
  server: {
    host: "127.0.0.1",
    port: 8712,
    strictPort: true,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8713",
        changeOrigin: false,
        ws: true,
      },
    },
  },
});
