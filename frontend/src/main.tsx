import React from "react";
import ReactDOM from "react-dom/client";
import App from "../src/App";
import "./index.css";
import keycloak from "../src/auth/keycloak";

// Init Keycloak BEFORE rendering the app
// onLoad: "login-required" means user must log in to see anything
keycloak
    .init({ onLoad: "login-required", pkceMethod: "S256" })
    .then(() => {
        ReactDOM.createRoot(document.getElementById("root")!).render(
            <React.StrictMode>
                <App kc={keycloak} />
            </React.StrictMode>
        );
    })
    .catch(() => {
        document.body.innerHTML = "<p style='color:white;padding:2rem'>Failed to connect to Keycloak. Is it running?</p>";
    });
