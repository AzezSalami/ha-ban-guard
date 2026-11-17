import { defineConfig } from "vitest/config";

// Builds one self-contained ES module that Home Assistant serves as the panel.
// The output is committed and CI rebuilds it and fails on any byte difference.
export default defineConfig({
  build: {
    lib: {
      entry: "src/ban-guard-panel.ts",
      formats: ["es"],
      fileName: () => "ban-guard-panel.js",
    },
    outDir: "../custom_components/ban_guard/frontend",
    emptyOutDir: false,
    target: "es2022",
    minify: true,
    sourcemap: false,
    reportCompressedSize: false,
  },
  test: {
    environment: "node",
    include: ["test/**/*.test.ts"],
  },
});
