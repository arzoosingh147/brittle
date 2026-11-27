import React from "react";
import { ReviewMetricsSummary } from "@/types";
import { Card } from "@/components/ui";
import { ShieldAlert, Zap, CheckCircle, BarChart3, AlertTriangle } from "lucide-react";
import { getRiskScoreColor } from "@/utils";

interface MetricsGridProps {
  metrics: ReviewMetricsSummary;
}

export const MetricsGrid = ({ metrics }: MetricsGridProps) => {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
      <Card className="flex items-center gap-4">
        <div className="p-3 rounded-lg bg-blue-500/10 text-blue-400">
          <BarChart3 className="w-5 h-5" />
        </div>
        <div>
          <div className="text-2xl font-bold text-zinc-100">{metrics.total_reviews}</div>
          <div className="text-xs text-zinc-400">Total PRs Reviewed</div>
        </div>
      </Card>

      <Card className="flex items-center gap-4">
        <div className={`p-3 rounded-lg ${getRiskScoreColor(metrics.avg_risk_score)}`}>
          <AlertTriangle className="w-5 h-5" />
        </div>
        <div>
          <div className="text-2xl font-bold text-zinc-100">{metrics.avg_risk_score} <span className="text-sm font-normal text-zinc-500">/ 10</span></div>
          <div className="text-xs text-zinc-400">Avg Risk Score</div>
        </div>
      </Card>

      <Card className="flex items-center gap-4">
        <div className="p-3 rounded-lg bg-red-500/10 text-red-400">
          <ShieldAlert className="w-5 h-5" />
        </div>
        <div>
          <div className="text-2xl font-bold text-zinc-100">{metrics.total_security_issues}</div>
          <div className="text-xs text-zinc-400">Security Concerns</div>
        </div>
      </Card>

      <Card className="flex items-center gap-4">
        <div className="p-3 rounded-lg bg-amber-500/10 text-amber-400">
          <Zap className="w-5 h-5" />
        </div>
        <div>
          <div className="text-2xl font-bold text-zinc-100">{metrics.total_perf_issues}</div>
          <div className="text-xs text-zinc-400">Perf Bottlenecks</div>
        </div>
      </Card>

      <Card className="flex items-center gap-4">
        <div className="p-3 rounded-lg bg-purple-500/10 text-purple-400">
          <CheckCircle className="w-5 h-5" />
        </div>
        <div>
          <div className="text-2xl font-bold text-zinc-100">{metrics.total_quality_issues}</div>
          <div className="text-xs text-zinc-400">Quality & Rule Fixes</div>
        </div>
      </Card>
    </div>
  );
};
