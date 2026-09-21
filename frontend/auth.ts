import NextAuth from "next-auth";
import Keycloak from "next-auth/providers/keycloak";

export const { handlers, signIn, signOut, auth } = NextAuth({
    providers: [Keycloak],
    callbacks: {
        async jwt({ token, account }) {
            // Persist the access token so we can send it to FastAPI
            if (account) {
                token.accessToken = account.access_token;
            }
            return token;
        },
        async session({ session, token }) {
            // @ts-expect-error - we are adding a custom property
            session.accessToken = token.accessToken;
            return session;
        },
    },
});
