import React, { useState } from "react";
import { Repository } from "@/types";
import { Card, Button } from "@/components/ui";
import { IndexingBadge } from "@/components/repos/IndexingBadge";
import { formatDate } from "@/utils";
import { GitBranch, Lock, Globe, RefreshCw, Settings2, ExternalLink, Trash2 } from "lucide-react";

interface RepoCardProps {
  repo: Repository;
  onIndex: (id: number) => Promise<void>;
  onEditRules: (repo: Repository) => void;
  onDelete?: (id: number) => Promise<void>;
}

export const RepoCard = ({ repo, onIndex, onEditRules, onDelete }: RepoCardProps) => {
  const [isIndexing, setIsIndexing] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  const handleIndexClick = async () => {
    setIsIndexing(true);
    try {
      await onIndex(repo.id);
    } finally {
      setIsIndexing(false);
    }
  };

  const handleDeleteClick = async () => {
    if (!onDelete) return;
    if (confirm(`Are you sure you want to disconnect ${repo.full_name}?`)) {
      setIsDeleting(true);
      try {
        await onDelete(repo.id);
      } finally {
        setIsDeleting(false);
      }
    }
  };

  return (
    <Card className="flex flex-col justify-between hover:border-zinc-700 transition-all">
      <div>
        <div className="flex items-start justify-between gap-4 mb-3">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2 mb-1">
              {repo.is_private ? (
                <Lock className="w-4 h-4 text-zinc-400 shrink-0" />
              ) : (
                <Globe className="w-4 h-4 text-zinc-400 shrink-0" />
              )}
              <h3 className="font-semibold text-base text-zinc-100 truncate hover:text-blue-400 cursor-pointer">
                {repo.full_name}
              </h3>
            </div>
            <div className="flex items-center gap-3 text-xs text-zinc-400">
              <span className="flex items-center gap-1">
                <GitBranch className="w-3 h-3" /> {repo.default_branch}
              </span>
              <span>•</span>
              <span>Last indexed: {formatDate(repo.last_indexed_at)}</span>
            </div>
          </div>
          <IndexingBadge status={repo.indexing_status} />
        </div>

        {/* Custom rules preview */}
        <div className="my-3 p-2.5 rounded bg-zinc-900/50 border border-zinc-800/80 text-xs">
          <div className="text-zinc-400 font-medium mb-1">Active Rules:</div>
          {Object.keys(repo.rules || {}).length > 0 ? (
            <div className="flex flex-wrap gap-1.5">
              {Object.keys(repo.rules).map((ruleKey) => (
                <span key={ruleKey} className="px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-300 font-mono text-[11px]">
                  {ruleKey}
                </span>
              ))}
            </div>
          ) : (
            <span className="text-zinc-500 italic">No custom rules configured</span>
          )}
        </div>
      </div>

      <div className="flex items-center justify-between pt-3 border-t border-zinc-800/60 mt-2">
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => onEditRules(repo)}
          >
            <Settings2 className="w-3.5 h-3.5" />
            Rules
          </Button>
          {onDelete && (
            <button
              onClick={handleDeleteClick}
              disabled={isDeleting}
              title="Disconnect repository"
              className="p-1.5 text-zinc-500 hover:text-red-400 rounded hover:bg-zinc-800/50 transition-colors"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          )}
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="secondary"
            size="sm"
            onClick={handleIndexClick}
            disabled={isIndexing || repo.indexing_status === "INDEXING"}
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isIndexing ? "animate-spin" : ""}`} />
            Index Repo
          </Button>
          <a
            href={`https://github.com/${repo.full_name}`}
            target="_blank"
            rel="noopener noreferrer"
            className="p-1.5 text-zinc-400 hover:text-zinc-200 transition-colors"
          >
            <ExternalLink className="w-4 h-4" />
          </a>
        </div>
      </div>
    </Card>
  );
};
