import React from "react";
import { IndexingStatus } from "@/types";
import { Badge } from "@/components/ui";
import { Loader2, CheckCircle2, Clock, AlertCircle } from "lucide-react";

interface IndexingBadgeProps {
  status: IndexingStatus;
}

export const IndexingBadge = ({ status }: IndexingBadgeProps) => {
  switch (status) {
    case "INDEXING":
      return (
        <Badge className="bg-amber-500/10 text-amber-400 border-amber-500/20 gap-1.5">
          <Loader2 className="w-3 h-3 animate-spin" />
          Indexing Codebase...
        </Badge>
      );
    case "COMPLETED":
      return (
        <Badge className="bg-emerald-500/10 text-emerald-400 border-emerald-500/20 gap-1.5">
          <CheckCircle2 className="w-3 h-3" />
          Indexed
        </Badge>
      );
    case "FAILED":
      return (
        <Badge className="bg-red-500/10 text-red-400 border-red-500/20 gap-1.5">
          <AlertCircle className="w-3 h-3" />
          Indexing Failed
        </Badge>
      );
    case "PENDING":
    default:
      return (
        <Badge className="bg-zinc-800 text-zinc-400 border-zinc-700 gap-1.5">
          <Clock className="w-3 h-3" />
          Not Indexed
        </Badge>
      );
  }
};
