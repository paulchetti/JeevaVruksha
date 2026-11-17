import type { NextAuthOptions } from "next-auth";

const issuer = process.env.OIDC_ISSUER?.replace(/\/$/, "");
const clientId = process.env.OIDC_CLIENT_ID;
const clientSecret = process.env.OIDC_CLIENT_SECRET;
const oidcConfigured = Boolean(issuer && clientId && clientSecret);

if (
  process.env.NODE_ENV === "production" &&
  process.env.NEXT_PHASE !== "phase-production-build" &&
  (!oidcConfigured || !process.env.NEXTAUTH_SECRET)
) {
  throw new Error("Production requires OIDC credentials and NEXTAUTH_SECRET.");
}

export const authOptions: NextAuthOptions = {
  secret: process.env.NEXTAUTH_SECRET,
  session: { strategy: "jwt" },
  providers: oidcConfigured
    ? [
        {
          id: "institution",
          name: "Institutional sign-in",
          type: "oauth",
          wellKnown: `${issuer}/.well-known/openid-configuration`,
          clientId,
          clientSecret,
          idToken: true,
          checks: ["pkce", "state"],
          authorization: { params: { scope: "openid email profile" } },
          profile(profile) {
            return {
              id: profile.sub,
              name: profile.name ?? profile.preferred_username ?? null,
              email: profile.email ?? null,
            };
          },
        },
      ]
    : [],
  callbacks: {
    async jwt({ token, account }) {
      if (account?.access_token) {
        token.apiAccessToken = account.access_token;
      }
      return token;
    },
  },
};
