/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  // For Vercel deployment, API routes proxy to production backend
  // For local Docker, they proxy to internal backend service
  async rewrites() {
    const isVercel = process.env.VERCEL === '1';
    if (isVercel) {
      return [
        {
          source: '/api/:path*',
          destination: 'https://careerpilot-backend.onrender.com/api/:path*',
        },
      ];
    }
    return [
      {
        source: '/api/:path*',
        destination: 'http://backend:7899/api/:path*',
      },
    ];
  },
  images: {
    domains: ['localhost', 'ui-avatars.com'],
  },
};

module.exports = nextConfig;