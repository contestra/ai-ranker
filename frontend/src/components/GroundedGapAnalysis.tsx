'use client'

import { useState, useEffect } from 'react'
import { dashboardApi } from '@/lib/api'

interface GroundedGapAnalysisProps {
  brandId: number
}

export default function GroundedGapAnalysis({ brandId }: GroundedGapAnalysisProps) {
  const [gapData, setGapData] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadGapData()
  }, [brandId])

  const loadGapData = async () => {
    try {
      const data = await dashboardApi.getGroundedGap(brandId)
      setGapData(data)
    } catch (error) {
      console.error('Failed to load gap data:', error)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return <div className="h-32 bg-gray-100 animate-pulse rounded"></div>
  }

  if (!gapData) {
    return <div className="text-gray-500">No gap analysis data available</div>
  }

  const gapPercentage = Math.abs(gapData.gap * 100)
  const isPositiveGap = gapData.gap > 0

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <div>
          <p className="text-sm text-gray-500">Grounded Mode</p>
          <p className="text-2xl font-semibold">{(gapData.grounded_rate * 100).toFixed(1)}%</p>
        </div>
        <div>
          <p className="text-sm text-gray-500">Ungrounded Mode</p>
          <p className="text-2xl font-semibold">{(gapData.ungrounded_rate * 100).toFixed(1)}%</p>
        </div>
      </div>
      
      <div className="border-t pt-4">
        <div className="flex items-center justify-between">
          <span className="text-sm font-medium text-gray-700">Gap</span>
          <span className={`text-lg font-semibold ${
            isPositiveGap ? 'text-green-600' : 'text-red-600'
          }`}>
            {isPositiveGap ? '+' : '-'}{gapPercentage.toFixed(1)}%
          </span>
        </div>
        
        <div className="mt-2 bg-gray-200 rounded-full h-2">
          <div
            className={`h-2 rounded-full ${
              isPositiveGap ? 'bg-green-500' : 'bg-red-500'
            }`}
            style={{ width: `${Math.min(gapPercentage * 2, 100)}%` }}
          />
        </div>
      </div>
      
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mt-4">
        <p className="text-sm font-semibold text-blue-900">Recommendation</p>
        <p className="text-sm text-blue-700 mt-1">{gapData.recommendation}</p>
      </div>
    </div>
  )
}