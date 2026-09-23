import { Link, useLocation } from "react-router-dom";
import type Keycloak from "keycloak-js";

interface Props { kc: Keycloak; }

export default function Navbar({ kc }: Props) {
    const { pathname } = useLocation();

    const links = [
        { href: "/", label: "Shop" },
        { href: "/returns/new", label: "Submit Return" },
        { href: "/reviewer", label: "Reviewer" },
    ];

    const username = (kc.tokenParsed as { preferred_username?: string })?.preferred_username ?? "User";

    return (
        <nav style={{
            background: "var(--surface)", borderBottom: "1px solid var(--border)",
            padding: "0 2rem", display: "flex", alignItems: "center",
            justifyContent: "space-between", height: "60px",
            position: "sticky", top: 0, zIndex: 100,
        }}>
            <span style={{ fontWeight: 700, fontSize: "1.1rem", color: "var(--accent-light)" }}>
                🛡️ ReturnGuard
            </span>
            <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
                {links.map(({ href, label }) => (
                    <Link key={href} to={href} style={{
                        padding: "0.5rem 1rem", borderRadius: "6px", fontWeight: 500, fontSize: "0.9rem",
                        color: pathname === href ? "var(--accent-light)" : "var(--text-muted)",
                        background: pathname === href ? "rgba(124,106,247,0.15)" : "transparent",
                        transition: "all 0.2s",
                    }}>
                        {label}
                    </Link>
                ))}
                <div style={{ width: "1px", height: "24px", background: "var(--border)", margin: "0 0.5rem" }} />
                <button onClick={() => kc.logout()} className="btn-secondary" style={{ padding: "0.4rem 1rem", fontSize: "0.85rem" }}>
                    Logout ({username})
                </button>
            </div>
        </nav>
    );
}
