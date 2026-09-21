"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { signIn, signOut, useSession } from "next-auth/react";

export default function Navbar() {
    const path = usePathname();
    const { data: session } = useSession();

    const links = [
        { href: "/", label: "Shop" },
        { href: "/returns/new", label: "Submit Return" },
        { href: "/reviewer", label: "Reviewer" },
    ];

    return (
        <nav style={{
            background: "var(--surface)",
            borderBottom: "1px solid var(--border)",
            padding: "0 2rem",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            height: "60px",
            position: "sticky",
            top: 0,
            zIndex: 100,
        }}>
            <span href="/" style={{ fontWeight: 700, fontSize: "1.1rem", color: "var(--accent-light)", cursor: "pointer" }}>
                🛡️ ReturnGuard
            </span>
            <div style={{ display: "flex", gap: "0.5rem" }}>
                {links.map(({ href, label }) => (
                    <Link key={href} href={href} style={{
                        padding: "0.5rem 1rem",
                        borderRadius: "6px",
                        fontWeight: 500,
                        fontSize: "0.9rem",
                        color: path === href ? "var(--accent-light)" : "var(--text-muted)",
                        background: path === href ? "rgba(124,106,247,0.15)" : "transparent",
                        transition: "all 0.2s",
                    }}>
                        {label}
                    </Link>
                ))}
                <div style={{ width: "1px", height: "24px", background: "var(--border)", margin: "0 0.5rem" }} />

                {session ? (
                    <button onClick={() => signOut()} className="btn-secondary" style={{ padding: "0.4rem 1rem" }}>
                        Logout ({session.user?.name || 'User'})
                    </button>
                ) : (
                    <button onClick={() => signIn("keycloak")} className="btn-primary" style={{ padding: "0.4rem 1rem" }}>
                        Login
                    </button>
                )}
            </div>
        </nav>
    );
}
