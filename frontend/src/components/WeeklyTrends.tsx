'use client'

import { useState, useEffect } from 'react'
import { Line } from 'react-chartjs-2'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  ChartOptions
} from 'chart.js'

// Register Chart.js components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
)

interface WeeklyDataPoint {
  week_start: string
  rank: number
  frequency: number
  variance?: number
}

interface EntityTracking {
  entity: string
  data_points: WeeklyDataPoint[]
  total_frequency: number
  avg_rank: number
  variance: number
}

interface BrandTracking {
  brand: string
  data_points: WeeklyDataPoint[]
  total_frequency: number
  avg_rank: number
  variance: number
}

interface WeeklyTrackingResponse {
  brand_name: string
  vendor: string
  entity_tracking: EntityTracking[]
  phrase_tracking: Record<string, BrandTracking[]>
}

interface WeeklyTrendsProps {
  brandId: number
  brandName: string
  vendor: string
}

export default function WeeklyTrends({ brandId, brandName, vendor }: WeeklyTrendsProps) {
  const [trackingData, setTrackingData] = useState<WeeklyTrackingResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [selectedView, setSelectedView] = useState<'entities' | 'brands'>('entities')
  const [selectedPhrase, setSelectedPhrase] = useState<string>('')

  const fetchTrackingData = async () => {
    setLoading(true)
    setError('')
    
    try {
      const response = await fetch(
        `http://localhost:8000/api/weekly-tracking/${encodeURIComponent(brandName)}/${vendor}`
      )
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }
      
      const data = await response.json()
      setTrackingData(data)
      
      // Set first phrase as selected if available
      if (data.phrase_tracking && Object.keys(data.phrase_tracking).length > 0) {
        setSelectedPhrase(Object.keys(data.phrase_tracking)[0])
      }
    } catch (err: any) {
      setError(`Failed to fetch tracking data: ${err.message}`)
    } finally {
      setLoading(false)
    }
  }

  const generateSampleData = async () => {
    setLoading(true)
    setError('')
    
    try {
      const response = await fetch(
        'http://localhost:8000/api/weekly-tracking/generate-sample',
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            brand_name: brandName,
            vendor: vendor
          })
        }
      )
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }
      
      // Fetch the generated data
      await fetchTrackingData()
    } catch (err: any) {
      setError(`Failed to generate sample data: ${err.message}`)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (brandName && vendor) {
      fetchTrackingData()
    }
  }, [brandName, vendor])

  // Prepare chart data for entities
  const getEntityChartData = () => {
    if (!trackingData || !trackingData.entity_tracking || trackingData.entity_tracking.length === 0) {
      console.log('No tracking data available')
      return null
    }

    // Get all unique weeks
    const allWeeks = new Set<string>()
    trackingData.entity_tracking.forEach(entity => {
      if (entity.data_points && Array.isArray(entity.data_points)) {
        entity.data_points.forEach(point => {
          if (point.week_start) {
            allWeeks.add(point.week_start)
          }
        })
      }
    })
    const weeks = Array.from(allWeeks).sort()

    if (weeks.length === 0) {
      console.log('No weeks data found')
      return null
    }

    // Colors for different lines
    const colors = [
      'rgb(99, 102, 241)',   // Indigo
      'rgb(236, 72, 153)',   // Pink
      'rgb(34, 197, 94)',    // Green
      'rgb(251, 146, 60)',   // Orange
      'rgb(147, 51, 234)',   // Purple
      'rgb(14, 165, 233)',   // Sky
      'rgb(251, 191, 36)',   // Amber
      'rgb(239, 68, 68)',    // Red
    ]

    const datasets = trackingData.entity_tracking
      .filter(entity => entity.entity && entity.entity.trim() !== '') // Filter out empty entities
      .slice(0, 8)
      .map((entity, index) => {
        const data = weeks.map(week => {
          const point = entity.data_points.find(p => p.week_start === week)
          // Invert rank for better visualization (1 = top, so show as 10)
          return point ? (11 - point.rank) : null
        })

        return {
          label: entity.entity || `Entity ${index + 1}`,
          data: data,
          borderColor: colors[index % colors.length],
          backgroundColor: colors[index % colors.length] + '20',
          tension: 0.3,
          pointRadius: 4,
          pointHoverRadius: 6
        }
      })

    return {
      labels: weeks.map(w => {
        const date = new Date(w)
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
      }),
      datasets: datasets
    }
  }

  // Prepare chart data for brands
  const getBrandChartData = () => {
    if (!trackingData || !selectedPhrase || !trackingData.phrase_tracking[selectedPhrase]) {
      return null
    }

    const brandsData = trackingData.phrase_tracking[selectedPhrase]
    
    // Get all unique weeks
    const allWeeks = new Set<string>()
    brandsData.forEach(brand => {
      brand.data_points.forEach(point => {
        allWeeks.add(point.week_start)
      })
    })
    const weeks = Array.from(allWeeks).sort()

    // Colors for different lines
    const colors = [
      'rgb(99, 102, 241)',   // Indigo
      'rgb(236, 72, 153)',   // Pink
      'rgb(34, 197, 94)',    // Green
      'rgb(251, 146, 60)',   // Orange
      'rgb(147, 51, 234)',   // Purple
    ]

    const datasets = brandsData.slice(0, 5).map((brand, index) => {
      const data = weeks.map(week => {
        const point = brand.data_points.find(p => p.week_start === week)
        // Invert rank for better visualization (1 = top, so show as 10)
        return point ? (11 - point.rank) : null
      })

      const isYourBrand = brand.brand.toLowerCase() === brandName.toLowerCase()
      
      return {
        label: brand.brand,
        data: data,
        borderColor: isYourBrand ? 'rgb(99, 102, 241)' : colors[(index + 1) % colors.length],
        backgroundColor: isYourBrand ? 'rgb(99, 102, 241, 0.2)' : colors[(index + 1) % colors.length] + '20',
        borderWidth: isYourBrand ? 3 : 2,
        tension: 0.3
      }
    })

    return {
      labels: weeks.map(w => {
        const date = new Date(w)
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
      }),
      datasets: datasets
    }
  }

  const chartOptions: ChartOptions<'line'> = {
    responsive: true,
    plugins: {
      legend: {
        position: 'top' as const,
      },
      title: {
        display: true,
        text: selectedView === 'entities' 
          ? 'Entity Ranking Trends (Higher is Better)'
          : `Brand Rankings for "${selectedPhrase}"`
      },
      tooltip: {
        callbacks: {
          label: (context) => {
            const rank = context.parsed.y ? (11 - context.parsed.y) : 'N/A'
            return `${context.dataset.label}: Rank #${rank}`
          }
        }
      }
    },
    scales: {
      y: {
        beginAtZero: true,
        max: 10,
        ticks: {
          stepSize: 1,
          callback: function(value) {
            // Invert the display (10 shows as 1, 9 as 2, etc.)
            return `#${11 - Number(value)}`
          }
        },
        title: {
          display: true,
          text: 'Ranking Position'
        }
      },
      x: {
        title: {
          display: true,
          text: 'Week Starting'
        }
      }
    }
  }

  const entityChartData = getEntityChartData()
  const brandChartData = getBrandChartData()

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-bold text-gray-900">Weekly Trends</h2>
          <div className="flex space-x-3">
            {!trackingData && (
              <button
                onClick={generateSampleData}
                disabled={loading}
                className="px-4 py-2 bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200 disabled:bg-gray-300"
              >
                Generate Sample Data
              </button>
            )}
            <button
              onClick={fetchTrackingData}
              disabled={loading}
              className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 disabled:bg-gray-400"
            >
              {loading ? 'Loading...' : 'Refresh'}
            </button>
          </div>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-red-50 text-red-700 rounded-lg">{error}</div>
        )}

        {trackingData && (
          <>
            {/* View Toggle */}
            <div className="flex space-x-4 mb-6">
              <button
                onClick={() => setSelectedView('entities')}
                className={`px-4 py-2 rounded-md ${
                  selectedView === 'entities'
                    ? 'bg-indigo-600 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                Entity Trends
              </button>
              <button
                onClick={() => setSelectedView('brands')}
                className={`px-4 py-2 rounded-md ${
                  selectedView === 'brands'
                    ? 'bg-indigo-600 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                Brand Competition
              </button>
            </div>

            {/* Phrase Selector for Brand View */}
            {selectedView === 'brands' && trackingData.phrase_tracking && (
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Select Tracked Phrase
                </label>
                <select
                  value={selectedPhrase}
                  onChange={(e) => setSelectedPhrase(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
                >
                  {Object.keys(trackingData.phrase_tracking).map(phrase => (
                    <option key={phrase} value={phrase}>{phrase}</option>
                  ))}
                </select>
              </div>
            )}

            {/* Chart */}
            <div className="bg-gray-50 p-4 rounded-lg">
              {selectedView === 'entities' && entityChartData ? (
                <Line data={entityChartData} options={chartOptions} />
              ) : selectedView === 'brands' && brandChartData ? (
                <Line data={brandChartData} options={chartOptions} />
              ) : (
                <div className="text-center py-8 text-gray-500">
                  No tracking data available yet. Run analyses to generate data points.
                </div>
              )}
            </div>

            {/* Statistics */}
            <div className="mt-6 grid grid-cols-1 md:grid-cols-3 gap-4">
              {selectedView === 'entities' && trackingData?.entity_tracking?.slice(0, 3).map(entity => (
                <div key={entity.entity} className="bg-gray-50 rounded-lg p-4">
                  <h4 className="font-medium text-gray-900">{entity.entity || 'Unknown'}</h4>
                  <div className="mt-2 space-y-1 text-sm">
                    <div className="flex justify-between">
                      <span className="text-gray-500">Avg Rank:</span>
                      <span className="font-medium">#{entity.avg_rank?.toFixed(1) || 'N/A'}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-500">Variance:</span>
                      <span className="font-medium">{entity.variance?.toFixed(2) || 'N/A'}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-500">Frequency:</span>
                      <span className="font-medium">{entity.total_frequency || 0}</span>
                    </div>
                  </div>
                </div>
              ))}
              
              {selectedView === 'brands' && selectedPhrase && trackingData?.phrase_tracking?.[selectedPhrase]?.slice(0, 3).map(brand => (
                <div key={brand.brand} className={`rounded-lg p-4 ${
                  brand.brand.toLowerCase() === brandName.toLowerCase() 
                    ? 'bg-indigo-50 border-2 border-indigo-200' 
                    : 'bg-gray-50'
                }`}>
                  <h4 className="font-medium text-gray-900">{brand.brand}</h4>
                  <div className="mt-2 space-y-1 text-sm">
                    <div className="flex justify-between">
                      <span className="text-gray-500">Avg Rank:</span>
                      <span className="font-medium">#{brand.avg_rank.toFixed(1)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-500">Variance:</span>
                      <span className="font-medium">{brand.variance.toFixed(2)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-500">Mentions:</span>
                      <span className="font-medium">{brand.total_frequency}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  )
}