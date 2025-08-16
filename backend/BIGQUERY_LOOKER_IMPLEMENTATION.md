# BigQuery and Looker Studio Implementation Guide

## Overview
This guide provides production-ready BigQuery views, Looker metrics, and React components for analyzing grounding enforcement data with full measurement integrity.

## 1. BigQuery Infrastructure

### 1.1 Metrics View
Create a denormalized view for efficient analytics:

```sql
-- contestra.metrics.runs_metrics_v1
CREATE OR REPLACE VIEW `contestra.metrics.runs_metrics_v1` AS
SELECT
  run_id,
  provider,
  model_alias,
  requested_mode,               -- "UNGROUNDED" | "PREFERRED" | "REQUIRED"
  enforcement_mode,             -- "none" | "soft" | "hard"
  enforcement_passed,           -- NEW: explicit pass/fail flag
  status,                       -- "ok" | "failed"
  tool_call_count,
  grounded_effective,
  why_not_grounded,
  error_code,
  usage_reasoning_tokens,
  usage_output_tokens,
  usage_total_tokens,
  budget_starved,
  effective_max_output_tokens,
  latency_ms,
  provoker_hash,
  answer_text,
  -- Computed helpers
  REGEXP_CONTAINS(model_alias, r'(?i)^gpt-5') AS is_gpt5,
  (requested_mode = 'REQUIRED' AND tool_call_count > 0) AS enforcement_passed_calc,
  -- Reasoning efficiency
  SAFE_DIVIDE(usage_reasoning_tokens, usage_output_tokens) AS reasoning_burn_ratio,
  -- Timestamp fields
  created_at,
  DATE(created_at) AS run_date
FROM `contestra.raw.runs`;
```

### 1.2 Daily Aggregates (Optional)
For dashboard performance at scale:

```sql
-- contestra.metrics.daily_enforcement_stats
CREATE OR REPLACE TABLE `contestra.metrics.daily_enforcement_stats` AS
SELECT
  DATE(created_at) as date,
  provider,
  model_alias,
  requested_mode,
  COUNT(*) as total_runs,
  SUM(CASE WHEN enforcement_passed THEN 1 ELSE 0 END) as enforcement_passed_count,
  AVG(CASE WHEN enforcement_passed THEN 1.0 ELSE 0.0 END) as enforcement_pass_rate,
  AVG(tool_call_count) as avg_tool_calls,
  AVG(usage_reasoning_tokens) as avg_reasoning_tokens,
  AVG(latency_ms) as avg_latency_ms,
  SUM(CASE WHEN budget_starved THEN 1 ELSE 0 END) as budget_starved_count
FROM `contestra.metrics.runs_metrics_v1`
GROUP BY 1, 2, 3, 4;
```

## 2. LookML Configuration

### 2.1 View Definition
```lkml
# views/runs_metrics_v1.view.lkml
view: runs_metrics_v1 {
  sql_table_name: `contestra.metrics.runs_metrics_v1` ;;

  # === DIMENSIONS ===
  dimension: run_id {
    primary_key: yes
    type: string
    sql: ${TABLE}.run_id ;;
  }

  dimension: provider {
    type: string
    sql: ${TABLE}.provider ;;
  }

  dimension: model_alias {
    type: string
    sql: ${TABLE}.model_alias ;;
  }

  dimension: requested_mode {
    type: string
    sql: ${TABLE}.requested_mode ;;
  }

  dimension: enforcement_mode {
    type: string
    sql: ${TABLE}.enforcement_mode ;;
  }

  dimension: status {
    type: string
    sql: ${TABLE}.status ;;
  }

  dimension: why_not_grounded {
    type: string
    sql: ${TABLE}.why_not_grounded ;;
  }

  dimension: error_code {
    type: string
    sql: ${TABLE}.error_code ;;
  }

  dimension: is_gpt5 {
    type: yesno
    sql: ${TABLE}.is_gpt5 ;;
  }

  dimension: enforcement_passed {
    type: yesno
    sql: ${TABLE}.enforcement_passed ;;
  }

  dimension: tool_call_count {
    type: number
    sql: ${TABLE}.tool_call_count ;;
  }

  dimension: grounded_effective {
    type: yesno
    sql: ${TABLE}.grounded_effective ;;
  }

  dimension: budget_starved {
    type: yesno
    sql: ${TABLE}.budget_starved ;;
  }

  dimension: latency_ms {
    type: number
    sql: ${TABLE}.latency_ms ;;
  }

  dimension: usage_reasoning_tokens {
    type: number
    sql: ${TABLE}.usage_reasoning_tokens ;;
  }

  dimension: usage_output_tokens {
    type: number
    sql: ${TABLE}.usage_output_tokens ;;
  }

  dimension: effective_max_output_tokens {
    type: number
    sql: ${TABLE}.effective_max_output_tokens ;;
  }

  dimension: reasoning_burn_ratio {
    type: number
    sql: ${TABLE}.reasoning_burn_ratio ;;
    value_format_name: percent_1
  }

  dimension_group: created {
    type: time
    timeframes: [raw, time, date, week, month, quarter, year]
    sql: ${TABLE}.created_at ;;
  }

  # === MEASURES ===
  measure: runs {
    type: count
    drill_fields: [run_id, provider, model_alias, requested_mode, status]
  }

  # Core KPI: REQUIRED enforcement pass rate
  measure: required_enforcement_pass_rate {
    type: average
    sql: CASE
           WHEN ${requested_mode} = 'REQUIRED'
           THEN CASE WHEN ${enforcement_passed} THEN 1 ELSE 0 END
         END ;;
    value_format_name: percent_1
    description: "Percentage of REQUIRED runs that successfully enforced grounding"
  }

  measure: required_grounded_rate {
    type: average
    sql: CASE
           WHEN ${requested_mode} = 'REQUIRED'
           THEN CASE WHEN ${tool_call_count} > 0 THEN 1 ELSE 0 END
         END ;;
    value_format_name: percent_1
    description: "Percentage of REQUIRED runs that performed searches"
  }

  measure: soft_required_fail_rate {
    type: average
    sql: CASE
           WHEN ${requested_mode}='REQUIRED' 
             AND ${enforcement_mode}='soft' 
             AND ${status}='failed'
           THEN 1 ELSE 0
         END ;;
    value_format_name: percent_1
    description: "Failure rate for soft-required (GPT-5) enforcement"
  }

  measure: avg_tool_calls_required {
    type: average
    sql: CASE WHEN ${requested_mode}='REQUIRED' THEN ${tool_call_count} END ;;
    value_format_name: decimal_1
    description: "Average tool calls in REQUIRED mode"
  }

  measure: avg_reasoning_tokens_required {
    type: average
    sql: CASE WHEN ${requested_mode}='REQUIRED' THEN ${usage_reasoning_tokens} END ;;
    value_format_name: decimal_0
    description: "Average reasoning tokens in REQUIRED mode"
  }

  measure: budget_starved_rate_required {
    type: average
    sql: CASE 
           WHEN ${requested_mode}='REQUIRED' AND ${budget_starved} 
           THEN 1 ELSE 0 
         END ;;
    value_format_name: percent_1
    description: "Token starvation rate in REQUIRED mode"
  }

  measure: avg_reasoning_burn_ratio {
    type: average
    sql: ${reasoning_burn_ratio} ;;
    value_format_name: percent_1
    description: "Average ratio of reasoning tokens to output tokens"
  }

  measure: p50_latency {
    type: percentile
    percentile: 50
    sql: ${latency_ms} ;;
    value_format_name: decimal_0
    description: "Median latency in milliseconds"
  }

  measure: p95_latency {
    type: percentile
    percentile: 95
    sql: ${latency_ms} ;;
    value_format_name: decimal_0
    description: "95th percentile latency in milliseconds"
  }
}
```

### 2.2 Explore Definition
```lkml
# models/grounding_enforcement.model.lkml
include: "/views/*.view"

explore: runs_metrics_v1 {
  label: "Grounding Enforcement"
  description: "Analyze enforcement outcomes by provider, model, and mode"
  
  # Optional: Add access filters
  # access_filter: {
  #   field: provider
  #   user_attribute: allowed_providers
  # }
}
```

### 2.3 Dashboard Configuration
```lkml
# dashboards/grounding_enforcement.dashboard.lookml
dashboard: grounding_enforcement {
  title: "Grounding Enforcement Analytics"
  layout: newspaper
  preferred_viewer: dashboards-next

  # Dashboard-level filters
  filter: date_filter {
    type: date
    explore: runs_metrics_v1
    field: runs_metrics_v1.created_date
    default_value: "7 days"
  }

  filter: provider_filter {
    type: field_filter
    explore: runs_metrics_v1
    field: runs_metrics_v1.provider
  }

  filter: model_filter {
    type: field_filter
    explore: runs_metrics_v1
    field: runs_metrics_v1.model_alias
  }

  # === KPI TILES ===
  element: kpi_enforcement_pass_rate {
    title: "REQUIRED Enforcement Pass Rate"
    type: single_value
    explore: runs_metrics_v1
    fields: [runs_metrics_v1.required_enforcement_pass_rate]
    listen:
      date_filter: runs_metrics_v1.created_date
      provider_filter: runs_metrics_v1.provider
      model_filter: runs_metrics_v1.model_alias
    note_display: hover
    note_text: "Percentage of REQUIRED runs where grounding was enforced"
  }

  element: kpi_total_runs {
    title: "Total Runs"
    type: single_value
    explore: runs_metrics_v1
    fields: [runs_metrics_v1.runs]
    listen:
      date_filter: runs_metrics_v1.created_date
      provider_filter: runs_metrics_v1.provider
      model_filter: runs_metrics_v1.model_alias
  }

  element: kpi_avg_reasoning_burn {
    title: "Avg Reasoning Burn"
    type: single_value
    explore: runs_metrics_v1
    fields: [runs_metrics_v1.avg_reasoning_burn_ratio]
    listen:
      date_filter: runs_metrics_v1.created_date
      provider_filter: runs_metrics_v1.provider
      model_filter: runs_metrics_v1.model_alias
  }

  # === CHARTS ===
  element: chart_enforcement_by_provider {
    title: "Enforcement Pass Rate by Provider"
    type: looker_column
    explore: runs_metrics_v1
    dimensions: [runs_metrics_v1.provider, runs_metrics_v1.requested_mode]
    measures: [runs_metrics_v1.required_enforcement_pass_rate]
    pivots: [runs_metrics_v1.requested_mode]
    listen:
      date_filter: runs_metrics_v1.created_date
      model_filter: runs_metrics_v1.model_alias
  }

  element: chart_soft_required_failures {
    title: "Soft-Required Failures (GPT-5)"
    type: looker_bar
    explore: runs_metrics_v1
    dimensions: [runs_metrics_v1.model_alias]
    measures: [runs_metrics_v1.soft_required_fail_rate]
    filters:
      runs_metrics_v1.is_gpt5: "Yes"
    sorts: [runs_metrics_v1.soft_required_fail_rate desc]
    listen:
      date_filter: runs_metrics_v1.created_date
  }

  element: table_failure_reasons {
    title: "Failure Reasons (REQUIRED Mode)"
    type: table
    explore: runs_metrics_v1
    dimensions: [
      runs_metrics_v1.error_code,
      runs_metrics_v1.why_not_grounded,
      runs_metrics_v1.enforcement_mode
    ]
    measures: [runs_metrics_v1.runs]
    filters:
      runs_metrics_v1.requested_mode: "REQUIRED"
      runs_metrics_v1.status: "failed"
    sorts: [runs_metrics_v1.runs desc]
    listen:
      date_filter: runs_metrics_v1.created_date
      provider_filter: runs_metrics_v1.provider
      model_filter: runs_metrics_v1.model_alias
  }

  element: scatter_reasoning_vs_searches {
    title: "Reasoning Tokens vs Tool Calls"
    type: looker_scatter
    explore: runs_metrics_v1
    dimensions: [runs_metrics_v1.usage_reasoning_tokens]
    measures: [runs_metrics_v1.tool_call_count]
    fields: [
      runs_metrics_v1.usage_reasoning_tokens,
      runs_metrics_v1.tool_call_count,
      runs_metrics_v1.provider
    ]
    filters:
      runs_metrics_v1.requested_mode: "REQUIRED"
    listen:
      date_filter: runs_metrics_v1.created_date
      model_filter: runs_metrics_v1.model_alias
  }

  element: line_trend_enforcement {
    title: "Enforcement Pass Rate Trend"
    type: looker_line
    explore: runs_metrics_v1
    dimensions: [runs_metrics_v1.created_date]
    measures: [runs_metrics_v1.required_enforcement_pass_rate]
    fields: [
      runs_metrics_v1.created_date,
      runs_metrics_v1.required_enforcement_pass_rate,
      runs_metrics_v1.provider
    ]
    pivots: [runs_metrics_v1.provider]
    listen:
      date_filter: runs_metrics_v1.created_date
      model_filter: runs_metrics_v1.model_alias
  }

  element: heatmap_token_starvation {
    title: "Token Starvation by Model & Mode"
    type: looker_grid
    explore: runs_metrics_v1
    dimensions: [runs_metrics_v1.model_alias, runs_metrics_v1.requested_mode]
    measures: [runs_metrics_v1.budget_starved_rate_required]
    listen:
      date_filter: runs_metrics_v1.created_date
      provider_filter: runs_metrics_v1.provider
  }
}
```

## 3. React Components

### 3.1 Run Detail Card Component
```tsx
// app/components/runs/RunDetailCard.tsx
import { Card, CardHeader, CardContent, CardFooter } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { AlertTriangle, CheckCircle2, XCircle, Search, Timer, Info, Cpu, Zap } from "lucide-react";

type Run = {
  id: string;
  provider: "openai" | "vertex" | string;
  model_alias: string;
  requested_mode: "UNGROUNDED" | "PREFERRED" | "REQUIRED";
  enforcement_mode: "none" | "soft" | "hard";
  enforcement_passed?: boolean | null;
  status: "ok" | "failed";
  tool_call_count: number;
  grounded_effective: boolean;
  why_not_grounded?: string | null;
  error_code?: string | null;
  usage_reasoning_tokens?: number | null;
  usage_output_tokens?: number | null;
  usage_total_tokens?: number | null;
  effective_max_output_tokens?: number | null;
  budget_starved?: boolean | null;
  latency_ms?: number | null;
  provoker_hash?: string | null;
  answer_text?: string | null;
};

export function RunDetailCard({
  run,
  onRetry
}: {
  run: Run;
  onRetry?: (runId: string) => void;
}) {
  const isGPT5 = /^gpt-5/i.test(run.model_alias || "");
  const isRequired = run.requested_mode === "REQUIRED";
  const modeLabel =
    isRequired && isGPT5 && run.enforcement_mode === "soft"
      ? "REQUIRED (soft on GPT-5)"
      : run.requested_mode;

  const groundedBadge =
    run.tool_call_count > 0 ? (
      <Badge variant="secondary" className="gap-1 bg-emerald-50 text-emerald-700 border-emerald-200">
        <CheckCircle2 className="h-4 w-4" /> Grounded ({run.tool_call_count} searches)
      </Badge>
    ) : (
      <Badge variant="secondary" className="gap-1 bg-rose-50 text-rose-700 border-rose-200">
        <XCircle className="h-4 w-4" /> Not grounded
      </Badge>
    );

  const statusBadge =
    run.status === "ok" ? (
      <Badge className="bg-emerald-600 hover:bg-emerald-600">OK</Badge>
    ) : (
      <Badge className="bg-rose-600 hover:bg-rose-600">Failed</Badge>
    );

  const enforcementBadge = run.enforcement_passed ? (
    <Badge variant="outline" className="gap-1 text-emerald-700">
      <CheckCircle2 className="h-3 w-3" /> Enforcement Passed
    </Badge>
  ) : (
    <Badge variant="outline" className="gap-1 text-rose-700">
      <XCircle className="h-3 w-3" /> Enforcement Failed
    </Badge>
  );

  const showRetry = run.budget_starved && isRequired && run.status === "failed";

  const reasoningBurnPercent = run.usage_reasoning_tokens && run.usage_output_tokens
    ? (run.usage_reasoning_tokens / run.usage_output_tokens * 100).toFixed(1)
    : null;

  return (
    <Card className="rounded-2xl shadow-sm">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between mb-3">
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="outline">{modeLabel}</Badge>
            <Badge variant="outline" className="capitalize">{run.provider}</Badge>
            <Badge variant="outline">{run.model_alias}</Badge>
            {groundedBadge}
            {statusBadge}
          </div>
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Timer className="h-4 w-4" />
            {typeof run.latency_ms === "number" ? `${run.latency_ms} ms` : "–"}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="outline">Enforcement: {run.enforcement_mode}</Badge>
          {enforcementBadge}
        </div>
      </CardHeader>

      <CardContent className="grid gap-4">
        {/* Telemetry metrics */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <Metric 
            label="Tool calls" 
            value={String(run.tool_call_count)} 
            icon={<Search className="h-4 w-4" />} 
          />
          <Metric 
            label="Reasoning tokens" 
            value={fmtNum(run.usage_reasoning_tokens)}
            subtitle={reasoningBurnPercent ? `${reasoningBurnPercent}% of output` : undefined}
            icon={<Cpu className="h-4 w-4" />}
          />
          <Metric 
            label="Output cap" 
            value={fmtNum(run.effective_max_output_tokens)}
            icon={<Zap className="h-4 w-4" />}
          />
          <Metric 
            label="Budget starved" 
            value={run.budget_starved ? "Yes" : "No"}
            className={run.budget_starved ? "border-amber-200 bg-amber-50" : ""}
          />
        </div>

        {/* Failure explanation for REQUIRED mode */}
        {isRequired && !run.enforcement_passed && (
          <div className="flex items-start gap-3 rounded-xl border border-amber-200 bg-amber-50 p-3">
            <AlertTriangle className="mt-0.5 h-5 w-5 text-amber-600" />
            <div className="text-sm">
              <div className="font-medium text-amber-800">
                Enforcement Failed in REQUIRED Mode
              </div>
              <div className="text-amber-800/90 mt-1">
                {run.enforcement_mode === "soft" && isGPT5
                  ? "GPT-5 doesn't support tool_choice:'required'. The model declined to search despite the search-first directive."
                  : "No tool calls were made in REQUIRED mode."}
              </div>
              {run.why_not_grounded && (
                <div className="mt-2 text-xs">
                  <span className="font-medium">Reason:</span> {run.why_not_grounded}
                </div>
              )}
              {run.error_code && (
                <div className="text-xs mt-1">
                  <span className="font-medium">Code:</span> <code className="px-1 py-0.5 bg-amber-100 rounded">{run.error_code}</code>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Token starvation warning */}
        {run.budget_starved && (
          <div className="flex items-start gap-3 rounded-xl border border-orange-200 bg-orange-50 p-3">
            <Zap className="mt-0.5 h-5 w-5 text-orange-600" />
            <div className="text-sm">
              <div className="font-medium text-orange-800">
                Token Budget Exhausted
              </div>
              <div className="text-orange-800/90 mt-1">
                All {run.usage_reasoning_tokens} output tokens were consumed by reasoning, 
                leaving no tokens for the final message. Consider retrying with a higher token limit.
              </div>
            </div>
          </div>
        )}

        {/* Answer preview */}
        {run.answer_text && (
          <div className="rounded-xl border bg-card p-3 text-sm">
            <div className="mb-1 font-medium text-muted-foreground">Answer</div>
            <div className="whitespace-pre-wrap font-mono text-xs">{run.answer_text}</div>
          </div>
        )}
      </CardContent>

      <CardFooter className="flex items-center justify-between">
        <TooltipProvider>
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Info className="h-3.5 w-3.5" />
            <Tooltip>
              <TooltipTrigger className="underline underline-offset-4">
                What is enforcement?
              </TooltipTrigger>
              <TooltipContent className="max-w-xs text-xs">
                <p className="mb-2">Enforcement ensures grounding requirements are met:</p>
                <ul className="list-disc list-inside space-y-1">
                  <li><strong>REQUIRED:</strong> Must perform web_search or fail</li>
                  <li><strong>PREFERRED:</strong> Search optional, no enforcement</li>
                  <li><strong>UNGROUNDED:</strong> Must NOT search or fail</li>
                </ul>
                <p className="mt-2">GPT-5 uses "soft" enforcement (can't force searches).</p>
              </TooltipContent>
            </Tooltip>
          </div>
        </TooltipProvider>

        {showRetry && (
          <Button
            onClick={() => onRetry?.(run.id)}
            variant="default"
            className="rounded-xl"
          >
            Retry same mode (2048 tokens)
          </Button>
        )}
      </CardFooter>
    </Card>
  );
}

function Metric({ 
  label, 
  value, 
  subtitle,
  icon,
  className = ""
}: { 
  label: string; 
  value: string;
  subtitle?: string;
  icon?: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={`rounded-xl border bg-white p-3 ${className}`}>
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        {icon}
        {label}
      </div>
      <div className="mt-1 text-base font-semibold">{value ?? "–"}</div>
      {subtitle && (
        <div className="text-xs text-muted-foreground mt-0.5">{subtitle}</div>
      )}
    </div>
  );
}

function fmtNum(n?: number | null) {
  if (n === null || n === undefined) return "–";
  return new Intl.NumberFormat().format(n);
}
```

### 3.2 Next.js API Routes

#### Get Single Run
```ts
// app/api/runs/[id]/route.ts
import { NextResponse } from "next/server";
import { BigQuery } from "@google-cloud/bigquery";

const bq = new BigQuery({ projectId: process.env.GOOGLE_PROJECT_ID });

export async function GET(_req: Request, ctx: { params: { id: string } }) {
  const runId = ctx.params.id;
  
  try {
    const [rows] = await bq.query({
      query: `
        SELECT
          run_id as id,
          provider,
          model_alias,
          requested_mode,
          enforcement_mode,
          enforcement_passed,
          status,
          tool_call_count,
          grounded_effective,
          why_not_grounded,
          error_code,
          usage_reasoning_tokens,
          usage_output_tokens,
          usage_total_tokens,
          budget_starved,
          effective_max_output_tokens,
          latency_ms,
          provoker_hash,
          answer_text
        FROM \`contestra.metrics.runs_metrics_v1\`
        WHERE run_id = @run_id
        LIMIT 1
      `,
      params: { run_id: runId },
    });

    if (!rows || rows.length === 0) {
      return NextResponse.json({ error: "Run not found" }, { status: 404 });
    }
    
    return NextResponse.json(rows[0]);
  } catch (error) {
    console.error("BigQuery error:", error);
    return NextResponse.json(
      { error: "Failed to fetch run data" },
      { status: 500 }
    );
  }
}
```

#### Retry Same Mode
```ts
// app/api/runs/[id]/retry/route.ts
import { NextResponse } from "next/server";

export async function POST(req: Request, ctx: { params: { id: string } }) {
  const runId = ctx.params.id;
  const body = await req.json().catch(() => ({}));
  
  // Default to 2048 tokens for retry
  const maxTokens = body.max_output_tokens || 2048;
  
  try {
    const url = `${process.env.BACKEND_URL}/api/runs/${encodeURIComponent(runId)}/retry`;
    
    const response = await fetch(url, {
      method: "POST",
      headers: { 
        "content-type": "application/json",
        "x-api-key": process.env.BACKEND_API_KEY || ""
      },
      body: JSON.stringify({ 
        max_output_tokens: maxTokens,
        maintain_mode: true  // Critical: keep same mode
      }),
    });
    
    if (!response.ok) {
      const text = await response.text();
      return NextResponse.json(
        { error: text || "Retry failed" },
        { status: response.status }
      );
    }
    
    const data = await response.json();
    return NextResponse.json({ 
      ok: true,
      new_run_id: data.run_id,
      ...data 
    });
  } catch (error) {
    console.error("Retry error:", error);
    return NextResponse.json(
      { error: "Failed to retry run" },
      { status: 500 }
    );
  }
}
```

### 3.3 Server Component Page
```tsx
// app/runs/[id]/page.tsx
import { RunDetailCard } from "@/components/runs/RunDetailCard";
import { redirect } from "next/navigation";

async function getRun(id: string) {
  const res = await fetch(
    `${process.env.NEXT_PUBLIC_APP_URL}/api/runs/${id}`,
    { cache: "no-store" }
  );
  
  if (!res.ok) {
    if (res.status === 404) {
      return null;
    }
    throw new Error("Failed to fetch run");
  }
  
  return res.json();
}

async function retryRun(runId: string) {
  "use server";
  
  const res = await fetch(
    `${process.env.NEXT_PUBLIC_APP_URL}/api/runs/${runId}/retry`,
    {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ max_output_tokens: 2048 }),
      cache: "no-store"
    }
  );
  
  if (res.ok) {
    const data = await res.json();
    if (data.new_run_id) {
      redirect(`/runs/${data.new_run_id}`);
    }
  }
}

export default async function RunPage({ 
  params 
}: { 
  params: { id: string } 
}) {
  const run = await getRun(params.id);
  
  if (!run) {
    return (
      <div className="container mx-auto max-w-4xl p-6">
        <Card>
          <CardContent className="py-8 text-center">
            <p className="text-muted-foreground">Run not found</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="container mx-auto max-w-4xl p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold">Run Details</h1>
        <p className="text-muted-foreground">
          ID: <code className="text-xs">{params.id}</code>
        </p>
      </div>
      
      <RunDetailCard
        run={run}
        onRetry={async () => {
          await retryRun(params.id);
        }}
      />
    </div>
  );
}
```

## 4. PostgreSQL Variant (Alternative to BigQuery)

If using PostgreSQL instead of BigQuery:

### 4.1 Database View
```sql
-- Create metrics view in PostgreSQL
CREATE OR REPLACE VIEW runs_metrics_v1 AS
SELECT
  run_id,
  provider,
  model_alias,
  requested_mode,
  enforcement_mode,
  enforcement_passed,
  status,
  tool_call_count,
  grounded_effective,
  why_not_grounded,
  error_code,
  usage_reasoning_tokens,
  usage_output_tokens,
  usage_total_tokens,
  budget_starved,
  effective_max_output_tokens,
  latency_ms,
  provoker_hash,
  answer_text,
  -- Computed fields
  (model_alias ~* '^gpt-5') AS is_gpt5,
  (requested_mode = 'REQUIRED' AND tool_call_count > 0) AS enforcement_passed_calc,
  CASE 
    WHEN usage_output_tokens > 0 
    THEN usage_reasoning_tokens::float / usage_output_tokens 
    ELSE NULL 
  END AS reasoning_burn_ratio,
  created_at,
  DATE(created_at) AS run_date
FROM runs;

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_runs_created_at ON runs(created_at);
CREATE INDEX IF NOT EXISTS idx_runs_provider_model ON runs(provider, model_alias);
CREATE INDEX IF NOT EXISTS idx_runs_requested_mode ON runs(requested_mode);
```

### 4.2 Next.js API Route for PostgreSQL
```ts
// app/api/runs/[id]/route.ts (PostgreSQL version)
import { NextResponse } from "next/server";
import { Pool } from "pg";

const pool = new Pool({ 
  connectionString: process.env.DATABASE_URL,
  ssl: process.env.NODE_ENV === "production" ? { rejectUnauthorized: false } : false
});

export async function GET(_req: Request, ctx: { params: { id: string } }) {
  try {
    const { rows } = await pool.query(
      `SELECT 
        run_id as id,
        provider,
        model_alias,
        requested_mode,
        enforcement_mode,
        enforcement_passed,
        status,
        tool_call_count,
        grounded_effective,
        why_not_grounded,
        error_code,
        usage_reasoning_tokens,
        usage_output_tokens,
        usage_total_tokens,
        budget_starved,
        effective_max_output_tokens,
        latency_ms,
        provoker_hash,
        answer_text
      FROM runs_metrics_v1 
      WHERE run_id = $1 
      LIMIT 1`,
      [ctx.params.id]
    );
    
    if (!rows.length) {
      return NextResponse.json({ error: "Run not found" }, { status: 404 });
    }
    
    return NextResponse.json(rows[0]);
  } catch (error) {
    console.error("Database error:", error);
    return NextResponse.json(
      { error: "Failed to fetch run data" },
      { status: 500 }
    );
  }
}
```

## 5. Key Metrics to Track

### 5.1 Executive Dashboard
- **REQUIRED Enforcement Pass Rate** - Primary KPI
- **Average Tool Calls by Provider** - Behavioral difference
- **Token Starvation Rate** - Operational health
- **P95 Latency** - Performance metric

### 5.2 Engineering Dashboard
- **Reasoning Burn Ratio** - Token efficiency
- **Failure Reasons Distribution** - Debug insights
- **Soft vs Hard Enforcement** - Provider capabilities
- **Budget Starvation by Model** - Capacity planning

### 5.3 Alerts to Configure
```sql
-- Alert: High token starvation rate
SELECT 
  AVG(CASE WHEN budget_starved THEN 1.0 ELSE 0.0 END) as starvation_rate
FROM runs_metrics_v1
WHERE created_at > CURRENT_TIMESTAMP - INTERVAL '1 hour'
HAVING starvation_rate > 0.1;  -- Alert if >10% starved

-- Alert: Low enforcement rate
SELECT 
  provider,
  model_alias,
  AVG(CASE WHEN enforcement_passed THEN 1.0 ELSE 0.0 END) as pass_rate
FROM runs_metrics_v1
WHERE requested_mode = 'REQUIRED'
  AND created_at > CURRENT_TIMESTAMP - INTERVAL '1 hour'
GROUP BY provider, model_alias
HAVING pass_rate < 0.5;  -- Alert if <50% pass rate
```

## 6. Implementation Checklist

- [ ] Create BigQuery dataset and tables
- [ ] Deploy metrics view
- [ ] Configure service account with BigQuery access
- [ ] Add LookML files to Looker project
- [ ] Deploy dashboard configuration
- [ ] Implement React components
- [ ] Set up Next.js API routes
- [ ] Configure environment variables
- [ ] Test retry functionality
- [ ] Set up monitoring alerts
- [ ] Document for team

## 7. Environment Variables

```env
# BigQuery
GOOGLE_PROJECT_ID=contestra-ai
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json

# PostgreSQL (alternative)
DATABASE_URL=postgresql://user:pass@host:5432/dbname

# Backend
BACKEND_URL=https://api.contestra.com
BACKEND_API_KEY=your-api-key

# Next.js
NEXT_PUBLIC_APP_URL=https://app.contestra.com
```

## Conclusion

This implementation provides:
1. **Complete observability** into grounding enforcement
2. **Measurement integrity** preserved throughout
3. **Clear failure reasons** for debugging
4. **Retry capability** without mode changes
5. **Executive visibility** through Looker dashboards

The system reveals true provider differences while maintaining experimental rigor.