import type { Metadata } from "next";
import "./globals.css";
import Navbar from "../components/Navbar";
import { SessionProvider } from "next-auth/react";

export const metadata: Metadata = {
    title: "ReturnGuard",
    description: "AI-governed return and refund management",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
    return (
        <html lang="en">
            <body>
                <SessionProvider>
                    <Navbar />
                    <main style={{ maxWidth: "1100px", margin: "0 auto", padding: "2rem 1rem" }}>
                        {children}
                    </main>
                </SessionProvider>
            </body>
        </html>
    );
}
