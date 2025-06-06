// Plugins
import AutoImport from "unplugin-auto-import/vite";
import Components from "unplugin-vue-components/vite";
import Fonts from "unplugin-fonts/vite";
import Layouts from "vite-plugin-vue-layouts";
import Vue from "@vitejs/plugin-vue";
import VueRouter from "unplugin-vue-router/vite";
import vuetify, {transformAssetUrls} from "vite-plugin-vuetify";

// Utilities
import {defineConfig} from "vite";
import {fileURLToPath, URL} from "node:url";

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    VueRouter(),
    Layouts(),
    Vue({
      template: {transformAssetUrls},
    }),
    // https://github.com/vuetifyjs/vuetify-loader/tree/master/packages/vite-plugin#readme
    vuetify({
      autoImport: true,
      styles: {
        configFile: "src/styles/styles.scss",
      },
    }),
    Components(),
    Fonts({
      google: {
        families: [
          {
            name: "Roboto",
            styles: "wght@100;300;400;500;700;900",
          },
        ],
      },
    }),
    AutoImport({
      imports: ["vue", "vue-router"],
      vueTemplate: true,
    }),
  ],
  define: {"process.env": {}},
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
    extensions: [".js", ".json", ".jsx", ".mjs", ".ts", ".tsx", ".vue"],
  },
  server: {
    proxy: {
      "/api": {
        target: "http://localhost:3000",
        changeOrigin: true,
        secure: false,
      },
      "/ws": {
        target: "ws://localhost:3000",
        changeOrigin: true,
        secure: false,
        ws: true,
      },
    },
    port: 8080,
    host: "0.0.0.0",
  },
});
