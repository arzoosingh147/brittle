"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { PullRequestReview, ReviewMetricsSummary } from "@/types";
import { apiClient } from "@/lib/api-client";
import { MetricsGrid } from "@/components/reviews/MetricsGrid";
import { Card, Badge, Button } from "@/components/ui";
import { formatDate, getRecommendationBadge, getRiskScoreColor } from "@/utils";
import { GitPullRequest, ArrowRight, RefreshCw, Sparkles, PlusCircle } from "lucide-react";

export default function DashboardPage() {
  const [metrics, setMetrics] = useState<ReviewMetricsSummary | null>(null);
  const [reviews, setReviews] = useState<PullRequestReview[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSimulating, setIsSimulating] = useState(false);

  const fetchData = async () => {
    setIsLoading(true);
    try {
      const [m, r] = await Promise.all([
        apiClient.getMetrics().catch(() => ({
          total_reviews: 0,
          avg_risk_score: 0.0,
          total_security_issues: 0,
          total_perf_issues: 0,
          total_quality_issues: 0,
          total_issues: 0,
        })),
        apiClient.getReviews().catch(() => [] as PullRequestReview[]),
      ]);
      setMetrics(m);
      setReviews(r);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSimulateReview = async () => {
    setIsSimulating(true);
    try {
      await apiClient.simulateReview();
      await fetchData();
    } catch (e) {
      console.error("Simulation failed:", e);
    } finally {
      setIsSimulating(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  return (
    <div className="space-y-8">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-zinc-100">Live AI Review Analytics</h1>
          <p className="text-sm text-zinc-400 mt-1">
            Real-time multi-agent code analysis metrics and persistent Pull Request reviews.
          </p>
        </div>
        <div className="flex items-center gap-2.5">
          <Button variant="secondary" size="sm" onClick={fetchData} disabled={isLoading}>
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? "animate-spin" : ""}`} />
            Refresh
          </Button>
          <Button variant="primary" size="sm" onClick={handleSimulateReview} disabled={isSimulating}>
            <Sparkles className={`w-3.5 h-3.5 ${isSimulating ? "animate-spin" : ""}`} />
            {isSimulating ? "Running Agents..." : "Trigger Live PR Review"}
          </Button>
        </div>
      </div>

      {/* Real-time Metrics Grid */}
      {metrics && <MetricsGrid metrics={metrics} />}

      {/* Recent Reviews Table */}
      <Card className="p-0 overflow-hidden">
        <div className="p-5 border-b border-zinc-800 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <GitPullRequest className="w-5 h-5 text-blue-400" />
            <h2 className="font-semibold text-zinc-100">Pull Request Reviews ({reviews.length})</h2>
          </div>
          <Link href="/repos" className="text-xs text-blue-400 hover:text-blue-300 flex items-center gap-1">
            Manage Repositories <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        {reviews.length === 0 ? (
          <div className="p-12 text-center space-y-4">
            <div className="w-12 h-12 rounded-full bg-blue-500/10 text-blue-400 mx-auto flex items-center justify-center">
              <GitPullRequest className="w-6 h-6" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-zinc-200">No PR reviews in database yet</h3>
              <p className="text-xs text-zinc-400 max-w-sm mx-auto mt-1">
                Trigger a live review now to test the real-time AI pipeline, or connect GitHub webhooks to review incoming PRs automatically.
              </p>
            </div>
            <Button variant="primary" size="sm" onClick={handleSimulateReview} disabled={isSimulating}>
              <PlusCircle className="w-4 h-4 mr-1.5" />
              {isSimulating ? "Running Live Pipeline..." : "Create First Live PR Review"}
            </Button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-zinc-900/50 text-xs text-zinc-400 uppercase border-b border-zinc-800">
                <tr>
                  <th className="px-5 py-3">Pull Request</th>
                  <th className="px-5 py-3">Risk Score</th>
                  <th className="px-5 py-3">Recommendation</th>
                  <th className="px-5 py-3">Findings</th>
                  <th className="px-5 py-3">Reviewed At</th>
                  <th className="px-5 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-800/60">
                {reviews.map((r) => {
                  const rec = getRecommendationBadge(r.recommendation);
                  return (
                    <tr key={r.id} className="hover:bg-zinc-900/30 transition-colors">
                      <td className="px-5 py-4">
                        <Link href={`/reviews/${r.id}`} className="font-medium text-zinc-100 hover:text-blue-400 block max-w-md truncate">
                          #{r.pr_number}: {r.title || "Untitled Pull Request"}
                        </Link>
                        <span className="text-xs text-zinc-500">by {r.author}</span>
                      </td>
                      <td className="px-5 py-4">
                        <span className={`px-2 py-0.5 rounded text-xs font-semibold border ${getRiskScoreColor(r.risk_score)}`}>
                          {r.risk_score} / 10
                        </span>
                      </td>
                      <td className="px-5 py-4">
                        <Badge className={rec.style}>{rec.text}</Badge>
                      </td>
                      <td className="px-5 py-4 text-xs space-x-2">
                        {r.security_issues_count > 0 && (
                          <span className="text-red-400 font-medium">
                            {r.security_issues_count} Sec
                          </span>
                        )}
                        {r.perf_issues_count > 0 && (
                          <span className="text-amber-400 font-medium">
                            {r.perf_issues_count} Perf
                          </span>
                        )}
                        {r.quality_issues_count > 0 && (
                          <span className="text-purple-400 font-medium">
                            {r.quality_issues_count} Quality
                          </span>
                        )}
                        {r.security_issues_count === 0 && r.perf_issues_count === 0 && r.quality_issues_count === 0 && (
                          <span className="text-emerald-400">All Clear</span>
                        )}
                      </td>
                      <td className="px-5 py-4 text-xs text-zinc-400">
                        {formatDate(r.created_at)}
                      </td>
                      <td className="px-5 py-4 text-right">
                        <Link href={`/reviews/${r.id}`}>
                          <Button variant="outline" size="sm">
                            View Diff
                          </Button>
                        </Link>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
