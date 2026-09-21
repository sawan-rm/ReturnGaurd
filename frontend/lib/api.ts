const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:3000";

export interface ReturnRequest {
    id: string;
    order_id: string;
    reason: string;
    photo_url: string | null;
    status: "submitted" | "processing" | "approved" | "escalated" | "denied" | "completed";
    risk_score: number | null;
    created_at: string;
    updated_at: string;
}

export interface Order {
    id: string;
    user_id: string;
    product_name: string;
    product_category: string;
    amount: number;
    ordered_at: string;
}

// ── Returns ───────────────────────────────

export async function listReturns(): Promise<ReturnRequest[]> {
    const res = await fetch(`${BASE}/api/returns/`, { cache: "no-store" });
    if (!res.ok) throw new Error("Failed to fetch returns");
    return res.json();
}

export async function createReturn(order_id: string, reason: string): Promise<ReturnRequest> {
    const res = await fetch(`${BASE}/api/returns/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ order_id, reason }),
    });
    if (!res.ok) throw new Error("Failed to create return");
    return res.json();
}

// ── Orders ────────────────────────────────
// We'll hit the DB via backend in Phase 3. For now we use a mock.

export const MOCK_ORDERS: Order[] = [
    { id: "", user_id: "", product_name: "Loading...", product_category: "", amount: 0, ordered_at: "" },
];
