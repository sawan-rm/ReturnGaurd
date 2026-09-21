import StatusBadge from "./StatusBadge";
import type { ReturnRequest } from "../lib/api";

export default function ReturnCard({ ret }: { ret: ReturnRequest }) {
    return (
        <div className="card" style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ fontFamily: "monospace", fontSize: "0.8rem", color: "var(--text-muted)" }}>
                    #{ret.id.slice(0, 8)}
                </span>
                <StatusBadge status={ret.status} />
            </div>
            <p style={{ color: "var(--text)", lineHeight: 1.5 }}>{ret.reason}</p>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.82rem", color: "var(--text-muted)" }}>
                <span>Order: {ret.order_id.slice(0, 8)}</span>
                {ret.risk_score !== null && (
                    <span>Risk: <strong style={{ color: ret.risk_score > 0.6 ? "var(--danger)" : "var(--success)" }}>
                        {(ret.risk_score * 100).toFixed(0)}%
                    </strong></span>
                )}
                <span>{new Date(ret.created_at).toLocaleDateString()}</span>
            </div>
        </div>
    );
}
