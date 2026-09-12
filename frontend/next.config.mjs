/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Next otherwise writes its own AGENTS.md/CLAUDE.md into this directory on
  // every build; this repo manages its own agent instructions.
  agentRules: false,
};

export default nextConfig;
