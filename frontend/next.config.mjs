/** @type {import('next').NextConfig} */
const nextConfig = {
    // Allow requests to backend container
    async rewrites() {
        return {
            fallback: [
                {
                    source: "/api/:path*",
                    destination: `${process.env.BACKEND_URL}/api/:path*`,
                },
            ],
        };
    },
};

export default nextConfig;
