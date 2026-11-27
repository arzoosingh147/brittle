import NextAuth from "next-auth";
import GitHub from "next-auth/providers/github";

export const { handlers, signIn, signOut, auth } = NextAuth({
  secret: process.env.AUTH_SECRET || "brittle-pr-super-secret-key-32-chars-long!",
  providers: [
    GitHub({
      clientId: process.env.GITHUB_CLIENT_ID || "dummy_client_id",
      clientSecret: process.env.GITHUB_CLIENT_SECRET || "dummy_client_secret",
    }),
  ],
  pages: {
    signIn: "/login",
  },
  callbacks: {
    async session({ session, token }) {
      if (token.sub && session.user) {
        session.user.id = token.sub;
      }
      return session;
    },
    async jwt({ token, user }) {
      if (user) {
        token.id = user.id;
      }
      return token;
    },
  },
});
