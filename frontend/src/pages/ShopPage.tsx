import { useNavigate } from "react-router-dom";

const products = [
    { name: "Wireless Earbuds", category: "Electronics", price: "$49.99", emoji: "🎧" },
    { name: "Running Sneakers", category: "Clothing", price: "$89.99", emoji: "👟" },
    { name: "Blender Pro", category: "Home", price: "$34.99", emoji: "🥤" },
    { name: "Python Cookbook", category: "Books", price: "$29.99", emoji: "📚" },
    { name: "LEGO City Set", category: "Toys", price: "$59.99", emoji: "🧱" },
    { name: "USB-C Hub", category: "Electronics", price: "$24.99", emoji: "🔌" },
];

export default function ShopPage() {
    const navigate = useNavigate();
    return (
        <div>
            <div style={{
                textAlign: "center", padding: "4rem 0 3rem",
                background: "radial-gradient(ellipse at 50% 0%, rgba(124,106,247,0.12) 0%, transparent 70%)",
                borderRadius: "16px", marginBottom: "3rem",
            }}>
                <h1 style={{ fontSize: "2.5rem", fontWeight: 700, marginBottom: "1rem" }}>🛡️ ReturnGuard Store</h1>
                <p style={{ color: "var(--text-muted)", fontSize: "1.1rem", marginBottom: "2rem" }}>
                    AI-governed returns — fast, fair, transparent.
                </p>
                <button className="btn-primary" style={{ fontSize: "1rem", padding: "0.875rem 2rem" }}
                    onClick={() => navigate("/returns/new")}>
                    Submit a Return →
                </button>
            </div>

            <h2 style={{ fontSize: "1.25rem", fontWeight: 600, marginBottom: "1.25rem" }}>Featured Products</h2>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(240px, 1fr))", gap: "1rem" }}>
                {products.map((p) => (
                    <div key={p.name} className="card" style={{ display: "flex", flexDirection: "column", gap: "0.5rem", transition: "transform 0.2s, box-shadow 0.2s" }}
                        onMouseEnter={e => { (e.currentTarget as HTMLDivElement).style.transform = "translateY(-4px)"; (e.currentTarget as HTMLDivElement).style.boxShadow = "0 8px 32px rgba(124,106,247,0.2)"; }}
                        onMouseLeave={e => { (e.currentTarget as HTMLDivElement).style.transform = ""; (e.currentTarget as HTMLDivElement).style.boxShadow = ""; }}
                    >
                        <div style={{ fontSize: "2.5rem" }}>{p.emoji}</div>
                        <div style={{ fontWeight: 600 }}>{p.name}</div>
                        <div style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>{p.category}</div>
                        <div style={{ color: "var(--accent-light)", fontWeight: 700 }}>{p.price}</div>
                    </div>
                ))}
            </div>
        </div>
    );
}
