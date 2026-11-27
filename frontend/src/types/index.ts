export type IndexingStatus = "PENDING" | "INDEXING" | "COMPLETED" | "FAILED";
export type ReviewState = "PENDING" | "REVIEWING" | "COMPLETED" | "FAILED";
export type ReviewRecommendation = "APPROVE" | "REQUEST_CHANGES" | "COMMENT";
export type CommentSeverity = "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | "INFO";
export type CommentSide = "RIGHT" | "LEFT";

export interface Repository {
  id: number;
  github_repo_id: number;
  name: string;
  full_name: string;
  owner: string;
  is_private: boolean;
  default_branch: string;
  indexing_status: IndexingStatus;
  last_indexed_at: string | null;
  rules: Record<string, unknown>;
}

export interface ReviewComment {
  id: number;
  file_path: string;
  line_number: number;
  side: CommentSide;
  agent_name: string;
  severity: CommentSeverity;
  title: string;
  comment: string;
  suggestion: string | null;
}

export interface PullRequestReview {
  id: number;
  repository_id: number;
  pr_number: number;
  head_sha: string;
  base_sha: string;
  title: string;
  author: string;
  state: ReviewState;
  summary: string | null;
  risk_score: number;
  recommendation: ReviewRecommendation;
  security_issues_count: number;
  perf_issues_count: number;
  quality_issues_count: number;
  comments: ReviewComment[];
  created_at: string;
  updated_at: string;
}

export interface ReviewMetricsSummary {
  total_reviews: number;
  avg_risk_score: number;
  total_security_issues: number;
  total_perf_issues: number;
  total_quality_issues: number;
  total_issues: number;
}
