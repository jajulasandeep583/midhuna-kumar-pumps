import frameworkUI from "@framework/ui/vite";
import vue from "@vitejs/plugin-vue";
import vueJsx from "@vitejs/plugin-vue-jsx";
import path from "path";
import { defineConfig } from "vite";
import { VitePWA } from "vite-plugin-pwa";
import {
  getLocalFrappeUIDevConfig,
  importFrappeUIPlugin,
} from "./vite-helpers";

export default defineConfig(async ({ mode }) => {
  const { useLocalFrappeUI, localFrappeUIAliases } = getLocalFrappeUIDevConfig({
    mode,
    rootDir: __dirname,
  });

  const frappeui = await importFrappeUIPlugin({ useLocalFrappeUI });
  const config = {
    plugins: [
      frappeui({
        frappeProxy: true,
        lucideIcons: true,
        jinjaBootData: true,
        buildConfig: {
          outDir: `../kumar_service/public/desk`,
          emptyOutDir: true,
          indexHtmlPath: "../kumar_service/www/helpdesk/index.html",
        },
        frappeTypes: {
          input: {
            helpdesk: [
              "hd_ticket_status",
              "hd_ticket",
              "hd_service_holiday_list",
              "hd_service_level_agreement",
              "hd_agent",
              "hd_team",
              "hd_customer",
            ],
            frappe: ["assignment_rule", "contact"],
          },
        },
      }),
      frameworkUI(),

      vue(),
      vueJsx(),
      VitePWA({
        // The service worker is deliberately off.
        //
        // It precached index.html and served it for any navigation, so after the
        // desk moved from /helpdesk to /kumar-desk a browser that had visited the
        // old path kept serving the old shell - the app landed on
        // /kumar-desk/kumar-desk from a cache the server could not see or clear.
        // Offline caching buys an internal tool on the office LAN nothing, and it
        // cost a bug that looks exactly like a routing fault and is not one.
        //
        // The manifest is kept so the desk can still be installed to a home
        // screen; injectRegister:null means nothing registers a worker.
        selfDestroying: true,
        injectRegister: null,
        registerType: "autoUpdate",
        devOptions: {
          enabled: false,
        },
        workbox: {
          cleanupOutdatedCaches: true,
          maximumFileSizeToCacheInBytes: 5 * 1024 * 1024,
        },
        manifest: {
          display: "standalone",
          name: "KUMAR Pumps Desk",
          short_name: "KUMAR Desk",
          start_url: "/kumar-desk",
          description:
            "Dealer service, warranty and traceability for KUMAR pumpsets - Sri Lakshmi Ganapathi Engineering Works, Tenali",
          icons: [
            {
              src: "/assets/kumar_service/desk/manifest/manifest-icon-192.maskable.png",
              sizes: "192x192",
              type: "image/png",
              purpose: "any",
            },
            {
              src: "/assets/kumar_service/desk/manifest/manifest-icon-192.maskable.png",
              sizes: "192x192",
              type: "image/png",
              purpose: "maskable",
            },
            {
              src: "/assets/kumar_service/desk/manifest/manifest-icon-512.maskable.png",
              sizes: "512x512",
              type: "image/png",
              purpose: "any",
            },
            {
              src: "/assets/kumar_service/desk/manifest/manifest-icon-512.maskable.png",
              sizes: "512x512",
              type: "image/png",
              purpose: "maskable",
            },
          ],
        },
      }),
    ],
    server: {
      allowedHosts: true,
      fs: {
        // ".." = apps/helpdesk; "../.." = apps/, so the linked @framework/ui
        // (apps/frappe/ui) can be served from source in dev.
        allow: ["..", "../.."],
      },
    },
    resolve: {
      alias: {
        "@": path.resolve(__dirname, "src"),
        "tailwind.config.js": path.resolve(__dirname, "tailwind.config.js"),
        // ...localFrappeUIAliases,
      },
      // frappe-ui is served from source (excluded from optimizeDeps) and the
      // submodule ships its own node_modules with older tiptap/ProseMirror.
      // Force a single copy of each so the editor doesn't load two
      // prosemirror-state instances (RangeError: different instances of a keyed plugin).
      dedupe: [
        // @framework/ui imports from vue/frappe-ui; force a single instance of
        // each so its Combobox shares helpdesk's frappe-ui, not a second copy.
        "vue",
        "frappe-ui",
        "reka-ui",
        "@tiptap/core",
        "@tiptap/pm",
        "prosemirror-state",
        "prosemirror-model",
        "prosemirror-transform",
        "prosemirror-view",
        "prosemirror-keymap",
        "prosemirror-commands",
        "prosemirror-history",
        "prosemirror-gapcursor",
        "prosemirror-tables",
      ],
    },
    optimizeDeps: {
      include: [
        "feather-icons",
        "tailwind.config.js",
        "prosemirror-state",
        "prosemirror-view",
        "prosemirror-gapcursor",
        "prosemirror-tables",
        "lowlight",
        "interactjs",
      ],
      exclude: ["frappe-ui", "@framework/ui"],
    },
  };
  return config;
});
