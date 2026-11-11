import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // ── Security Headers ────────────────────────────────────────────────────────
  // Applied to every route. Adjust CSP connect-src if the backend moves.
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: [
          // Prevent clickjacking
          { key: "X-Frame-Options", value: "DENY" },
          // Prevent MIME-type sniffing
          { key: "X-Content-Type-Options", value: "nosniff" },
          // Referrer policy — no cross-origin leakage
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          // Disable browser-level XSS filter (deprecated; CSP replaces it)
          { key: "X-XSS-Protection", value: "0" },
          // Only connect to our own backend and Supabase
          {
            key: "Content-Security-Policy",
            value: [
              "default-src 'self'",
              // Next.js requires 'unsafe-inline' for its inline styles and scripts
              "script-src 'self' 'unsafe-inline' 'unsafe-eval'",
              "style-src 'self' 'unsafe-inline'",
              "img-src 'self' data: blob:",
              // Allow fetches to the FastAPI backend and Supabase
              `connect-src 'self' ${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"} https://*.supabase.co wss://*.supabase.co`,
              "font-src 'self'",
              "object-src 'none'",
              "base-uri 'self'",
              "form-action 'self'",
              "frame-ancestors 'none'",
              "upgrade-insecure-requests",
            ].join("; "),
          },
          // Permissions policy — disable unused browser features
          {
            key: "Permissions-Policy",
            value: "camera=(), microphone=(), geolocation=(), interest-cohort=()",
          },
        ],
      },
    ];
  },
};

export default nextConfig;
