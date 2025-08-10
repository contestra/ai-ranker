'use client'

import { useState, useEffect } from 'react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { dashboardApi } from '@/lib/api'

interface CompetitorComparisonProps {
  brandId: number
}

export default function CompetitorComparison({ brandId }: CompetitorComparisonProps) {
  const [competitors, setCompetitors] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadCompetitors()
  }, [brandId])

  const loadCompetitors = async () => {
    try {
      const data = await dashboardApi.getCompetitors(brandId)
      setCompetitors(data.map((c: any) => ({
        ...c,
        mention_rate: c.mention_rate * 100,
        weighted_score: c.weighted_score * 100,
      })))
    } catch (error) {
      console.error('Failed to load competitors:', error)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return <div className="h-64 bg-gray-100 animate-pulse rounded"></div>
  }

  if (competitors.length === 0) {
    return <div className="text-gray-500 text-center py-8">No competitor data available</div>
  }

  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={competitors}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="brand_name" />
        <YAxis />
        <Tooltip />
        <Legend />
        <Bar dataKey="weighted_score" fill="#8884d8" name="Weighted Score (%)" />
        <Bar dataKey="mention_rate" fill="#82ca9d" name="Mention Rate (%)" />
      </BarChart>
    </ResponsiveContainer>
  )
}