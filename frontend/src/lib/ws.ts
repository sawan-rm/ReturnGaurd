// Module-level singleton — created once, shared across the app.
// React StrictMode mounts/unmounts components twice in dev; a module-level
// variable is NOT affected by component lifecycles.

type UpdateListener = (id: string, status: string, riskScore?: number) => void;
const listeners = new Set<UpdateListener>();

let ws: WebSocket | null = null;

function connect() {
    if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) return;

    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    ws = new WebSocket(`${protocol}//${window.location.host}/ws`);

    ws.onmessage = (event) => {
        try {
            const update = JSON.parse(event.data);
            listeners.forEach(fn => fn(update.id, update.status, update.risk_score));
        } catch { /* ignore bad frames */ }
    };

    ws.onclose = () => {
        // Reconnect after 3 seconds if the page is still open
        setTimeout(() => { if (listeners.size > 0) connect(); }, 3000);
    };

    ws.onerror = () => ws?.close();
}

export function subscribeWS(listener: UpdateListener): () => void {
    listeners.add(listener);
    connect();                        // ensure connected
    return () => listeners.delete(listener);   // unsubscribe on cleanup
}
