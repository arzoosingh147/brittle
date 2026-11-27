"use client";

import React, { useState } from "react";
import { Card, Button } from "@/components/ui";
import { X, Sparkles, FolderGit2, AlertCircle, Loader2, Globe, Lock } from "lucide-react";
import { Repository } from "@/types";

interface AddRepoModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (repo: Repository) => void;
  onConnect: (data: {
    name: string;
    owner?: string;
    default_branch?: string;
    is_private?: boolean;
    rules?: Record<string, unknown>;
    auto_index?: boolean;
  }) => Promise<Repository>;
}

const PRESET_RULES: Record<string, Record<string, unknown>> = {
  strict: {
    max_function_lines: 50,
    forbidden_libraries: ["pickle", "eval", "os.system"],
    require_typed_returns: true,
    security_audit: "high",
    enforce_jwt_rotation: true,
  },
  standard: {
    max_function_lines: 80,
    forbidden_libraries: ["pickle"],
    require_typed_returns: true,
    security_audit: "standard",
  },
  minimal: {
    security_audit: "basic",
    detect_secrets: true,
  },
};

export const AddRepoModal = ({
  isOpen,
  onClose,
  onSuccess,
  onConnect,
}: AddRepoModalProps) => {
  const [repoInput, setRepoInput] = useState("");
  const [defaultBranch, setDefaultBranch] = useState("main");
  const [isPrivate, setIsPrivate] = useState(false);
  const [selectedPreset, setSelectedPreset] = useState<"strict" | "standard" | "minimal">("strict");
  const [autoIndex, setAutoIndex] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleFillDemo = (name: string) => {
    setRepoInput(name);
    setError(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!repoInput.trim()) {
      setError("Please provide a repository name or URL");
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      const created = await onConnect({
        name: repoInput.trim(),
        default_branch: defaultBranch.trim() || "main",
        is_private: isPrivate,
        rules: PRESET_RULES[selectedPreset],
        auto_index: autoIndex,
      });
      onSuccess(created);
      onClose();
    } catch (err: any) {
      setError(err?.message || "Failed to connect repository");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-in fade-in duration-150">
      <Card className="w-full max-w-lg p-0 overflow-hidden bg-zinc-900 border-zinc-700 shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-zinc-800 bg-zinc-950/60">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-blue-600/10 text-blue-400 border border-blue-500/20">
              <FolderGit2 className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-semibold text-zinc-100">Connect GitHub Repository</h2>
              <p className="text-xs text-zinc-400">Register repository for multi-agent PR reviews and vector search.</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-zinc-400 hover:text-zinc-100 p-1 rounded-md transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {/* Quick-fill Demo suggestions */}
          <div className="p-3 rounded-lg bg-zinc-950 border border-zinc-800/80 text-xs flex flex-col gap-2">
            <span className="text-zinc-400 font-medium flex items-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5 text-blue-400" /> Quick-fill existing repo:
            </span>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() => handleFillDemo("arzoosingh147/projectecofy")}
                className="px-2.5 py-1 rounded bg-zinc-800 hover:bg-zinc-700 text-zinc-200 text-xs font-mono transition-colors"
              >
                arzoosingh147/projectecofy
              </button>
              <button
                type="button"
                onClick={() => handleFillDemo("acme-engineering/brittle-core")}
                className="px-2.5 py-1 rounded bg-zinc-800 hover:bg-zinc-700 text-zinc-200 text-xs font-mono transition-colors"
              >
                acme-engineering/brittle-core
              </button>
            </div>
          </div>

          {/* Repository Slug or URL */}
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-zinc-200">
              Repository URL or Slug <span className="text-red-400">*</span>
            </label>
            <input
              type="text"
              value={repoInput}
              onChange={(e) => setRepoInput(e.target.value)}
              placeholder="e.g. arzoosingh147/projectecofy or https://github.com/..."
              className="w-full px-3 py-2 text-sm rounded-md bg-zinc-950 border border-zinc-800 text-zinc-100 placeholder-zinc-500 focus:outline-none focus:ring-1 focus:ring-blue-500 font-mono"
              required
            />
          </div>

          {/* Default Branch & Visibility */}
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-zinc-200">Default Branch</label>
              <input
                type="text"
                value={defaultBranch}
                onChange={(e) => setDefaultBranch(e.target.value)}
                placeholder="main"
                className="w-full px-3 py-2 text-sm rounded-md bg-zinc-950 border border-zinc-800 text-zinc-100 placeholder-zinc-500 focus:outline-none focus:ring-1 focus:ring-blue-500 font-mono"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-medium text-zinc-200">Visibility</label>
              <button
                type="button"
                onClick={() => setIsPrivate(!isPrivate)}
                className={`w-full flex items-center justify-center gap-2 px-3 py-2 text-sm rounded-md border transition-colors ${
                  isPrivate
                    ? "bg-amber-500/10 border-amber-500/30 text-amber-300"
                    : "bg-zinc-950 border-zinc-800 text-zinc-300"
                }`}
              >
                {isPrivate ? <Lock className="w-3.5 h-3.5" /> : <Globe className="w-3.5 h-3.5" />}
                {isPrivate ? "Private Repo" : "Public Repo"}
              </button>
            </div>
          </div>

          {/* AI Review Rules Preset */}
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-zinc-200">Review Rules Preset</label>
            <div className="grid grid-cols-3 gap-2 text-xs">
              {(["strict", "standard", "minimal"] as const).map((preset) => (
                <button
                  key={preset}
                  type="button"
                  onClick={() => setSelectedPreset(preset)}
                  className={`p-2.5 rounded-md border text-left transition-all ${
                    selectedPreset === preset
                      ? "bg-blue-600/15 border-blue-500 text-blue-300"
                      : "bg-zinc-950 border-zinc-800 text-zinc-400 hover:border-zinc-700"
                  }`}
                >
                  <div className="font-semibold capitalize text-zinc-200">{preset}</div>
                  <div className="text-[10px] text-zinc-400 mt-0.5">
                    {preset === "strict" ? "High Security & Perf" : preset === "standard" ? "Clean Architecture" : "Basic Checks"}
                  </div>
                </button>
              ))}
            </div>
          </div>

          {/* Auto Index Checkbox */}
          <label className="flex items-center gap-2.5 pt-1 text-xs text-zinc-300 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={autoIndex}
              onChange={(e) => setAutoIndex(e.target.checked)}
              className="rounded bg-zinc-950 border-zinc-700 text-blue-600 focus:ring-0"
            />
            <span>Trigger vector store AST indexing immediately after connecting</span>
          </label>

          {/* Error Message */}
          {error && (
            <div className="p-3 rounded bg-red-500/10 border border-red-500/20 text-red-400 text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* Actions */}
          <div className="flex items-center justify-end gap-3 pt-4 border-t border-zinc-800">
            <Button variant="ghost" size="sm" type="button" onClick={onClose} disabled={isSubmitting}>
              Cancel
            </Button>
            <Button variant="primary" size="sm" type="submit" disabled={isSubmitting}>
              {isSubmitting ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  Connecting...
                </>
              ) : (
                "Connect Repository"
              )}
            </Button>
          </div>
        </form>
      </Card>
    </div>
  );
};
