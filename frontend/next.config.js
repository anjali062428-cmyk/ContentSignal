/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8001/api",
  },
  async rewrites() {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL
      ? process.env.NEXT_PUBLIC_API_URL.replace(/\/+$/, "")
      : "http://127.0.0.1:8001/api";
    return [
      {
        source: "/api/:path*",
        destination: `${apiUrl}/:path*`,
      },
    ];
  },
  async redirects() {
    return [
      {
        source: "/dashboard/model-insights",
        destination: "/dashboard/models",
        permanent: false,
      },
      {
        source: "/dashboard/ai-assistant",
        destination: "/dashboard/ai",
        permanent: false,
      },
    ];
  },
};

module.exports = nextConfig;