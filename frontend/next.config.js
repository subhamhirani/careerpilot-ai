/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  async rewrites() {
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
