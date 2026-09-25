const BASE = "/api";  // Vite proxy handles this

export interface ReturnRequest {
    id: string; order_id: string; reason: string;
    photo_url: string | null;
    status: "submitted" | "processing" | "approved" | "escalated" | "denied" | "completed";
    risk_score: number | null;
    created_at: string; updated_at: string;
}

export interface Order {
    id: string; user_id: string; product_name: string;
    product_category: string; amount: number; ordered_at: string;
}

export async function listOrders(token: string): Promise<Order[]> {
    const res = await fetch(`${BASE}/orders/`, {
        headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) throw new Error("Failed to fetch orders");
    return res.json();
}

export async function listReturns(): Promise<ReturnRequest[]> {
    const res = await fetch(`${BASE}/returns/`);
    if (!res.ok) throw new Error("Failed to fetch returns");
    return res.json();
}

export async function createReturn(order_id: string, reason: string, token: string, photo?: File): Promise<ReturnRequest> {
    const formData = new FormData();
    formData.append("order_id", order_id);
    formData.append("reason", reason);
    if (photo) {
        formData.append("photo", photo);
    }

    const res = await fetch(`${BASE}/returns/`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
    });
    if (!res.ok) throw new Error("Failed to create return");
    return res.json();
}
