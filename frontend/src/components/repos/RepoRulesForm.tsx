"use client";

import React, { useState } from "react";
import { Repository } from "@/types";
import { Card, Button } from "@/components/ui";
import {
  X,
  Save,
  AlertCircle,
  Sparkles,
  ShieldAlert,
  Zap,
  Code2,
  Sliders,
  Check,
  FileCode,
  RotateCcw,
} from "lucide-react";

interface RepoRulesFormProps {
  repo: Repository;
  onSave: (rules: Record<string, unknown>) => Promise<void>;
  onClose: () => void;
}

interface PrewrittenRule {
  id: string;
  name: string;
  description: string;
  category: "security" | "perf" | "quality";
  key: string;
  defaultVal: unknown;
}

const PREWRITTEN_CATALOG: PrewrittenRule[] = [
  // Security
  {
    id: "sec_forbidden_imports",
    name: "Block Insecure Deserialization & Exec",
    description: "Flag usage of pickle, eval, exec, and raw os.system calls.",
    category: "security",
    key: "forbidden_libraries",
    defaultVal: ["pickle", "eval", "exec", "os.system"],
  },
  {
    id: "sec_detect_secrets",
    name: "Scan for Hardcoded Secrets & API Keys",
    description: "Strictly flag bearer tokens, private keys, and passwords in diffs.",
    category: "security",
    key: "detect_hardcoded_secrets",
    defaultVal: true,
  },
  {
    id: "sec_sql_injection",
    name: "Enforce Parameterized SQL Queries",
    description: "Forbid raw f-string and string interpolation inside SQL queries.",
    category: "security",
    key: "prevent_sql_injection",
    defaultVal: true,
  },

  // Performance
  {
    id: "perf_blocking_async",
    name: "Forbid Synchronous I/O in Async Routes",
    description: "Detect time.sleep(), sync Redis, and blocking requests in async event loops.",
    category: "perf",
    key: "forbid_blocking_sync_calls",
    defaultVal: true,
  },
  {
    id: "perf_n_plus_one",
    name: "Detect N+1 Database Queries",
    description: "Enforce joinedload / selectinload for ORM relation traversal in loops.",
    category: "perf",
    key: "detect_n_plus_one",
    defaultVal: true,
  },

  // Quality & Architecture
  {
    id: "qual_typed_returns",
    name: "Require Static Type Return Annotations",
    description: "All public functions and service methods must specify explicit return types.",
    category: "quality",
    key: "require_typed_returns",
    defaultVal: true,
  },
  {
    id: "qual_clean_architecture",
    name: "Enforce Layered Clean Architecture",
    description: "No direct database or SQL queries allowed inside API routers/controllers.",
    category: "quality",
    key: "enforce_layered_architecture",
    defaultVal: true,
  },
  {
    id: "qual_no_any",
    name: "Disallow Unchecked 'any' Types",
    description: "Flag loose 'any' annotations in TypeScript and untyped Dict[Any, Any] in Python.",
    category: "quality",
    key: "forbid_raw_any_types",
    defaultVal: true,
  },
];

const PRESET_BUNDLES: Record<string, { label: string; rules: Record<string, unknown> }> = {
  strict: {
    label: "Strict Production (High Security & Perf)",
    rules: {
      max_function_lines: 50,
      forbidden_libraries: ["pickle", "eval", "exec", "os.system"],
      detect_hardcoded_secrets: true,
      prevent_sql_injection: true,
      forbid_blocking_sync_calls: true,
      detect_n_plus_one: true,
      require_typed_returns: true,
      enforce_layered_architecture: true,
      forbid_raw_any_types: true,
      security_audit_level: "high",
    },
  },
  clean_arch: {
    label: "Clean Architecture & Typing",
    rules: {
      max_function_lines: 60,
      require_typed_returns: true,
      enforce_layered_architecture: true,
      forbid_raw_any_types: true,
      detect_hardcoded_secrets: true,
      prevent_sql_injection: true,
    },
  },
  pragmatic: {
    label: "Pragmatic (Core Safeguards Only)",
    rules: {
      max_function_lines: 100,
      detect_hardcoded_secrets: true,
      prevent_sql_injection: true,
      security_audit_level: "standard",
    },
  },
};

export const RepoRulesForm = ({ repo, onSave, onClose }: RepoRulesFormProps) => {
  const [activeTab, setActiveTab] = useState<"builder" | "json">("builder");
  const [rulesState, setRulesState] = useState<Record<string, unknown>>(() => {
    return repo.rules && Object.keys(repo.rules).length > 0
      ? { ...repo.rules }
      : { ...PRESET_BUNDLES.strict.rules };
  });

  const [rulesText, setRulesText] = useState(() => JSON.stringify(rulesState, null, 2));
  const [customInstructions, setCustomInstructions] = useState<string>(() => {
    return (rulesState["custom_guidelines"] as string) || "";
  });
  const [maxFunctionLines, setMaxFunctionLines] = useState<number>(() => {
    return (rulesState["max_function_lines"] as number) || 50;
  });

  const [error, setError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  // Sync state into JSON text
  const updateRulesAndSync = (newRules: Record<string, unknown>) => {
    setRulesState(newRules);
    setRulesText(JSON.stringify(newRules, null, 2));
  };

  const handleApplyPreset = (presetKey: string) => {
    const bundle = PRESET_BUNDLES[presetKey];
    if (bundle) {
      const merged = {
        ...bundle.rules,
        ...(customInstructions.trim() ? { custom_guidelines: customInstructions.trim() } : {}),
      };
      setMaxFunctionLines((merged["max_function_lines"] as number) || 50);
      updateRulesAndSync(merged);
      setError(null);
    }
  };

  const handleTogglePrewritten = (rule: PrewrittenRule) => {
    const next = { ...rulesState };
    if (rule.key in next) {
      delete next[rule.key];
    } else {
      next[rule.key] = rule.defaultVal;
    }
    updateRulesAndSync(next);
  };

  const handleMaxLinesChange = (lines: number) => {
    setMaxFunctionLines(lines);
    const next = { ...rulesState, max_function_lines: lines };
    updateRulesAndSync(next);
  };

  const handleCustomInstructionsChange = (text: string) => {
    setCustomInstructions(text);
    const next = { ...rulesState };
    if (text.trim()) {
      next["custom_guidelines"] = text.trim();
    } else {
      delete next["custom_guidelines"];
    }
    updateRulesAndSync(next);
  };

  const handleJsonTextChange = (text: string) => {
    setRulesText(text);
    try {
      const parsed = JSON.parse(text);
      setRulesState(parsed);
      setError(null);
      if (parsed["custom_guidelines"]) {
        setCustomInstructions(parsed["custom_guidelines"]);
      }
      if (parsed["max_function_lines"]) {
        setMaxFunctionLines(parsed["max_function_lines"]);
      }
    } catch {
      // Allow live typing without throwing immediate error
    }
  };

  const handleSave = async () => {
    setError(null);
    try {
      let finalRules = rulesState;
      if (activeTab === "json") {
        finalRules = JSON.parse(rulesText);
      }
      setIsSaving(true);
      await onSave(finalRules);
      onClose();
    } catch (e) {
      setError((e as Error).message || "Invalid JSON syntax");
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4 animate-in fade-in duration-150">
      <Card className="w-full max-w-2xl bg-zinc-900 border-zinc-700 shadow-2xl p-0 overflow-hidden flex flex-col max-h-[90vh]">
        {/* Modal Header */}
        <div className="flex items-center justify-between p-5 border-b border-zinc-800 bg-zinc-950/80">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-blue-600/10 text-blue-400 border border-blue-500/20">
              <Sliders className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-semibold text-zinc-100">Review Rules & AI Guidelines</h2>
              <p className="text-xs text-zinc-400">
                Configure review standards and custom instructions for <span className="font-mono text-zinc-200">{repo.full_name}</span>
              </p>
            </div>
          </div>
          <button onClick={onClose} className="text-zinc-400 hover:text-zinc-100 p-1 rounded-md transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Tab Selector */}
        <div className="flex items-center gap-2 px-6 pt-4 border-b border-zinc-800/80 bg-zinc-950/40 text-xs">
          <button
            type="button"
            onClick={() => setActiveTab("builder")}
            className={`flex items-center gap-1.5 pb-2.5 font-medium border-b-2 transition-colors ${
              activeTab === "builder"
                ? "border-blue-500 text-blue-400"
                : "border-transparent text-zinc-400 hover:text-zinc-200"
            }`}
          >
            <Sliders className="w-3.5 h-3.5" />
            Visual Rule Selector & Presets
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("json")}
            className={`flex items-center gap-1.5 pb-2.5 font-medium border-b-2 transition-colors ${
              activeTab === "json"
                ? "border-blue-500 text-blue-400"
                : "border-transparent text-zinc-400 hover:text-zinc-200"
            }`}
          >
            <FileCode className="w-3.5 h-3.5" />
            Raw JSON Schema Editor
          </button>
        </div>

        {/* Modal Scrollable Body */}
        <div className="p-6 overflow-y-auto space-y-5 flex-1">
          {activeTab === "builder" ? (
            <>
              {/* Preset Profile Cards */}
              <div className="space-y-2">
                <div className="text-xs font-semibold text-zinc-300 flex items-center gap-1.5">
                  <Sparkles className="w-3.5 h-3.5 text-blue-400" /> Pre-written Preset Profiles:
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
                  {Object.entries(PRESET_BUNDLES).map(([key, bundle]) => (
                    <button
                      key={key}
                      type="button"
                      onClick={() => handleApplyPreset(key)}
                      className="p-3 rounded-lg border border-zinc-800 bg-zinc-950/60 hover:bg-zinc-800/60 hover:border-blue-500/50 text-left transition-all group"
                    >
                      <div className="text-xs font-semibold text-zinc-200 group-hover:text-blue-300">
                        {key === "strict" ? "🛡️ Strict Production" : key === "clean_arch" ? "📐 Clean Arch" : "🚀 Pragmatic Fast"}
                      </div>
                      <div className="text-[11px] text-zinc-400 mt-1 line-clamp-2">
                        {bundle.label}
                      </div>
                    </button>
                  ))}
                </div>
              </div>

              {/* Pre-written Rule Toggles */}
              <div className="space-y-2.5">
                <div className="text-xs font-semibold text-zinc-300">
                  Pre-written Rule Catalog (Toggle to Add / Remove):
                </div>
                <div className="grid grid-cols-1 gap-2">
                  {PREWRITTEN_CATALOG.map((rule) => {
                    const isEnabled = rule.key in rulesState;
                    return (
                      <div
                        key={rule.id}
                        onClick={() => handleTogglePrewritten(rule)}
                        className={`p-3 rounded-lg border cursor-pointer select-none transition-all flex items-start justify-between gap-3 ${
                          isEnabled
                            ? "bg-blue-600/10 border-blue-500/40 text-zinc-100"
                            : "bg-zinc-950/50 border-zinc-800/80 text-zinc-400 hover:border-zinc-700"
                        }`}
                      >
                        <div className="space-y-0.5">
                          <div className="flex items-center gap-2">
                            {rule.category === "security" && <ShieldAlert className="w-3.5 h-3.5 text-red-400" />}
                            {rule.category === "perf" && <Zap className="w-3.5 h-3.5 text-amber-400" />}
                            {rule.category === "quality" && <Code2 className="w-3.5 h-3.5 text-emerald-400" />}
                            <span className="text-xs font-semibold text-zinc-200">{rule.name}</span>
                          </div>
                          <p className="text-[11px] text-zinc-400">{rule.description}</p>
                        </div>
                        <div
                          className={`w-5 h-5 rounded flex items-center justify-center shrink-0 border transition-colors ${
                            isEnabled
                              ? "bg-blue-600 border-blue-500 text-white"
                              : "border-zinc-700 bg-zinc-900"
                          }`}
                        >
                          {isEnabled && <Check className="w-3 h-3" />}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Max Function Lines Config */}
              <div className="p-3.5 rounded-lg bg-zinc-950/60 border border-zinc-800 flex items-center justify-between gap-4">
                <div>
                  <div className="text-xs font-medium text-zinc-200">Max Function Length (Lines)</div>
                  <div className="text-[11px] text-zinc-400">Flag functions that exceed this line count for refactoring.</div>
                </div>
                <div className="flex items-center gap-2">
                  {[30, 50, 80, 100].map((lines) => (
                    <button
                      key={lines}
                      type="button"
                      onClick={() => handleMaxLinesChange(lines)}
                      className={`px-2.5 py-1 rounded text-xs font-mono transition-colors ${
                        maxFunctionLines === lines
                          ? "bg-blue-600 text-white font-bold"
                          : "bg-zinc-800 text-zinc-300 hover:bg-zinc-700"
                      }`}
                    >
                      {lines}
                    </button>
                  ))}
                </div>
              </div>

              {/* Natural Language / Custom Prompt Guidelines */}
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-zinc-200 flex items-center justify-between">
                  <span>Custom Written AI Instructions & Guidelines</span>
                  <span className="text-[11px] text-zinc-500 font-normal">Plain English prompt instructions</span>
                </label>
                <textarea
                  rows={3}
                  value={customInstructions}
                  onChange={(e) => handleCustomInstructionsChange(e.target.value)}
                  placeholder="e.g. 'Prefer Zod schemas for validation. All database models must inherit from TimestampMixin. Write helpful, friendly review feedback.'"
                  className="w-full text-xs rounded-md bg-zinc-950 border border-zinc-800 text-zinc-200 placeholder-zinc-500 p-3 focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
              </div>
            </>
          ) : (
            /* JSON Tab */
            <div className="space-y-2">
              <div className="flex items-center justify-between text-xs">
                <span className="text-zinc-400">Raw JSON rules structure:</span>
                <button
                  type="button"
                  onClick={() => handleApplyPreset("strict")}
                  className="text-blue-400 hover:text-blue-300 flex items-center gap-1 text-[11px]"
                >
                  <RotateCcw className="w-3 h-3" /> Reset to Strict Profile
                </button>
              </div>
              <textarea
                rows={14}
                className="w-full font-mono text-xs bg-zinc-950 border border-zinc-800 rounded p-3 text-zinc-200 focus:outline-none focus:border-blue-500 leading-relaxed"
                value={rulesText}
                onChange={(e) => handleJsonTextChange(e.target.value)}
              />
            </div>
          )}

          {error && (
            <div className="flex items-center gap-2 p-3 rounded bg-red-500/10 border border-red-500/20 text-xs text-red-400">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}
        </div>

        {/* Modal Footer Actions */}
        <div className="flex items-center justify-between p-4 border-t border-zinc-800 bg-zinc-950/80">
          <div className="text-xs text-zinc-500">
            {Object.keys(rulesState).length} active rule{Object.keys(rulesState).length === 1 ? "" : "s"}
          </div>
          <div className="flex items-center gap-2.5">
            <Button variant="ghost" size="sm" onClick={onClose} disabled={isSaving}>
              Cancel
            </Button>
            <Button variant="primary" size="sm" onClick={handleSave} disabled={isSaving}>
              <Save className="w-3.5 h-3.5" />
              {isSaving ? "Saving Rules..." : "Save Rules"}
            </Button>
          </div>
        </div>
      </Card>
    </div>
  );
};
