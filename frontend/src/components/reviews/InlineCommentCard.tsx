import React from "react";
import { ReviewComment } from "@/types";
import { Badge, Card } from "@/components/ui";
import { getSeverityStyle } from "@/utils";
import { Shield, Zap, Code2, Sparkles, FileCode } from "lucide-react";

interface InlineCommentCardProps {
  comment: ReviewComment;
}

export const InlineCommentCard = ({ comment }: InlineCommentCardProps) => {
  const sevStyle = getSeverityStyle(comment.severity);

  const getAgentIcon = (agent: string) => {
    switch (agent) {
      case "security":
        return <Shield className="w-3.5 h-3.5 text-red-400" />;
      case "performance":
        return <Zap className="w-3.5 h-3.5 text-amber-400" />;
      case "quality":
      default:
        return <Code2 className="w-3.5 h-3.5 text-purple-400" />;
    }
  };

  return (
    <Card className={`border-l-4 ${sevStyle.border} ${sevStyle.bg} mb-3`}>
      <div className="flex items-start justify-between gap-3 mb-2">
        <div className="flex items-center gap-2 flex-wrap">
          <Badge className={sevStyle.badge}>{comment.severity}</Badge>
          <div className="flex items-center gap-1.5 text-xs text-zinc-400 capitalize">
            {getAgentIcon(comment.agent_name)}
            <span>{comment.agent_name} Agent</span>
          </div>
          <span className="text-zinc-600">•</span>
          <div className="flex items-center gap-1 font-mono text-xs text-blue-400">
            <FileCode className="w-3.5 h-3.5" />
            <span>{comment.file_path}:{comment.line_number}</span>
          </div>
        </div>
      </div>

      <h4 className="font-semibold text-sm text-zinc-100 mb-1">{comment.title}</h4>
      <p className="text-xs text-zinc-300 leading-relaxed whitespace-pre-wrap">{comment.comment}</p>

      {comment.suggestion && (
        <div className="mt-3 rounded border border-zinc-800 bg-zinc-950 p-3">
          <div className="flex items-center gap-1 text-[11px] font-semibold text-emerald-400 mb-1.5">
            <Sparkles className="w-3.5 h-3.5" />
            <span>Suggested Fix</span>
          </div>
          <pre className="font-mono text-xs text-zinc-200 overflow-x-auto p-1 bg-zinc-900/60 rounded">
            <code>{comment.suggestion}</code>
          </pre>
        </div>
      )}
    </Card>
  );
};
