import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Self-contained server output: lets the Docker image run without node_modules.
  output: "standalone",
  // NOTE: `cacheComponents` and `partialPrefetching` are deliberately NOT enabled. They keep
  // visited pages alive in the background and re-run their effects when you come back, which
  // crashes Leaflet maps ("Map container is being reused by another instance") when you navigate
  // back to a page that has one. This app is client-rendered and live, so it gains nothing from them.
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
