import React from "react";
import { PullRequestReview } from "@/types";
import { Card, Badge } from "@/components/ui";
import { getRiskScoreColor, getRecommendationBadge, formatDate } from "@/utils";
import { GitPullRequest, User, Clock, AlertOctagon } from "lucide-react";

interface ReviewSummaryProps {
  review: PullRequestReview;
}

export const ReviewSummary = ({ review }: ReviewSummaryProps) => {
  const recBadge = getRecommendationBadge(review.recommendation);
  const riskClass = getRiskScoreColor(review.risk_score);

  return (
    <Card className="mb-6 space-y-4">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-zinc-800/80">
        <div>
          <div className="flex items-center gap-2 mb-1.5">
            <GitPullRequest className="w-5 h-5 text-blue-400 shrink-0" />
            <h1 className="text-xl font-bold text-zinc-100">
              PR #{review.pr_number}: {review.title || "Untitled Pull Request"}
            </h1>
          </div>
          <div className="flex items-center gap-4 text-xs text-zinc-400 flex-wrap">
            <span className="flex items-center gap-1">
              <User className="w-3.5 h-3.5" /> {review.author || "Unknown"}
            </span>
            <span>•</span>
            <span className="flex items-center gap-1 font-mono">
              commit: {review.head_sha.slice(0, 7)}
            </span>
            <span>•</span>
            <span className="flex items-center gap-1">
              <Clock className="w-3.5 h-3.5" /> {formatDate(review.created_at)}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div className={`px-3 py-1.5 rounded-lg border font-semibold text-xs flex items-center gap-1.5 ${riskClass}`}>
            <AlertOctagon className="w-4 h-4" />
            Risk: {review.risk_score}/10
          </div>
          <Badge className={`px-3 py-1.5 text-xs font-semibold ${recBadge.style}`}>
            {recBadge.text}
          </Badge>
        </div>
      </div>

      <div>
        <h3 className="text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-2">
          Executive AI Synthesis
        </h3>
        <p className="text-sm text-zinc-200 leading-relaxed bg-zinc-900/60 p-4 rounded border border-zinc-800/80">
          {review.summary || "No executive summary available for this review."}
        </p>
      </div>

      <div className="grid grid-cols-3 gap-3 pt-2 text-center">
        <div className="p-2.5 rounded bg-zinc-900/40 border border-zinc-800/60">
          <div className="text-lg font-bold text-red-400">{review.security_issues_count}</div>
          <div className="text-[11px] text-zinc-400">Security Findings</div>
        </div>
        <div className="p-2.5 rounded bg-zinc-900/40 border border-zinc-800/60">
          <div className="text-lg font-bold text-amber-400">{review.perf_issues_count}</div>
          <div className="text-[11px] text-zinc-400">Performance Findings</div>
        </div>
        <div className="p-2.5 rounded bg-zinc-900/40 border border-zinc-800/60">
          <div className="text-lg font-bold text-purple-400">{review.quality_issues_count}</div>
          <div className="text-[11px] text-zinc-400">Architecture & Rules</div>
        </div>
      </div>
    </Card>
  );
};
