export interface Brand {
  id: number
  name: string
  domain?: string
  wikidata_qid?: string
  aliases: string[]
  category: string[]
}

export interface Experiment {
  id: number
  title: string
  description?: string
  created_at: string
}

export interface Metric {
  id: number
  run_id: number
  brand_id: number
  concept_id?: number
  mention_rate: number
  avg_rank?: number
  weighted_score: number
  ci_low: number
  ci_high: number
}

export interface DashboardData {
  representation_score: number
  mention_rate: number
  avg_rank?: number
  confidence_interval: [number, number]
  trend: 'up' | 'down' | 'stable'
}

export interface TrendData {
  date: string
  mention_rate: number
  weighted_score: number
}