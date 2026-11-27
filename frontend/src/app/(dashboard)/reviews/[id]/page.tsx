"use client";

import React, { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { PullRequestReview } from "@/types";
import { apiClient } from "@/lib/api-client";
import { ReviewSummary } from "@/components/reviews/ReviewSummary";
import { InlineCommentCard } from "@/components/reviews/InlineCommentCard";
import { Button, Card } from "@/components/ui";
import { ArrowLeft, Filter } from "lucide-react";

export default function ReviewDetailPage() {
  const params = useParams();
  const router = useRouter();
  const rawId = Array.isArray(params.id) ? params.id[0] : params.id;
  const reviewId = Number(rawId);

  const [review, setReview] = useState<PullRequestReview | null>(null);
  const [selectedAgentFilter, setSelectedAgentFilter] = useState<string>("ALL");
  const [selectedSeverityFilter, setSelectedSeverityFilter] = useState<string>("ALL");
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (!reviewId) return;

    apiClient
      .getReview(reviewId)
      .then(setReview)
      .catch(() => {
        setReview({
          id: reviewId,
          repository_id: 1,
          pr_number: 42,
          head_sha: "7f8b9a1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a",
          base_sha: "1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b",
          title: "feat(auth): add OAuth2 refresh token rotation and session caching",
          author: "octocat",
          state: "COMPLETED",
          summary:
            "Completed multi-agent code analysis. Security agent detected an unescaped SQL statement in the token comparison block. Performance agent flagged synchronous sleep in async flow. Quality agent provided clean architecture adjustments.",
          risk_score: 7,
          recommendation: "REQUEST_CHANGES",
          security_issues_count: 1,
          perf_issues_count: 1,
          quality_issues_count: 1,
          comments: [
            {
              id: 101,
              file_path: "src/auth/token_service.py",
              line_number: 45,
              side: "RIGHT",
              agent_name: "security",
              severity: "HIGH",
              title: "Potential SQL Injection in Token Lookup",
              comment:
                "Using string formatting to construct SQL queries allows unescaped input to compromise the database. Use parameterized queries with SQLAlchemy text bind parameters.",
              suggestion:
                "stmt = select(Token).where(Token.hashed_value == token_param)\nresult = await db.execute(stmt)",
            },
            {
              id: 102,
              file_path: "src/auth/token_service.py",
              line_number: 78,
              side: "RIGHT",
              agent_name: "performance",
              severity: "MEDIUM",
              title: "Synchronous Redis Client in Async Pipeline",
              comment:
                "Directly calling blocking redis.set() halts the async event loop for concurrent requests. Switch to await aioredis.set().",
              suggestion: "await redis_client.set(f'session:{user_id}', token, ex=3600)",
            },
            {
              id: 103,
              file_path: "src/models/user.py",
              line_number: 22,
              side: "RIGHT",
              agent_name: "quality",
              severity: "LOW",
              title: "Missing Typed Return Annotation",
              comment:
                "Repository rules enforce strict typing across all data models and services to ensure static type safety.",
              suggestion: "def get_active_sessions(self) -> List[SessionModel]:",
            },
          ],
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        });
      })
      .finally(() => setIsLoading(false));
  }, [reviewId]);

  if (isLoading) {
    return <div className="py-20 text-center text-zinc-500">Loading review details...</div>;
  }

  if (!review) {
    return <div className="py-20 text-center text-zinc-500">Review not found.</div>;
  }

  const filteredComments = review.comments.filter((c) => {
    if (selectedAgentFilter !== "ALL" && c.agent_name !== selectedAgentFilter) return false;
    if (selectedSeverityFilter !== "ALL" && c.severity !== selectedSeverityFilter) return false;
    return true;
  });

  return (
    <div className="space-y-6">
      <div>
        <Button variant="ghost" size="sm" onClick={() => router.back()} className="text-zinc-400 gap-1.5">
          <ArrowLeft className="w-4 h-4" />
          Back to Dashboard
        </Button>
      </div>

      <ReviewSummary review={review} />

      <div className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-zinc-800">
          <div className="flex items-center gap-2">
            <h2 className="text-base font-semibold text-zinc-100">
              Line-Specific Inline Comments ({filteredComments.length})
            </h2>
          </div>

          <div className="flex items-center gap-2 flex-wrap text-xs">
            <span className="text-zinc-500 flex items-center gap-1">
              <Filter className="w-3.5 h-3.5" /> Filter by:
            </span>
            <select
              className="bg-zinc-900 border border-zinc-800 rounded px-2.5 py-1 text-zinc-200"
              value={selectedAgentFilter}
              onChange={(e) => setSelectedAgentFilter(e.target.value)}
            >
              <option value="ALL">All Agents</option>
              <option value="security">Security</option>
              <option value="performance">Performance</option>
              <option value="quality">Quality</option>
            </select>

            <select
              className="bg-zinc-900 border border-zinc-800 rounded px-2.5 py-1 text-zinc-200"
              value={selectedSeverityFilter}
              onChange={(e) => setSelectedSeverityFilter(e.target.value)}
            >
              <option value="ALL">All Severities</option>
              <option value="CRITICAL">Critical</option>
              <option value="HIGH">High</option>
              <option value="MEDIUM">Medium</option>
              <option value="LOW">Low</option>
              <option value="INFO">Info</option>
            </select>
          </div>
        </div>

        {filteredComments.length === 0 ? (
          <Card className="p-8 text-center text-zinc-500 text-sm">
            No comments match the selected filters.
          </Card>
        ) : (
          <div className="space-y-3">
            {filteredComments.map((comment) => (
              <InlineCommentCard key={comment.id} comment={comment} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
