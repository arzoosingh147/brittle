import React from "react";
import { Card, Button } from "@/components/ui";
import { ShieldCheck, GitPullRequest, Terminal, Sparkles } from "lucide-react";
import { signIn } from "@/lib/auth";

export default function LoginPage() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[70vh]">
      <Card className="w-full max-w-md p-8 text-center space-y-6 bg-zinc-900/80 border-zinc-800">
        <div className="w-12 h-12 rounded-xl bg-blue-600 mx-auto flex items-center justify-center text-white shadow-lg shadow-blue-500/20">
          <ShieldCheck className="w-7 h-7" />
        </div>

        <div>
          <h1 className="text-2xl font-bold tracking-tight text-zinc-100">Welcome to Brittle</h1>
          <p className="text-xs text-zinc-400 mt-1.5">
            Production-grade autonomous AI code reviewer for your GitHub Pull Requests.
          </p>
        </div>

        <div className="space-y-2 text-left bg-zinc-950 p-4 rounded-lg border border-zinc-800/80 text-xs text-zinc-300">
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-blue-400 shrink-0" />
            <span>Parallel Multi-Agent review (Security, Perf, Quality)</span>
          </div>
          <div className="flex items-center gap-2">
            <Terminal className="w-4 h-4 text-emerald-400 shrink-0" />
            <span>Exact GitHub inline diff comments & code fixes</span>
          </div>
          <div className="flex items-center gap-2">
            <GitPullRequest className="w-4 h-4 text-purple-400 shrink-0" />
            <span>Vector-indexed cross-file repository context</span>
          </div>
        </div>

        <form
          action={async () => {
            "use server";
            await signIn("github");
          }}
        >
          <Button variant="primary" size="lg" className="w-full" type="submit">
            Continue with GitHub
          </Button>
        </form>

        <p className="text-[11px] text-zinc-500">
          By signing in, you connect your GitHub repositories with Brittle AI Webhooks.
        </p>
      </Card>
    </div>
  );
}
