import { CommentSeverity, ReviewRecommendation } from "@/types";

export function formatDate(dateString: string | null | undefined): string {
  if (!dateString) return "Never";
  try {
    const d = new Date(dateString);
    return d.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return dateString;
  }
}

export function getSeverityStyle(severity: CommentSeverity): { badge: string; border: string; bg: string } {
  switch (severity) {
    case "CRITICAL":
      return {
        badge: "bg-red-500/10 text-red-400 border-red-500/20",
        border: "border-red-500/30",
        bg: "bg-red-950/20",
      };
    case "HIGH":
      return {
        badge: "bg-amber-500/10 text-amber-400 border-amber-500/20",
        border: "border-amber-500/30",
        bg: "bg-amber-950/20",
      };
    case "MEDIUM":
      return {
        badge: "bg-blue-500/10 text-blue-400 border-blue-500/20",
        border: "border-blue-500/30",
        bg: "bg-blue-950/20",
      };
    case "LOW":
      return {
        badge: "bg-zinc-500/10 text-zinc-400 border-zinc-500/20",
        border: "border-zinc-500/30",
        bg: "bg-zinc-950/20",
      };
    case "INFO":
    default:
      return {
        badge: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
        border: "border-emerald-500/30",
        bg: "bg-emerald-950/20",
      };
  }
}

export function getRiskScoreColor(score: number): string {
  if (score >= 7) return "text-red-400 bg-red-500/10 border-red-500/20";
  if (score >= 4) return "text-amber-400 bg-amber-500/10 border-amber-500/20";
  return "text-emerald-400 bg-emerald-500/10 border-emerald-500/20";
}

export function getRecommendationBadge(rec: ReviewRecommendation): { text: string; style: string } {
  switch (rec) {
    case "APPROVE":
      return { text: "Approved", style: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20" };
    case "REQUEST_CHANGES":
      return { text: "Changes Requested", style: "bg-red-500/10 text-red-400 border-red-500/20" };
    case "COMMENT":
    default:
      return { text: "Commented", style: "bg-blue-500/10 text-blue-400 border-blue-500/20" };
  }
}
