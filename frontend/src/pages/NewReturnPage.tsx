import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import type Keycloak from "keycloak-js";
import { listOrders, createReturn } from "../lib/api";
import type { Order } from "../lib/api";

interface Props { kc: Keycloak; }

export default function NewReturnPage({ kc }: Props) {
    const navigate = useNavigate();
    const [orders, setOrders] = useState<Order[]>([]);
    const [orderId, setOrderId] = useState("");
    const [reason, setReason] = useState("");
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");

    useEffect(() => {
        if (!kc.token) return;
        listOrders(kc.token)
            .then(setOrders)
            .catch(() => setError("Could not load orders."));
    }, [kc.token]);

    async function handleSubmit(e: React.FormEvent) {
        e.preventDefault();
        if (!orderId || !reason.trim()) { setError("Please select an order and enter a reason."); return; }
        if (!kc.token) { setError("Not authenticated."); return; }
        setLoading(true); setError("");
        try {
            await createReturn(orderId, reason, kc.token);
            navigate("/reviewer");
        } catch (err: unknown) {
            setError(err instanceof Error ? err.message : "Something went wrong");
        } finally {
            setLoading(false);
        }
    }

    return (
        <div style={{ maxWidth: "560px", margin: "0 auto" }}>
            <h1 style={{ fontSize: "1.75rem", fontWeight: 700, marginBottom: "0.5rem" }}>Submit a Return</h1>
            <p style={{ color: "var(--text-muted)", marginBottom: "2rem" }}>Fill in the form below. Our AI reviews every request fairly.</p>

            <form onSubmit={handleSubmit} className="card" style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
                <div>
                    <label htmlFor="order-select">Select Order</label>
                    <select id="order-select" value={orderId} onChange={e => setOrderId(e.target.value)} required>
                        <option value="">— choose an order —</option>
                        {orders.map(o => (
                            <option key={o.id} value={o.id}>{o.product_name} — ${o.amount.toFixed(2)}</option>
                        ))}
                    </select>
                </div>

                <div>
                    <label htmlFor="reason">Reason for Return</label>
                    <textarea id="reason" value={reason} onChange={e => setReason(e.target.value)}
                        placeholder="Describe what happened with your order..." rows={4} required />
                </div>

                <div>
                    <label htmlFor="photo">Photo (optional)</label>
                    <input id="photo" type="file" accept="image/*" style={{ padding: "0.5rem" }} />
                    <span style={{ fontSize: "0.78rem", color: "var(--text-muted)", marginTop: "0.25rem", display: "block" }}>
                        MinIO photo upload coming in Phase 5.
                    </span>
                </div>

                {error && (
                    <div style={{ background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.3)", borderRadius: "8px", padding: "0.75rem", color: "#ef4444", fontSize: "0.875rem" }}>
                        {error}
                    </div>
                )}

                <button id="submit-return-btn" type="submit" className="btn-primary" disabled={loading}>
                    {loading ? "Submitting…" : "Submit Return →"}
                </button>
            </form>
        </div>
    );
}
