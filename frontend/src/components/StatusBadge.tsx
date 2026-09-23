const colors: Record<string, string> = {
    submitted: "#7c6af7", processing: "#f59e0b", approved: "#22c55e",
    escalated: "#f97316", denied: "#ef4444", completed: "#06b6d4",
};

export default function StatusBadge({ status }: { status: string }) {
    const color = colors[status] ?? "#888";
    return (
        <span style={{
            background: `${color}22`, color, border: `1px solid ${color}44`,
            padding: "0.25rem 0.75rem", borderRadius: "999px",
            fontSize: "0.78rem", fontWeight: 600, textTransform: "capitalize",
        }}>
            {status}
        </span>
    );
}
