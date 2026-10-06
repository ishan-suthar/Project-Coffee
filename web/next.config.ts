import type { NextConfig } from "next";

// Extra hosts allowed to load the dev server (for access from other devices
// on your network). start.ps1 sets COFFEE_LAN_IP from -LanIp; set it
// yourself (comma-separated) when running `npm run dev` directly.
const lanHosts = (process.env.COFFEE_LAN_IP ?? "")
  .split(",")
  .map((host) => host.trim())
  .filter(Boolean);

const nextConfig: NextConfig = {
  allowedDevOrigins: lanHosts,
};

export default nextConfig;
