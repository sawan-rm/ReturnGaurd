import { useState, useEffect } from "react";
import type Keycloak from "keycloak-js";
import StatusBadge from "./StatusBadge";
import { resumeReturn } from "../lib/api";

interface ReturnRequest {
    id: string; order_id: string; reason: string;
    photo_url?: string | null;
    status: string; risk_score: number | null; created_at: string;
}

interface Props {
    ret: ReturnRequest;
    kc?: Keycloak;
    onUpdate?: () => void;
}

export default function ReturnCard({ ret: initialRet, kc, onUpdate }: Props) {
    const [ret, setRet] = useState(initialRet);
    const [resuming, setResuming] = useState(false);

    useEffect(() => {
        const ws = new WebSocket("ws://localhost:8000/ws");
        ws.onmessage = (event) => {
            const update = JSON.parse(event.data);
            if (update.id === ret.id) {
                setRet(prev => ({ ...prev, status: update.status, risk_score: update.risk_score ?? prev.risk_score }));
            }
        };
        return () => {
            if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
                setTimeout(() => ws.close(), 100);
            }
        };
    }, [ret.id]);

    const handleResume = async (action: "confirm_deny" | "override_approve") => {
        if (!kc?.token) return alert("Not authenticated");
        setResuming(true);
        try {
            await resumeReturn(ret.id, action, kc.token);
            onUpdate?.();
        } catch (err) {
            console.error(err);
            alert("Failed to resume return");
        } finally {
            setResuming(false);
        }
    };

    return (
        <div className="card" style={{ display: "flex", flexDirection: "column", gap: "0.75rem", transition: "all 0.3s" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ fontFamily: "monospace", fontSize: "0.8rem", color: "var(--text-muted)" }}>
                    #{ret.id.slice(0, 8)}
                </span>
                <StatusBadge status={ret.status} />
            </div>
            <div style={{ display: "flex", gap: "1rem" }}>
                {ret.photo_url && (
                    <img 
                        src={ret.photo_url} 
                        alt="Return Item" 
                        style={{ width: "80px", height: "80px", objectFit: "cover", borderRadius: "8px" }} 
                    />
                )}
                <p style={{ color: "var(--text)", lineHeight: 1.5, margin: 0 }}>{ret.reason}</p>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.82rem", color: "var(--text-muted)" }}>
                <span>Order: {ret.order_id.slice(0, 8)}</span>
                {ret.risk_score !== null && (
                    <span>Risk: <strong style={{ color: ret.risk_score > 0.6 ? "var(--danger)" : "var(--success)" }}>
                        {(ret.risk_score * 100).toFixed(0)}%
                    </strong></span>
                )}
                <span>{new Date(ret.created_at).toLocaleDateString()}</span>
            </div>

            {/* HITL Buttons — only show for escalated returns */}
            {ret.status === "escalated" && kc && (
                <div style={{ display: "flex", gap: "0.75rem", marginTop: "0.25rem" }}>
                    <button
                        onClick={() => handleResume("confirm_deny")}
                        disabled={resuming}
                        style={{
                            flex: 1, padding: "0.6rem", border: "none", borderRadius: "8px", cursor: "pointer",
                            background: "var(--danger)", color: "white", fontWeight: 600, fontSize: "0.85rem",
                            opacity: resuming ? 0.6 : 1,
                        }}
                    >
                        {resuming ? "Processing..." : "✋ Confirm Denial"}
                    </button>
                    <button
                        onClick={() => handleResume("override_approve")}
                        disabled={resuming}
                        style={{
                            flex: 1, padding: "0.6rem", border: "none", borderRadius: "8px", cursor: "pointer",
                            background: "var(--success)", color: "white", fontWeight: 600, fontSize: "0.85rem",
                            opacity: resuming ? 0.6 : 1,
                        }}
                    >
                        {resuming ? "Processing..." : "✅ Override → Approve"}
                    </button>
                </div>
            )}
        </div>
    );
}
