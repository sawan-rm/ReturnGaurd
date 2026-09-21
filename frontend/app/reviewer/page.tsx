import ReturnCard from "../../components/ReturnCard";
import type { ReturnRequest } from "../../lib/api";

async function getReturns(): Promise<ReturnRequest[]> {
    try {
        const res = await fetch("http://backend:8000/api/returns/", { cache: "no-store" });
        if (!res.ok) return [];
        return res.json();
    } catch {
        return [];
    }
}

export default async function ReviewerPage() {
    const returns = await getReturns();

    const counts = {
        total: returns.length,
        escalated: returns.filter(r => r.status === "escalated").length,
        approved: returns.filter(r => r.status === "approved").length,
        denied: returns.filter(r => r.status === "denied").length,
    };

    return (
        <div>
            <h1 style={{ fontSize: "1.75rem", fontWeight: 700, marginBottom: "0.5rem" }}>
                Reviewer Dashboard
            </h1>
            <p style={{ color: "var(--text-muted)", marginBottom: "2rem" }}>
                All return requests — AI decisions shown when available.
            </p>

            {/* Stats row */}
            <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "1rem", marginBottom: "2rem" }}>
                {[
                    { label: "Total", value: counts.total, color: "var(--accent)" },
                    { label: "Escalated", value: counts.escalated, color: "var(--warning)" },
                    { label: "Approved", value: counts.approved, color: "var(--success)" },
                    { label: "Denied", value: counts.denied, color: "var(--danger)" },
                ].map(stat => (
                    <div key={stat.label} className="card" style={{ textAlign: "center" }}>
                        <div style={{ fontSize: "2rem", fontWeight: 700, color: stat.color }}>{stat.value}</div>
                        <div style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>{stat.label}</div>
                    </div>
                ))}
            </div>

            {/* Returns list */}
            {returns.length === 0 ? (
                <div className="card" style={{ textAlign: "center", color: "var(--text-muted)", padding: "3rem" }}>
                    No returns yet. Submit one from the shop!
                </div>
            ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
                    {returns.map(ret => <ReturnCard key={ret.id} ret={ret} />)}
                </div>
            )}
        </div>
    );
}
