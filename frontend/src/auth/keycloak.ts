import Keycloak from "keycloak-js";

const keycloak = new Keycloak({
    url: "http://localhost:8080",
    realm: "returnguard",
    clientId: "nextjs-client",  // reusing the same client
});

export default keycloak;
