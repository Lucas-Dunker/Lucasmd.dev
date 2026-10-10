import { defineConfig, passthroughImageService } from "astro/config";
import tailwindcss from "@tailwindcss/vite";
import sitemap from "@astrojs/sitemap";
import icon from "astro-icon";

// https://astro.build/config
export default defineConfig({
  output: "static",
  redirects: { "/writing": "/#writing" },
  site: "https://lucasdunker.com",
  integrations: [sitemap(), icon()],
  image: {
    service: passthroughImageService(),
  },
  prefetch: {
    defaultStrategy: "load",
    prefetchAll: true,
  },
  vite: {
    plugins: [tailwindcss()],
    server: {
      watch: {
        usePolling: true,
        interval: 1000,
      },
    },
  },
});
