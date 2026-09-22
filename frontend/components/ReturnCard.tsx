"use client"; // <-- Add this to make it a client component!
import { useState, useEffect } from "react";
import StatusBadge from "./StatusBadge";
import type { ReturnRequest } from "@/lib/api";

export default function ReturnCard({ ret: initialRet }: { ret: ReturnRequest }) {
    const [ret, setRet] = useState(initialRet);

    useEffect(() => {
        // Listen for WebSocket updates
        const ws = new WebSocket("ws://localhost:8000/ws");

        ws.onmessage = (event) => {
            const update = JSON.parse(event.data);
            if (update.id === ret.id) {
                setRet(prev => ({
                    ...prev,
                    status: update.status,
                    risk_score: update.risk_score ?? prev.risk_score
                }));
            }
        };

        return () => ws.close();
    }, [ret.id]);

    return (
        <div className="card" style={{ display: "flex", flexDirection: "column", gap: "0.75rem", transition: "all 0.3s" }}>
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
