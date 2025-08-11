'use client'

import { useState, useEffect } from 'react'

interface ComparisonViewProps {
  brandId: number
  brandName: string
}

interface EntityData {
  entity: string
  frequency: number
  avg_position: number
  weighted_score: number
  variants?: string[]
}

interface ComparisonData {
  ungrounded: {
    entities: EntityData[]
    metadata: any
  }
  grounded: {
    entities: EntityData[]
    metadata: any
  }
}

export default function ComparisonView({ brandId, brandName }: ComparisonViewProps) {
  const [comparisonData, setComparisonData] = useState<ComparisonData | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    const loadComparisonData = () => {
      const ungroundedData = localStorage.getItem(`google_ungrounded_${brandName}`)
      const groundedData = localStorage.getItem(`google_grounded_${brandName}`)
      
      if (ungroundedData && groundedData) {
        setComparisonData({
          ungrounded: JSON.parse(ungroundedData),
          grounded: JSON.parse(groundedData)
        })
      }
    }
    
    // Initial load
    loadComparisonData()
    
    // Listen for comparison complete event
    const handleComparisonComplete = (event: any) => {
      if (event.detail.brandName === brandName) {
        loadComparisonData()
      }
    }
    
    window.addEventListener('comparisonComplete', handleComparisonComplete)
    
    return () => {
      window.removeEventListener('comparisonComplete', handleComparisonComplete)
    }
  }, [brandName])

  const getScoreColor = (score: number) => {
    const opacity = Math.min(score * 2, 1)
    return `rgba(59, 130, 246, ${opacity})`
  }

  const calculateOverlap = () => {
    if (!comparisonData) return { count: 0, percentage: 0 }
    
    const ungroundedSet = new Set(comparisonData.ungrounded.entities.map(e => e.entity.toLowerCase()))
    const groundedSet = new Set(comparisonData.grounded.entities.map(e => e.entity.toLowerCase()))
    
    const overlap = [...ungroundedSet].filter(e => groundedSet.has(e))
    const percentage = Math.round((overlap.length / Math.max(ungroundedSet.size, groundedSet.size)) * 100)
    
    return { count: overlap.length, percentage }
  }

  if (!comparisonData) {
    return (
      <div className="space-y-6">
        <div>
          <h2 className="text-2xl font-bold text-gray-900 mb-2">Grounded vs Ungrounded Comparison</h2>
          <p className="text-gray-600">
            Compare how Google Gemini responds with and without grounding (web search).
          </p>
        </div>
        
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div className="flex">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-blue-400" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="ml-3">
              <h3 className="text-sm font-medium text-blue-800">No Comparison Data Available</h3>
              <div className="mt-2 text-sm text-blue-700">
                <p>To see grounded vs ungrounded comparison:</p>
                <ol className="list-decimal list-inside mt-2">
                  <li>Go to the Settings tab</li>
                  <li>Enter your brand name and tracked phrases</li>
                  <li>Click <strong>"Compare Grounded vs Ungrounded (Google)"</strong></li>
                </ol>
              </div>
            </div>
          </div>
        </div>
      </div>
    )
  }

  const overlap = calculateOverlap()

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-gray-900 mb-2">Grounded vs Ungrounded Comparison</h2>
        <p className="text-gray-600">
          Google Gemini results with and without web grounding for {brandName}
        </p>
        
        {/* Overlap Metrics */}
        <div className="mt-4 grid grid-cols-3 gap-4">
          <div className="bg-white rounded-lg shadow p-4">
            <div className="text-sm text-gray-500">Ungrounded Entities</div>
            <div className="text-2xl font-bold text-gray-900">{comparisonData.ungrounded.entities.length}</div>
          </div>
          <div className="bg-white rounded-lg shadow p-4">
            <div className="text-sm text-gray-500">Grounded Entities</div>
            <div className="text-2xl font-bold text-gray-900">{comparisonData.grounded.entities.length}</div>
          </div>
          <div className="bg-white rounded-lg shadow p-4">
            <div className="text-sm text-gray-500">Overlap</div>
            <div className="text-2xl font-bold text-indigo-600">{overlap.percentage}%</div>
            <div className="text-xs text-gray-500">{overlap.count} shared entities</div>
          </div>
        </div>
      </div>

      {/* Side-by-side comparison */}
      <div className="grid grid-cols-2 gap-6">
        {/* Ungrounded Results */}
        <div className="bg-white rounded-lg shadow">
          <div className="px-6 py-4 border-b bg-gray-50">
            <h3 className="text-lg font-semibold">Ungrounded (Naked Token)</h3>
            <p className="text-sm text-gray-500 mt-1">Pure AI associations without web search</p>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">#</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Entity</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Freq</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Pos</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Score</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {comparisonData.ungrounded.entities.slice(0, 15).map((entity, index) => {
                  const isInGrounded = comparisonData.grounded.entities.some(
                    g => g.entity.toLowerCase() === entity.entity.toLowerCase()
                  )
                  return (
                    <tr key={index} className={`hover:bg-gray-50 ${!isInGrounded ? 'bg-red-50' : ''}`}>
                      <td className="px-4 py-2 text-sm text-gray-500">{index + 1}</td>
                      <td className="px-4 py-2 text-sm font-medium text-gray-900">
                        {entity.entity}
                        {entity.variants && entity.variants.length > 1 && (
                          <span className="ml-1 text-xs text-gray-500">({entity.variants.length} var.)</span>
                        )}
                        {!isInGrounded && (
                          <span className="ml-2 text-xs bg-red-100 text-red-800 px-1 rounded">unique</span>
                        )}
                      </td>
                      <td className="px-4 py-2 text-sm text-gray-500">{entity.frequency}</td>
                      <td className="px-4 py-2 text-sm text-gray-500">{entity.avg_position.toFixed(1)}</td>
                      <td className="px-4 py-2 text-sm text-gray-500">
                        <div className="flex items-center">
                          <div className="w-12 h-2 bg-gray-200 rounded-full overflow-hidden">
                            <div
                              className="h-full rounded-full"
                              style={{
                                width: `${entity.weighted_score * 100}%`,
                                backgroundColor: getScoreColor(entity.weighted_score)
                              }}
                            />
                          </div>
                          <span className="ml-1 text-xs">{entity.weighted_score.toFixed(2)}</span>
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* Grounded Results */}
        <div className="bg-white rounded-lg shadow">
          <div className="px-6 py-4 border-b bg-green-50">
            <h3 className="text-lg font-semibold">Grounded (Web Search)</h3>
            <p className="text-sm text-gray-500 mt-1">AI associations with web context</p>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">#</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Entity</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Freq</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Pos</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Score</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {comparisonData.grounded.entities.slice(0, 15).map((entity, index) => {
                  const isInUngrounded = comparisonData.ungrounded.entities.some(
                    u => u.entity.toLowerCase() === entity.entity.toLowerCase()
                  )
                  return (
                    <tr key={index} className={`hover:bg-gray-50 ${!isInUngrounded ? 'bg-green-50' : ''}`}>
                      <td className="px-4 py-2 text-sm text-gray-500">{index + 1}</td>
                      <td className="px-4 py-2 text-sm font-medium text-gray-900">
                        {entity.entity}
                        {entity.variants && entity.variants.length > 1 && (
                          <span className="ml-1 text-xs text-gray-500">({entity.variants.length} var.)</span>
                        )}
                        {!isInUngrounded && (
                          <span className="ml-2 text-xs bg-green-100 text-green-800 px-1 rounded">unique</span>
                        )}
                      </td>
                      <td className="px-4 py-2 text-sm text-gray-500">{entity.frequency}</td>
                      <td className="px-4 py-2 text-sm text-gray-500">{entity.avg_position.toFixed(1)}</td>
                      <td className="px-4 py-2 text-sm text-gray-500">
                        <div className="flex items-center">
                          <div className="w-12 h-2 bg-gray-200 rounded-full overflow-hidden">
                            <div
                              className="h-full rounded-full"
                              style={{
                                width: `${entity.weighted_score * 100}%`,
                                backgroundColor: getScoreColor(entity.weighted_score)
                              }}
                            />
                          </div>
                          <span className="ml-1 text-xs">{entity.weighted_score.toFixed(2)}</span>
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Metadata Comparison */}
      {comparisonData.ungrounded.metadata && comparisonData.grounded.metadata && (
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold mb-4">Analysis Metadata</h3>
          <div className="grid grid-cols-2 gap-6">
            <div>
              <h4 className="font-medium text-gray-700 mb-2">Ungrounded</h4>
              <dl className="space-y-1">
                <div className="flex justify-between text-sm">
                  <dt className="text-gray-500">Total unique entities:</dt>
                  <dd className="font-medium">{comparisonData.ungrounded.metadata.total_unique_entities}</dd>
                </div>
                <div className="flex justify-between text-sm">
                  <dt className="text-gray-500">Canonical groups:</dt>
                  <dd className="font-medium">{comparisonData.ungrounded.metadata.canonical_groups}</dd>
                </div>
                <div className="flex justify-between text-sm">
                  <dt className="text-gray-500">Avg entities per run:</dt>
                  <dd className="font-medium">{comparisonData.ungrounded.metadata.avg_entities_per_run?.toFixed(1)}</dd>
                </div>
                <div className="flex justify-between text-sm">
                  <dt className="text-gray-500">Convergence rate:</dt>
                  <dd className="font-medium">{(comparisonData.ungrounded.metadata.convergence_rate * 100).toFixed(0)}%</dd>
                </div>
              </dl>
            </div>
            <div>
              <h4 className="font-medium text-gray-700 mb-2">Grounded</h4>
              <dl className="space-y-1">
                <div className="flex justify-between text-sm">
                  <dt className="text-gray-500">Total unique entities:</dt>
                  <dd className="font-medium">{comparisonData.grounded.metadata.total_unique_entities}</dd>
                </div>
                <div className="flex justify-between text-sm">
                  <dt className="text-gray-500">Canonical groups:</dt>
                  <dd className="font-medium">{comparisonData.grounded.metadata.canonical_groups}</dd>
                </div>
                <div className="flex justify-between text-sm">
                  <dt className="text-gray-500">Avg entities per run:</dt>
                  <dd className="font-medium">{comparisonData.grounded.metadata.avg_entities_per_run?.toFixed(1)}</dd>
                </div>
                <div className="flex justify-between text-sm">
                  <dt className="text-gray-500">Convergence rate:</dt>
                  <dd className="font-medium">{(comparisonData.grounded.metadata.convergence_rate * 100).toFixed(0)}%</dd>
                </div>
              </dl>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}