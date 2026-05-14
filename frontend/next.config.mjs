import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const backendProxy = process.env.API_PROXY_TARGET || process.env.BACKEND_URL || "";

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  transpilePackages: ["@heroui/react"],
  async rewrites() {
    if (!backendProxy) return [];
    const base = String(backendProxy).replace(/\/$/, "");
    return [
      { source: "/api/v1/:path*", destination: `${base}/api/v1/:path*` },
      { source: "/socket.io/:path*", destination: `${base}/socket.io/:path*` },
    ];
  },
};

export default nextConfig;
