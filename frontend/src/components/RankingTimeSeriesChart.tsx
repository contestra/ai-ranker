'use client'

import { useEffect, useState } from 'react'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  ChartOptions,
} from 'chart.js'
import { Line } from 'react-chartjs-2'

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
)

interface DataPoint {
  week_start: string
  rank: number
  frequency: number
}

interface SeriesData {
  entity?: string
  brand?: string
  data_points: DataPoint[]
  total_frequency: number
  avg_rank: number
  variance: number
}

interface RankingTimeSeriesChartProps {
  title: string
  description?: string
  seriesData: SeriesData[]
  height?: number
  showWeeklyView?: boolean
}

// Color palette similar to Dejan.ai
const COLORS = [
  '#FF6B6B', // Red
  '#4ECDC4', // Teal
  '#45B7D1', // Blue
  '#FFA07A', // Light Salmon
  '#98D8C8', // Mint
  '#F7DC6F', // Yellow
  '#BB8FCE', // Purple
  '#85C1E2', // Light Blue
  '#F8B739', // Orange
  '#82E0AA', // Green
]

export default function RankingTimeSeriesChart({
  title,
  description,
  seriesData,
  height = 300,
  showWeeklyView = true,
}: RankingTimeSeriesChartProps) {
  const [chartData, setChartData] = useState<any>(null)

  useEffect(() => {
    if (!seriesData || seriesData.length === 0) return

    // Get all unique weeks
    const allWeeks = new Set<string>()
    seriesData.forEach(series => {
      series.data_points.forEach(point => {
        allWeeks.add(point.week_start)
      })
    })
    
    // Sort weeks chronologically
    const sortedWeeks = Array.from(allWeeks).sort()
    
    // Format week labels
    const labels = sortedWeeks.map(week => {
      const date = new Date(week)
      return date.toLocaleDateString('en-US', { 
        month: 'short', 
        day: 'numeric',
        year: 'numeric'
      })
    })

    // Create datasets
    const datasets = seriesData.slice(0, 10).map((series, index) => {
      const name = series.entity || series.brand || 'Unknown'
      const data = sortedWeeks.map(week => {
        const point = series.data_points.find(p => p.week_start === week)
        return point ? point.rank : null
      })

      return {
        label: `${name} (freq: ${series.total_frequency}, var: ${series.variance})`,
        data: data,
        borderColor: COLORS[index % COLORS.length],
        backgroundColor: COLORS[index % COLORS.length] + '20',
        borderWidth: 2,
        pointRadius: 4,
        pointHoverRadius: 6,
        tension: 0.2,
        spanGaps: true,
      }
    })

    setChartData({
      labels,
      datasets,
    })
  }, [seriesData])

  const options: ChartOptions<'line'> = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'bottom' as const,
        labels: {
          boxWidth: 12,
          padding: 15,
          font: {
            size: 11,
          },
        },
      },
      title: {
        display: !!title,
        text: title,
        font: {
          size: 14,
          weight: 'bold',
        },
      },
      tooltip: {
        mode: 'index' as const,
        intersect: false,
        callbacks: {
          label: (context) => {
            const label = context.dataset.label || ''
            const value = context.parsed.y
            const dataIndex = context.dataIndex
            const series = seriesData[context.datasetIndex]
            const frequency = series?.data_points[dataIndex]?.frequency || 0
            
            return `${label.split(' (')[0]}: Rank #${value} (freq: ${frequency})`
          },
        },
      },
    },
    scales: {
      x: {
        grid: {
          display: true,
          color: 'rgba(0, 0, 0, 0.05)',
        },
        title: {
          display: true,
          text: 'Week Starting',
          font: {
            size: 11,
          },
        },
      },
      y: {
        reverse: true, // Inverted scale - rank 1 at top
        min: 1,
        max: 10,
        ticks: {
          stepSize: 1,
          callback: function(value) {
            return '#' + value
          },
        },
        grid: {
          display: true,
          color: 'rgba(0, 0, 0, 0.05)',
        },
        title: {
          display: true,
          text: 'Rank Position',
          font: {
            size: 11,
          },
        },
      },
    },
  }

  if (!chartData) {
    return (
      <div className="flex items-center justify-center" style={{ height }}>
        <div className="text-gray-400">
          <svg className="animate-spin h-8 w-8 mx-auto mb-2" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          <p className="text-sm">Loading chart data...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-lg">
      {description && (
        <p className="text-sm text-gray-600 mb-3">{description}</p>
      )}
      <div style={{ height }}>
        <Line data={chartData} options={options} />
      </div>
    </div>
  )
}