'use client'

import { useState, useEffect } from 'react'
import { dashboardApi } from '@/lib/api'

interface WeeklyTrendChartProps {
  brandId: number
  phraseId: number
  phraseName: string
  vendor: string
}

export default function WeeklyTrendChart({ brandId, phraseId, phraseName, vendor }: WeeklyTrendChartProps) {
  const [weeklyData, setWeeklyData] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadWeeklyData()
  }, [brandId, phraseId, vendor])

  const loadWeeklyData = async () => {
    try {
      const data = await dashboardApi.getWeeklyTrends(brandId, phraseId)
      setWeeklyData(data)
    } catch (error) {
      console.error('Failed to load weekly trends:', error)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="h-64 bg-gray-100 animate-pulse rounded-lg flex items-center justify-center">
        <p className="text-gray-500">Loading trends...</p>
      </div>
    )
  }

  // Mock data for visualization
  const mockWeeks = ['Week 1', 'Week 2', 'Week 3', 'Week 4']
  const mockData = mockWeeks.map((week, index) => ({
    week,
    position: Math.floor(Math.random() * 5) + 1,
    mentioned: Math.random() > 0.3
  }))

  return (
    <div className="bg-white rounded-lg p-4">
      <h4 className="text-lg font-semibold mb-4">
        Weekly Trend: "{phraseName}"
      </h4>
      
      <div className="relative h-48">
        {/* Y-axis labels */}
        <div className="absolute left-0 top-0 bottom-0 w-8 flex flex-col justify-between text-xs text-gray-500">
          <span>1</span>
          <span>2</span>
          <span>3</span>
          <span>4</span>
          <span>5</span>
        </div>
        
        {/* Chart area */}
        <div className="ml-10 h-full border-l border-b border-gray-300 relative">
          {/* Data points */}
          <div className="absolute inset-0 flex items-end justify-around px-4">
            {mockData.map((data, index) => (
              <div key={index} className="flex flex-col items-center">
                <div 
                  className={`w-8 ${data.mentioned ? 'bg-green-500' : 'bg-gray-400'} rounded-t`}
                  style={{ height: `${(6 - data.position) * 20}%` }}
                />
                <span className="text-xs mt-2">{data.week}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
      
      <div className="mt-4 flex items-center justify-between text-sm">
        <div className="flex items-center">
          <div className="w-3 h-3 bg-green-500 rounded mr-2"></div>
          <span>Brand Mentioned</span>
        </div>
        <div className="flex items-center">
          <div className="w-3 h-3 bg-gray-400 rounded mr-2"></div>
          <span>Not Mentioned</span>
        </div>
      </div>
    </div>
  )
}