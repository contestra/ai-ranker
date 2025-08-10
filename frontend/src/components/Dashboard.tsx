'use client'

import { useState, useEffect } from 'react'
import { DashboardData, TrendData } from '@/types'
import { dashboardApi } from '@/lib/api'
import ScoreCard from './ScoreCard'
import TrendChart from './TrendChart'
import CompetitorComparison from './CompetitorComparison'
import GroundedGapAnalysis from './GroundedGapAnalysis'

interface DashboardProps {
  brandId: number
}

export default function Dashboard({ brandId }: DashboardProps) {
  const [overview, setOverview] = useState<DashboardData | null>(null)
  const [trends, setTrends] = useState<TrendData[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadDashboardData()
  }, [brandId])

  const loadDashboardData = async () => {
    setLoading(true)
    try {
      const [overviewData, trendsData] = await Promise.all([
        dashboardApi.getOverview(brandId),
        dashboardApi.getTrends(brandId, 30)
      ])
      setOverview(overviewData)
      setTrends(trendsData)
    } catch (error) {
      console.error('Failed to load dashboard data:', error)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-32 bg-gray-200 animate-pulse rounded-lg"></div>
          ))}
        </div>
      </div>
    )
  }

  if (!overview) {
    return <div>No data available</div>
  }

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <ScoreCard
          title="Representation Score"
          value={overview.representation_score}
          format="percentage"
          trend={overview.trend}
        />
        <ScoreCard
          title="Mention Rate"
          value={overview.mention_rate}
          format="percentage"
          confidence={overview.confidence_interval}
        />
        <ScoreCard
          title="Average Rank"
          value={overview.avg_rank}
          format="rank"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white p-6 rounded-lg shadow">
          <h2 className="text-lg font-semibold mb-4">Trend Analysis</h2>
          <TrendChart data={trends} />
        </div>
        
        <div className="bg-white p-6 rounded-lg shadow">
          <h2 className="text-lg font-semibold mb-4">Competitor Comparison</h2>
          <CompetitorComparison brandId={brandId} />
        </div>
      </div>

      <div className="bg-white p-6 rounded-lg shadow">
        <h2 className="text-lg font-semibold mb-4">Grounded vs Ungrounded Gap</h2>
        <GroundedGapAnalysis brandId={brandId} />
      </div>
    </div>
  )
}