"use client";

import React, { useEffect, useState } from "react";
import { Repository } from "@/types";
import { apiClient } from "@/lib/api-client";
import { RepoCard } from "@/components/repos/RepoCard";
import { RepoRulesForm } from "@/components/repos/RepoRulesForm";
import { AddRepoModal } from "@/components/repos/AddRepoModal";
import { Button } from "@/components/ui";
import { Plus, RefreshCw, FolderGit2, Sparkles } from "lucide-react";

export default function RepositoriesPage() {
  const [repos, setRepos] = useState<Repository[]>([]);
  const [selectedRepoForRules, setSelectedRepoForRules] = useState<Repository | null>(null);
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  const fetchRepos = async () => {
    setIsLoading(true);
    try {
      const data = await apiClient.getRepositories().catch(() => []);
      setRepos(data);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchRepos();
  }, []);

  const handleConnectRepo = async (data: Parameters<typeof apiClient.createRepository>[0]) => {
    const created = await apiClient.createRepository(data);
    setRepos((prev) => [created, ...prev.filter((r) => r.id !== created.id)]);
    return created;
  };

  const handleDeleteRepo = async (id: number) => {
    await apiClient.deleteRepository(id);
    setRepos((prev) => prev.filter((r) => r.id !== id));
  };

  const handleTriggerIndex = async (repoId: number) => {
    await apiClient.triggerIndexing(repoId);
    setRepos((prev) =>
      prev.map((r) => (r.id === repoId ? { ...r, indexing_status: "INDEXING" } : r))
    );
  };

  const handleSaveRules = async (rules: Record<string, unknown>) => {
    if (!selectedRepoForRules) return;
    const updated = await apiClient.updateRules(selectedRepoForRules.id, rules);
    setRepos((prev) =>
      prev.map((r) => (r.id === updated.id ? { ...r, rules: updated.rules } : r))
    );
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-zinc-100">Connected Repositories</h1>
          <p className="text-sm text-zinc-400 mt-1">
            Manage vector-indexed repositories, trigger codebase re-indexing, and configure custom rules.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="secondary" size="sm" onClick={fetchRepos} disabled={isLoading}>
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? "animate-spin" : ""}`} />
            Refresh
          </Button>
          <Button variant="primary" size="sm" onClick={() => setIsAddModalOpen(true)}>
            <Plus className="w-3.5 h-3.5" />
            Connect GitHub Repository
          </Button>
        </div>
      </div>

      {repos.length === 0 ? (
        <div className="rounded-lg border border-dashed border-zinc-800 p-12 text-center bg-zinc-950/40">
          <FolderGit2 className="w-10 h-10 text-zinc-500 mx-auto mb-3" />
          <h3 className="text-base font-medium text-zinc-200">No repositories connected yet</h3>
          <p className="text-xs text-zinc-400 mt-1 max-w-md mx-auto mb-5">
            Connect your GitHub repositories to enable AST code chunking, vector embeddings, and multi-agent AI reviews.
          </p>
          <div className="flex flex-wrap items-center justify-center gap-3">
            <Button variant="primary" size="sm" onClick={() => setIsAddModalOpen(true)}>
              <Plus className="w-3.5 h-3.5" />
              Connect Repository
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                handleConnectRepo({
                  name: "projectecofy",
                  owner: "arzoosingh147",
                  default_branch: "main",
                  is_private: false,
                  rules: {
                    max_function_lines: 50,
                    forbidden_libraries: ["pickle", "eval"],
                    require_typed_returns: true,
                  },
                });
              }}
            >
              <Sparkles className="w-3.5 h-3.5 text-blue-400 mr-1" />
              Quick-Connect arzoosingh147/projectecofy
            </Button>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {repos.map((repo) => (
            <RepoCard
              key={repo.id}
              repo={repo}
              onIndex={handleTriggerIndex}
              onEditRules={setSelectedRepoForRules}
              onDelete={handleDeleteRepo}
            />
          ))}
        </div>
      )}

      {selectedRepoForRules && (
        <RepoRulesForm
          repo={selectedRepoForRules}
          onSave={handleSaveRules}
          onClose={() => setSelectedRepoForRules(null)}
        />
      )}

      <AddRepoModal
        isOpen={isAddModalOpen}
        onClose={() => setIsAddModalOpen(false)}
        onSuccess={() => {}}
        onConnect={handleConnectRepo}
      />
    </div>
  );
}
