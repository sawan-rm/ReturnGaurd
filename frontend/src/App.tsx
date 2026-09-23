import { BrowserRouter, Routes, Route } from "react-router-dom";
import type Keycloak from "keycloak-js";
import Navbar from "./components/Navbar";
import ShopPage from './pages/ShopPage'
import NewReturnPage from "./pages/NewReturnPage";
import ReviewerPage from "./pages/ReviewerPage";

interface Props { kc: Keycloak; }

export default function App({ kc }: Props) {
    return (
        <BrowserRouter>
            <Navbar kc={kc} />
            <main style={{ maxWidth: "1100px", margin: "0 auto", padding: "2rem 1rem" }}>
                <Routes>
                    <Route path="/" element={<ShopPage />} />
                    <Route path="/returns/new" element={<NewReturnPage kc={kc} />} />
                    <Route path="/reviewer" element={<ReviewerPage />} />
                </Routes>
            </main>
        </BrowserRouter>
    );
}
