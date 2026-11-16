import type { NextConfig } from "next";

const TOMU_API = process.env.TOMU_API ?? "http://localhost:8000";

const nextConfig: NextConfig = {
  /* config options here */
  cacheComponents: true,
  partialPrefetching: true,
  // Pass /api/... on to the Python API, so the browser only ever talks to the page.
  rewrites: async () => [{ source: "/api/:path*", destination: `${TOMU_API}/api/:path*` }],
};

export default nextConfig;
