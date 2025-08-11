'use client'

import { useState, useEffect } from 'react'
import { LineChart, Line, BarChart, Bar, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, AreaChart, Area } from 'recharts'
import { CalendarIcon, ArrowUpIcon, ArrowDownIcon, ChartBarIcon } from '@heroicons/react/24/outline'
import { format, subDays, startOfDay, endOfDay } from 'date-fns'

interface DailyStat {
  date: string
  total_hits: number
  bot_hits: number
  human_hits: number
  on_demand_hits: number
  indexing_hits: number
  training_hits: number
  bot_percentage: number
  top_bot: string | null
  top_provider: string | null
}

interface BotBreakdown {
  name: string
  hits: number
}

interface ProviderBreakdown {
  provider: string
  hits: number
}

const COLORS = ['#10B981', '#3B82F6', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899', '#14B8A6', '#F97316']

export default function BotAnalytics({ domainId, domainUrl }: { domainId: number, domainUrl: string }) {
  const [dailyStats, setDailyStats] = useState<DailyStat[]>([])
  const [botBreakdown, setBotBreakdown] = useState<BotBreakdown[]>([])
  const [providerBreakdown, setProviderBreakdown] = useState<ProviderBreakdown[]>([])
  const [hourlyPattern, setHourlyPattern] = useState<number[]>([])
  const [dateRange, setDateRange] = useState(7) // Default to 7 days
  const [loading, setLoading] = useState(true)
  const [aggregating, setAggregating] = useState(false)

  useEffect(() => {
    if (domainId) {
      loadAnalytics()
    }
  }, [domainId, dateRange])

  const loadAnalytics = async () => {
    setLoading(true)
    try {
      // Load daily stats
      const dailyResponse = await fetch(
        `http://localhost:8000/api/bot-analytics/domains/${domainId}/daily-stats?days=${dateRange}`
      )
      if (dailyResponse.ok) {
        const data = await dailyResponse.json()
        setDailyStats(data.stats)
      }

      // Load bot breakdown
      const breakdownResponse = await fetch(
        `http://localhost:8000/api/bot-analytics/domains/${domainId}/bot-breakdown?days=${dateRange}`
      )
      if (breakdownResponse.ok) {
        const data = await breakdownResponse.json()
        setBotBreakdown(data.top_bots.slice(0, 8))
        setProviderBreakdown(data.by_provider)
      }

      // Load hourly pattern
      const hourlyResponse = await fetch(
        `http://localhost:8000/api/bot-analytics/domains/${domainId}/hourly-pattern?days=${dateRange}`
      )
      if (hourlyResponse.ok) {
        const data = await hourlyResponse.json()
        setHourlyPattern(data.hourly_pattern)
      }
    } catch (error) {
      console.error('Failed to load analytics:', error)
    } finally {
      setLoading(false)
    }
  }

  const triggerAggregation = async () => {
    setAggregating(true)
    try {
      const response = await fetch(
        `http://localhost:8000/api/bot-analytics/domains/${domainId}/aggregate-stats`,
        { method: 'POST' }
      )
      if (response.ok) {
        // Reload analytics after aggregation
        setTimeout(() => {
          loadAnalytics()
        }, 2000)
      }
    } catch (error) {
      console.error('Failed to trigger aggregation:', error)
    } finally {
      setAggregating(false)
    }
  }

  // Calculate summary metrics
  const totalBotHits = dailyStats.reduce((sum, stat) => sum + stat.bot_hits, 0)
  const totalHumanHits = dailyStats.reduce((sum, stat) => sum + stat.human_hits, 0)
  const avgDailyBots = totalBotHits / Math.max(dailyStats.length, 1)
  const avgBotPercentage = dailyStats.reduce((sum, stat) => sum + stat.bot_percentage, 0) / Math.max(dailyStats.length, 1)

  // Calculate trend (compare last 2 periods)
  const midPoint = Math.floor(dailyStats.length / 2)
  const firstHalf = dailyStats.slice(0, midPoint).reduce((sum, stat) => sum + stat.bot_hits, 0)
  const secondHalf = dailyStats.slice(midPoint).reduce((sum, stat) => sum + stat.bot_hits, 0)
  const trend = firstHalf > 0 ? ((secondHalf - firstHalf) / firstHalf) * 100 : 0

  // Format hourly data for chart
  const hourlyData = hourlyPattern.map((hits, hour) => ({
    hour: `${hour}:00`,
    hits
  }))

  // Format data for bot type chart
  const botTypeData = dailyStats.length > 0 ? [
    { name: 'Live Queries', value: dailyStats.reduce((sum, s) => sum + s.on_demand_hits, 0) },
    { name: 'Indexing', value: dailyStats.reduce((sum, s) => sum + s.indexing_hits, 0) },
    { name: 'Training', value: dailyStats.reduce((sum, s) => sum + s.training_hits, 0) }
  ].filter(d => d.value > 0) : []

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Loading analytics...</div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header with date range selector */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">Bot Traffic Analytics</h3>
          <p className="text-sm text-gray-500">Historical data for {domainUrl}</p>
        </div>
        <div className="flex items-center space-x-4">
          <button
            onClick={triggerAggregation}
            disabled={aggregating}
            className="px-3 py-1.5 bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200 text-sm disabled:opacity-50"
          >
            {aggregating ? 'Aggregating...' : 'Refresh Data'}
          </button>
          <div className="flex items-center space-x-2">
            <CalendarIcon className="h-5 w-5 text-gray-400" />
            <select
              value={dateRange}
              onChange={(e) => setDateRange(Number(e.target.value))}
              className="px-3 py-1.5 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value={7}>Last 7 days</option>
              <option value={14}>Last 14 days</option>
              <option value={30}>Last 30 days</option>
              <option value={60}>Last 60 days</option>
              <option value={90}>Last 90 days</option>
            </select>
          </div>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-lg shadow p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">Total Bot Hits</p>
              <p className="text-2xl font-bold text-gray-900">{totalBotHits.toLocaleString()}</p>
              <p className="text-xs text-gray-500 mt-1">Avg {avgDailyBots.toFixed(0)}/day</p>
            </div>
            <ChartBarIcon className="h-8 w-8 text-indigo-400" />
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">Bot Percentage</p>
              <p className="text-2xl font-bold text-indigo-600">{avgBotPercentage.toFixed(1)}%</p>
              <p className="text-xs text-gray-500 mt-1">of total traffic</p>
            </div>
            <div className="text-indigo-400">
              <svg className="h-8 w-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">Human Traffic</p>
              <p className="text-2xl font-bold text-gray-900">{totalHumanHits.toLocaleString()}</p>
              <p className="text-xs text-gray-500 mt-1">Non-bot visits</p>
            </div>
            <div className="text-gray-400">
              <svg className="h-8 w-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
              </svg>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">Trend</p>
              <div className="flex items-center">
                <p className="text-2xl font-bold text-gray-900">{Math.abs(trend).toFixed(1)}%</p>
                {trend > 0 ? (
                  <ArrowUpIcon className="h-5 w-5 text-green-500 ml-2" />
                ) : trend < 0 ? (
                  <ArrowDownIcon className="h-5 w-5 text-red-500 ml-2" />
                ) : null}
              </div>
              <p className="text-xs text-gray-500 mt-1">vs previous period</p>
            </div>
            <div className="text-gray-400">
              <svg className="h-8 w-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4h16v12a1 1 0 01-1 1H5a1 1 0 01-1-1V4z" />
              </svg>
            </div>
          </div>
        </div>
      </div>

      {/* Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Traffic Over Time */}
        <div className="bg-white rounded-lg shadow p-4">
          <h4 className="text-sm font-semibold text-gray-900 mb-4">Traffic Over Time</h4>
          <ResponsiveContainer width="100%" height={250}>
            <AreaChart data={dailyStats}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis 
                dataKey="date" 
                tickFormatter={(date) => format(new Date(date), 'MMM dd')}
              />
              <YAxis />
              <Tooltip 
                labelFormatter={(date) => format(new Date(date), 'MMM dd, yyyy')}
              />
              <Legend />
              <Area type="monotone" dataKey="bot_hits" stackId="1" stroke="#3B82F6" fill="#3B82F6" name="Bot Traffic" />
              <Area type="monotone" dataKey="human_hits" stackId="1" stroke="#10B981" fill="#10B981" name="Human Traffic" />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Bot Type Distribution */}
        <div className="bg-white rounded-lg shadow p-4">
          <h4 className="text-sm font-semibold text-gray-900 mb-4">Bot Type Distribution</h4>
          <ResponsiveContainer width="100%" height={250}>
            {botTypeData.length > 0 ? (
              <PieChart>
                <Pie
                  data={botTypeData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {botTypeData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            ) : (
              <div className="flex items-center justify-center h-full text-gray-500">
                No bot type data available
              </div>
            )}
          </ResponsiveContainer>
        </div>

        {/* Top Bots */}
        <div className="bg-white rounded-lg shadow p-4">
          <h4 className="text-sm font-semibold text-gray-900 mb-4">Top AI Bots</h4>
          <ResponsiveContainer width="100%" height={250}>
            {botBreakdown.length > 0 ? (
              <BarChart data={botBreakdown} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis type="number" />
                <YAxis dataKey="name" type="category" width={100} />
                <Tooltip />
                <Bar dataKey="hits" fill="#3B82F6" />
              </BarChart>
            ) : (
              <div className="flex items-center justify-center h-full text-gray-500">
                No bot data available
              </div>
            )}
          </ResponsiveContainer>
        </div>

        {/* Hourly Pattern */}
        <div className="bg-white rounded-lg shadow p-4">
          <h4 className="text-sm font-semibold text-gray-900 mb-4">24-Hour Activity Pattern</h4>
          <ResponsiveContainer width="100%" height={250}>
            {hourlyData.length > 0 ? (
              <LineChart data={hourlyData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="hour" />
                <YAxis />
                <Tooltip />
                <Line type="monotone" dataKey="hits" stroke="#3B82F6" strokeWidth={2} dot={false} />
              </LineChart>
            ) : (
              <div className="flex items-center justify-center h-full text-gray-500">
                No hourly data available
              </div>
            )}
          </ResponsiveContainer>
        </div>
      </div>

      {/* Provider Breakdown */}
      {providerBreakdown.length > 0 && (
        <div className="bg-white rounded-lg shadow p-4">
          <h4 className="text-sm font-semibold text-gray-900 mb-4">AI Provider Breakdown</h4>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {providerBreakdown.map((provider, index) => (
              <div key={provider.provider} className="text-center">
                <div className="text-2xl font-bold" style={{ color: COLORS[index % COLORS.length] }}>
                  {provider.hits.toLocaleString()}
                </div>
                <div className="text-sm text-gray-600 capitalize">{provider.provider}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}