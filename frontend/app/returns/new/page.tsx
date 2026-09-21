"use client";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";

interface Order {
    id: string;
    product_name: string;
    amount: number;
}

export default function NewReturnPage() {
    const router = useRouter();
    const [orders, setOrders] = useState<Order[]>([]);
    const [orderId, setOrderId] = useState("");
    const [reason, setReason] = useState("");
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");

    // Fetch real orders from backend
    useEffect(() => {
        fetch("/api/orders/")
            .then(r => r.json())
            .then(setOrders)
            .catch(() => setError("Could not load orders."));
    }, []);

    async function handleSubmit(e: React.FormEvent) {
        e.preventDefault();
        if (!orderId || !reason.trim()) {
            setError("Please select an order and enter a reason.");
            return;
        }
        setLoading(true);
        setError("");
        try {
            const res = await fetch("/api/returns/", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ order_id: orderId, reason }),
            });
            if (!res.ok) throw new Error(await res.text());
            router.push("/reviewer");
        } catch (err: unknown) {
            setError(err instanceof Error ? err.message : "Something went wrong");
        } finally {
            setLoading(false);
        }
    }

    return (
        <div style={{ maxWidth: "560px", margin: "0 auto" }}>
            <h1 style={{ fontSize: "1.75rem", fontWeight: 700, marginBottom: "0.5rem" }}>
                Submit a Return
            </h1>
            <p style={{ color: "var(--text-muted)", marginBottom: "2rem" }}>
                Fill in the form below. Our AI reviews every request fairly.
            </p>

            <form onSubmit={handleSubmit} className="card" style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
                {/* Order selector */}
                <div>
                    <label htmlFor="order-select">Select Order</label>
                    <select
                        id="order-select"
                        value={orderId}
                        onChange={e => setOrderId(e.target.value)}
                        required
                    >
                        <option value="">— choose an order —</option>
                        {orders.map(o => (
                            <option key={o.id} value={o.id}>
                                {o.product_name} — ${o.amount.toFixed(2)}
                            </option>
                        ))}
                    </select>
                </div>

                {/* Reason */}
                <div>
                    <label htmlFor="reason">Reason for Return</label>
                    <textarea
                        id="reason"
                        value={reason}
                        onChange={e => setReason(e.target.value)}
                        placeholder="Describe what happened with your order..."
                        rows={4}
                        required
                    />
                </div>

                {/* Photo (stored locally for now — MinIO upload comes in Phase 4) */}
                <div>
                    <label htmlFor="photo">Photo (optional)</label>
                    <input id="photo" type="file" accept="image/*" style={{ padding: "0.5rem" }} />
                    <span style={{ fontSize: "0.78rem", color: "var(--text-muted)", marginTop: "0.25rem", display: "block" }}>
                        Photo upload will be wired to MinIO in Phase 4.
                    </span>
                </div>

                {error && (
                    <div style={{
                        background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.3)",
                        borderRadius: "8px", padding: "0.75rem", color: "#ef4444", fontSize: "0.875rem"
                    }}>
                        {error}
                    </div>
                )}

                <button
                    id="submit-return-btn"
                    type="submit"
                    className="btn-primary"
                    disabled={loading}
                    style={{ opacity: loading ? 0.7 : 1 }}
                >
                    {loading ? "Submitting…" : "Submit Return →"}
                </button>
            </form>
        </div>
    );
}
