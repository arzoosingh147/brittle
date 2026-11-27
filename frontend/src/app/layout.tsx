import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";
import { ShieldCheck, Database, LayoutDashboard } from "lucide-react";

export const metadata: Metadata = {
  title: "Brittle — AI Pull Request & Codebase Reviewer",
  description: "Autonomous multi-agent code reviewer powered by LangGraph, pgvector, and Google Gemini.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark" suppressHydrationWarning>
      <body className="bg-zinc-950 text-zinc-100 antialiased min-h-screen flex flex-col" suppressHydrationWarning>
        {/* Navigation Bar */}
        <header className="sticky top-0 z-40 border-b border-zinc-800/80 bg-zinc-950/80 backdrop-blur-md">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
            <div className="flex items-center gap-8">
              <Link href="/dashboard" className="flex items-center gap-2.5 font-bold text-lg tracking-tight">
                <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center text-white shadow-md shadow-blue-500/20">
                  <ShieldCheck className="w-5 h-5" />
                </div>
                <span>Brittle<span className="text-blue-500 font-mono text-sm ml-1">PR</span></span>
              </Link>

              <nav className="hidden md:flex items-center gap-1 text-sm font-medium">
                <Link
                  href="/dashboard"
                  className="px-3 py-1.5 rounded-md text-zinc-300 hover:text-white hover:bg-zinc-800/60 transition-colors flex items-center gap-1.5"
                >
                  <LayoutDashboard className="w-4 h-4" />
                  Dashboard
                </Link>
                <Link
                  href="/repos"
                  className="px-3 py-1.5 rounded-md text-zinc-300 hover:text-white hover:bg-zinc-800/60 transition-colors flex items-center gap-1.5"
                >
                  <Database className="w-4 h-4" />
                  Repositories
                </Link>
              </nav>
            </div>

            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2 text-xs text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2.5 py-1 rounded-full">
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                Agent Pipeline Online
              </div>
            </div>
          </div>
        </header>

        {/* Main Content */}
        <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {children}
        </main>

        {/* Footer */}
        <footer className="border-t border-zinc-800/60 py-6 text-center text-xs text-zinc-500">
          <p>© 2026 Brittle AI Reviewer — Parallel Multi-Agent Code Review & Vector Store Indexing</p>
        </footer>
      </body>
    </html>
  );
}
