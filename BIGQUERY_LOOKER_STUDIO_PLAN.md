# BigQuery & Looker Studio Implementation Plan for AI Ranker

**Date**: August 15, 2025  
**Status**: Planning Phase  
**Priority**: High - Next Major Feature

## Executive Summary

Implement BigQuery for scalable analytics storage and Looker Studio for client-facing dashboards to track AI brand visibility across models, countries, and grounding modes. This will replace the current basic "Results" tab with enterprise-grade analytics.

## Why BigQuery & Looker Studio

### Business Value
1. **Scale**: Handle millions of prompt runs without performance degradation
2. **Client Isolation**: Row-level security for multi-brand support (AVEA, future clients)
3. **Real-time Analytics**: Stream results as they complete, instant visibility
4. **Professional Dashboards**: Move from basic tables to interactive visualizations
5. **Cost Effective**: <$10/month initially, <$100/month at scale

### Technical Advantages
1. **Append-heavy, query-light**: Perfect for event streaming (prompt runs)
2. **Columnar storage**: Fast aggregations across millions of rows
3. **Native RLS**: Google identity-based access control
4. **EU Data Locality**: Matches Vertex AI in europe-west4
5. **No Infrastructure**: Fully serverless, zero maintenance

## Architecture Overview

```
┌─────────────────┐
│  AI Ranker App  │
│   (FastAPI)     │
└────────┬────────┘
         │ Stream events
         ▼
┌─────────────────┐
│    BigQuery     │
│  (EU Dataset)   │
│  - Partitioned  │
│  - Clustered    │
│  - RLS Enabled  │
└────────┬────────┘
         │ Query
         ▼
┌─────────────────┐
│  Looker Studio  │
│  - Embedded     │
│  - Parameterized│
│  - Secure       │
└─────────────────┘
```

## Implementation Phases

### Phase 1: BigQuery Setup (Week 1)

#### 1.1 Create Dataset & Tables
```sql
-- Create EU dataset for data locality
CREATE SCHEMA IF NOT EXISTS `contestra-ai.ai_ranker`
OPTIONS(location="EU", description="AI Ranker analytics data");

-- Main runs table
CREATE TABLE IF NOT EXISTS `contestra-ai.ai_ranker.prompt_runs` (
  -- Identifiers
  run_id STRING NOT NULL,
  template_id STRING NOT NULL,
  template_name STRING,
  workspace_id STRING NOT NULL,  -- Brand/client identifier
  org_id STRING,
  
  -- Configuration
  prompt_text STRING,
  prompt_hash STRING,
  model_name STRING,
  provider STRING,  -- 'openai' or 'google'
  countries ARRAY<STRING>,
  grounding_modes ARRAY<STRING>,
  prompt_type STRING,
  
  -- Timing
  created_at TIMESTAMP NOT NULL,
  completed_at TIMESTAMP,
  total_duration_ms INT64,
  
  -- Metadata
  als_applied BOOL,
  temperature FLOAT64,
  seed INT64,
  system_fingerprint STRING,
  
  -- Aggregated results
  total_results INT64,
  successful_results INT64,
  failed_results INT64,
  avg_mention_rate FLOAT64,
  avg_confidence FLOAT64
)
PARTITION BY DATE(created_at)
CLUSTER BY workspace_id, provider, model_name
OPTIONS(
  description="Prompt template runs with configuration and aggregated results",
  partition_expiration_days=365
);

-- Individual results table
CREATE TABLE IF NOT EXISTS `contestra-ai.ai_ranker.prompt_results` (
  -- Identifiers
  result_id STRING NOT NULL,
  run_id STRING NOT NULL,
  workspace_id STRING NOT NULL,
  
  -- Test configuration
  country STRING,
  grounding_mode STRING,
  
  -- Brand detection
  brand_name STRING,
  brand_mentioned BOOL,
  mention_count INT64,
  confidence_score FLOAT64,
  
  -- Response details
  response_text STRING,
  response_time_ms INT64,
  model_version STRING,
  response_id STRING,  -- Gemini's responseId
  
  -- Probe results (for Countries tab)
  probe_results JSON,  -- {vat, plug, emergency}
  probe_passed BOOL,
  
  -- Quality metrics
  leak_detected BOOL,
  leak_phrases ARRAY<STRING>,
  
  -- Timing
  created_at TIMESTAMP NOT NULL
)
PARTITION BY DATE(created_at)
CLUSTER BY workspace_id, country, grounding_mode
OPTIONS(
  description="Individual test results with brand detection and probe outcomes",
  partition_expiration_days=180  -- Keep raw results for 6 months
);

-- Brand/workspace metadata
CREATE TABLE IF NOT EXISTS `contestra-ai.ai_ranker.workspaces` (
  workspace_id STRING NOT NULL,
  workspace_name STRING,
  brand_name STRING,
  domain STRING,
  industry STRING,
  created_at TIMESTAMP,
  active BOOL
)
OPTIONS(description="Brand/client workspace metadata");
```

#### 1.2 Row-Level Security Setup
```sql
-- Access control table
CREATE TABLE IF NOT EXISTS `contestra-ai.ai_ranker.user_access` (
  email STRING NOT NULL,         -- Google account email
  workspace_id STRING NOT NULL,  -- Which workspace they can access
  permission_level STRING,       -- 'view', 'edit', 'admin'
  granted_at TIMESTAMP,
  granted_by STRING
)
OPTIONS(description="Maps Google accounts to workspace access");

-- Row-level security policy for runs
CREATE OR REPLACE ROW ACCESS POLICY workspace_access_runs
ON `contestra-ai.ai_ranker.prompt_runs`
GRANT TO ('domain:contestra.com')  -- Adjust to your domain
FILTER USING (
  workspace_id IN (
    SELECT workspace_id
    FROM `contestra-ai.ai_ranker.user_access`
    WHERE email = SESSION_USER()
    AND permission_level IN ('view', 'edit', 'admin')
  )
);

-- Row-level security policy for results
CREATE OR REPLACE ROW ACCESS POLICY workspace_access_results
ON `contestra-ai.ai_ranker.prompt_results`
GRANT TO ('domain:contestra.com')
FILTER USING (
  workspace_id IN (
    SELECT workspace_id
    FROM `contestra-ai.ai_ranker.user_access`
    WHERE email = SESSION_USER()
    AND permission_level IN ('view', 'edit', 'admin')
  )
);
```

### Phase 2: Data Streaming Integration (Week 1-2)

#### 2.1 Add BigQuery Client to Backend
```python
# backend/app/services/bigquery_streamer.py
from google.cloud import bigquery
from typing import List, Dict, Any
import asyncio
from datetime import datetime

class BigQueryStreamer:
    def __init__(self, project_id="contestra-ai", dataset_id="ai_ranker"):
        self.client = bigquery.Client(project=project_id)
        self.dataset_id = dataset_id
        self.project_id = project_id
        
    async def stream_run(self, run: PromptRun, results: List[PromptResult]):
        """Stream a completed run and its results to BigQuery"""
        
        # Prepare run record
        run_row = {
            "run_id": str(run.id),
            "template_id": str(run.template_id),
            "template_name": run.template.name if run.template else None,
            "workspace_id": run.workspace_id or "default",
            "org_id": run.org_id,
            "prompt_text": run.template.prompt_text if run.template else None,
            "prompt_hash": run.prompt_hash,
            "model_name": run.model_name,
            "provider": self._get_provider(run.model_name),
            "countries": run.countries,
            "grounding_modes": run.grounding_modes,
            "prompt_type": run.template.prompt_type if run.template else "custom",
            "created_at": run.created_at.isoformat(),
            "completed_at": run.completed_at.isoformat() if run.completed_at else None,
            "total_duration_ms": run.total_duration_ms,
            "als_applied": any(c != "NONE" for c in run.countries),
            "temperature": 0.0,  # We use fixed temperature
            "seed": 42,  # Fixed seed
            "system_fingerprint": run.system_fingerprint,
            "total_results": len(results),
            "successful_results": sum(1 for r in results if r.response_text),
            "failed_results": sum(1 for r in results if not r.response_text),
            "avg_mention_rate": self._calculate_avg_mention_rate(results),
            "avg_confidence": self._calculate_avg_confidence(results)
        }
        
        # Stream run to BigQuery
        table_id = f"{self.project_id}.{self.dataset_id}.prompt_runs"
        errors = self.client.insert_rows_json(table_id, [run_row])
        
        if errors:
            print(f"Failed to stream run: {errors}")
            
        # Prepare result records
        result_rows = []
        for result in results:
            result_row = {
                "result_id": str(result.id),
                "run_id": str(result.run_id),
                "workspace_id": run.workspace_id or "default",
                "country": result.country,
                "grounding_mode": result.grounding_mode,
                "brand_name": run.brand_name,
                "brand_mentioned": result.brand_mentioned,
                "mention_count": result.mention_count,
                "confidence_score": result.confidence_score,
                "response_text": result.response_text[:10000] if result.response_text else None,  # Truncate for storage
                "response_time_ms": result.response_time_ms,
                "model_version": result.model_version,
                "response_id": result.response_id,
                "probe_results": {
                    "vat": getattr(result, 'probe_vat', None),
                    "plug": getattr(result, 'probe_plug', None),
                    "emergency": getattr(result, 'probe_emergency', None)
                },
                "probe_passed": getattr(result, 'probe_passed', False),
                "leak_detected": False,  # TODO: Implement leak detection
                "leak_phrases": [],
                "created_at": result.created_at.isoformat()
            }
            result_rows.append(result_row)
        
        # Stream results to BigQuery
        if result_rows:
            table_id = f"{self.project_id}.{self.dataset_id}.prompt_results"
            errors = self.client.insert_rows_json(table_id, result_rows)
            
            if errors:
                print(f"Failed to stream results: {errors}")
    
    def _get_provider(self, model_name: str) -> str:
        if "gpt" in model_name.lower():
            return "openai"
        elif "gemini" in model_name.lower():
            return "google"
        else:
            return "unknown"
    
    def _calculate_avg_mention_rate(self, results: List[PromptResult]) -> float:
        if not results:
            return 0.0
        mentions = sum(1 for r in results if r.brand_mentioned)
        return mentions / len(results)
    
    def _calculate_avg_confidence(self, results: List[PromptResult]) -> float:
        if not results:
            return 0.0
        confidences = [r.confidence_score for r in results if r.confidence_score]
        if not confidences:
            return 0.0
        return sum(confidences) / len(confidences)
```

#### 2.2 Integrate Streaming into Prompt Tracking
```python
# In backend/app/api/prompt_tracking.py
# Add to run_template endpoint after saving results

from app.services.bigquery_streamer import BigQueryStreamer

# After all results are saved
try:
    streamer = BigQueryStreamer()
    await streamer.stream_run(run, results)
except Exception as e:
    # Log but don't fail the request
    print(f"BigQuery streaming failed: {e}")
```

### Phase 3: Looker Studio Dashboards (Week 2)

#### 3.1 Create Report Parameters
In Looker Studio, create these parameters:
- `workspace_id` (Text) - Filter by brand/client
- `country` (Text) - Filter by test country
- `grounded` (Boolean) - Filter by grounding mode
- `model` (Text) - Filter by AI model
- `start_date` (Date) - Start of date range
- `end_date` (Date) - End of date range

#### 3.2 Custom Query Data Source
```sql
-- Parameterized query for Looker Studio
DECLARE p_workspace_id STRING DEFAULT @workspace_id;
DECLARE p_country STRING DEFAULT @country;
DECLARE p_grounded BOOL DEFAULT @grounded;
DECLARE p_model STRING DEFAULT @model;
DECLARE p_start_date DATE DEFAULT @start_date;
DECLARE p_end_date DATE DEFAULT @end_date;

WITH filtered_results AS (
  SELECT 
    r.*,
    pr.template_name,
    pr.prompt_type,
    pr.provider,
    DATE(r.created_at, 'Europe/Ljubljana') as result_date
  FROM `contestra-ai.ai_ranker.prompt_results` r
  LEFT JOIN `contestra-ai.ai_ranker.prompt_runs` pr
    ON r.run_id = pr.run_id
  WHERE 
    DATE(r.created_at, 'Europe/Ljubljana') BETWEEN p_start_date AND p_end_date
    AND (p_workspace_id IS NULL OR p_workspace_id = '' OR r.workspace_id = p_workspace_id)
    AND (p_country IS NULL OR p_country = '' OR r.country = p_country)
    AND (p_grounded IS NULL OR r.grounding_mode = IF(p_grounded, 'web', 'none'))
    AND (p_model IS NULL OR p_model = '' OR pr.model_name = p_model)
)
SELECT 
  workspace_id,
  country,
  grounding_mode,
  brand_name,
  provider,
  model_version,
  template_name,
  prompt_type,
  
  -- Metrics
  COUNT(*) as total_tests,
  SUM(IF(brand_mentioned, 1, 0)) as mentions,
  AVG(IF(brand_mentioned, 1, 0)) * 100 as mention_rate,
  AVG(confidence_score) as avg_confidence,
  AVG(response_time_ms) as avg_response_time,
  
  -- Probe metrics (Countries tab)
  SUM(IF(probe_passed, 1, 0)) as probes_passed,
  AVG(IF(probe_passed, 1, 0)) * 100 as probe_success_rate,
  
  -- Time dimensions
  result_date,
  EXTRACT(HOUR FROM created_at) as hour_of_day,
  FORMAT_DATE('%A', result_date) as day_of_week
  
FROM filtered_results
GROUP BY 1,2,3,4,5,6,7,8,9,10,11
```

#### 3.3 Dashboard Pages

##### Page 1: Executive Overview
- **KPI Cards**: Total runs, avg mention rate, avg confidence
- **Time Series**: Mention rate over time by model
- **Country Heatmap**: Performance by country
- **Model Comparison**: Side-by-side GPT-5 vs Gemini

##### Page 2: Brand Visibility Analysis
- **Mention Rate by Configuration**: Country × Grounding matrix
- **Template Performance**: Which prompts work best
- **Response Time Analysis**: Performance by model/country

##### Page 3: Locale Testing (Countries Tab)
- **Probe Success Matrix**: VAT/Plug/Emergency by country
- **ALS Effectiveness**: Compare NONE vs country-specific
- **Leak Detection**: Any location mentions in responses

##### Page 4: Model Fingerprint Tracking
- **Version Timeline**: When models update
- **Performance Drift**: Changes after model updates
- **Reproducibility Score**: Consistency with same fingerprint

### Phase 4: Embed in React App (Week 2-3)

#### 4.1 Create Dashboard Component
```tsx
// frontend/src/components/AnalyticsDashboard.tsx
import React, { useMemo } from 'react';
import { Card } from '@/components/ui/card';

interface DashboardProps {
  workspaceId?: string;
  brandName?: string;
}

export function AnalyticsDashboard({ workspaceId, brandName }: DashboardProps) {
  const REPORT_ID = "YOUR_LOOKER_STUDIO_REPORT_ID"; // Replace after creating report
  const BASE_URL = `https://lookerstudio.google.com/embed/reporting/${REPORT_ID}/page/p_abc123`;
  
  const embedUrl = useMemo(() => {
    const params = {
      workspace_id: workspaceId || '',
      start_date: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
      end_date: new Date().toISOString().split('T')[0]
    };
    
    const paramString = encodeURIComponent(JSON.stringify(params));
    return `${BASE_URL}?params=${paramString}`;
  }, [workspaceId]);
  
  return (
    <Card className="p-4">
      <div className="mb-4">
        <h2 className="text-2xl font-bold">
          Analytics Dashboard {brandName && `- ${brandName}`}
        </h2>
      </div>
      
      <iframe
        src={embedUrl}
        className="w-full h-[800px] rounded-lg border"
        frameBorder="0"
        allowFullScreen
      />
      
      <div className="mt-4 text-sm text-muted-foreground">
        <p>Note: You'll need to sign in with your Google account to view the dashboard.</p>
        <p>Data is updated in real-time as tests complete.</p>
      </div>
    </Card>
  );
}
```

#### 4.2 Replace Results Tab
```tsx
// In PromptTracking.tsx, replace the Results tab content
{activeTab === 'results' && (
  <AnalyticsDashboard 
    workspaceId={selectedBrand?.workspace_id}
    brandName={selectedBrand?.name}
  />
)}
```

## Migration Strategy

### Data Migration (Optional)
```python
# One-time script to migrate existing PostgreSQL data to BigQuery
import asyncio
from sqlalchemy import select
from app.database import async_session
from app.models import PromptRun, PromptResult
from app.services.bigquery_streamer import BigQueryStreamer

async def migrate_to_bigquery():
    streamer = BigQueryStreamer()
    
    async with async_session() as session:
        # Get all runs
        runs = await session.execute(
            select(PromptRun).order_by(PromptRun.created_at)
        )
        
        for run in runs.scalars():
            # Get results for this run
            results = await session.execute(
                select(PromptResult).where(PromptResult.run_id == run.id)
            )
            
            # Stream to BigQuery
            await streamer.stream_run(run, list(results.scalars()))
            
    print("Migration complete!")

# Run migration
asyncio.run(migrate_to_bigquery())
```

## Cost Analysis

### Estimated Monthly Costs
- **Storage**: 1GB × $0.02 = $0.02
- **Streaming Inserts**: 10MB × $0.05 = $0.0005
- **Queries**: 100GB scanned × $5/TB = $0.50
- **Looker Studio**: FREE
- **Total**: <$1/month initially, <$10/month at 100x scale

### Cost Optimization
1. **Partition by date**: Queries scan only needed partitions
2. **Cluster by workspace**: Fast filtering for client data
3. **Materialized views**: Pre-aggregate common queries
4. **Table expiration**: Auto-delete old raw data

## Security Considerations

1. **Authentication**: Google identity-based (no custom auth needed)
2. **Row-Level Security**: Enforced by BigQuery, not application
3. **Data Residency**: EU dataset for GDPR compliance
4. **Audit Trail**: BigQuery logs all access automatically
5. **Encryption**: At-rest and in-transit by default

## Success Metrics

### Technical Metrics
- Query response time <2 seconds
- Dashboard load time <5 seconds
- 99.9% streaming success rate
- Zero data loss

### Business Metrics
- Replace Results tab completely
- Support 10+ concurrent clients
- Reduce time to insights from hours to seconds
- Enable self-service analytics

## Timeline

### Week 1 (Aug 19-23)
- [ ] Create BigQuery dataset and tables
- [ ] Implement streaming integration
- [ ] Test with existing data

### Week 2 (Aug 26-30)
- [ ] Create Looker Studio report
- [ ] Design 4 dashboard pages
- [ ] Add parameters and filters

### Week 3 (Sep 2-6)
- [ ] Embed in React app
- [ ] User access management
- [ ] Testing and refinement

### Week 4 (Sep 9-13)
- [ ] Deploy to production
- [ ] Migrate historical data
- [ ] Documentation and training

## Next Steps

1. **Get Approval**: Review plan with stakeholders
2. **Enable BigQuery API**: In contestra-ai GCP project
3. **Create Dataset**: Start with schema creation
4. **Prototype**: Build minimal streaming integration
5. **Iterate**: Refine based on initial usage

## Support Resources

- [BigQuery Streaming API](https://cloud.google.com/bigquery/docs/streaming-data-into-bigquery)
- [BigQuery Row-Level Security](https://cloud.google.com/bigquery/docs/row-level-security)
- [Looker Studio Parameters](https://support.google.com/looker-studio/answer/9002005)
- [Looker Studio Embedding](https://support.google.com/looker-studio/answer/7450231)

## Appendix: Sample Access Grants

```sql
-- Grant access to AVEA team
INSERT INTO `contestra-ai.ai_ranker.user_access` VALUES
  ('alice@avea-life.com', 'workspace_avea', 'view', CURRENT_TIMESTAMP(), 'admin@contestra.com'),
  ('bob@avea-life.com', 'workspace_avea', 'edit', CURRENT_TIMESTAMP(), 'admin@contestra.com');

-- Grant admin access to Contestra team  
INSERT INTO `contestra-ai.ai_ranker.user_access` VALUES
  ('l@contestra.com', 'workspace_avea', 'admin', CURRENT_TIMESTAMP(), 'system'),
  ('l@contestra.com', 'workspace_default', 'admin', CURRENT_TIMESTAMP(), 'system');
```

## Contact

For questions about this implementation plan, contact the AI Ranker development team.