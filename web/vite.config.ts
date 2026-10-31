import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// base "./" keeps every asset path relative, so the same build works on GitHub Pages
// (served from /stargaze/) and from any other static host.
export default defineConfig({
  base: "./",
  plugins: [react(), tailwindcss()],
});
