'use client'

import { useState } from 'react'
import { ChartBarIcon, ArrowsRightLeftIcon, CheckCircleIcon, XCircleIcon, ExclamationCircleIcon } from '@heroicons/react/24/outline'

interface EntityComparison {
  entity: string
  prompted_rank: number | null
  prompted_score: number | null
  embedding_rank: number | null
  embedding_similarity: number | null
  rank_difference: number | null
  agreement_level: string
}

interface ConcordanceMetrics {
  spearman_correlation: number
  kendall_tau: number
  rank_agreement_percentage: number
  top_5_overlap: number
  top_10_overlap: number
  mean_rank_difference: number
}

interface ConcordanceData {
  brand: string
  vendor: string
  entity_comparisons: EntityComparison[]
  metrics: ConcordanceMetrics
  insights: string[]
  prompted_only: string[]
  embedding_only: string[]
}

interface ConcordanceAnalysisProps {
  brandName: string
  vendor: string
  trackedPhrases: string[]
}

export default function ConcordanceAnalysis({ brandName, vendor, trackedPhrases }: ConcordanceAnalysisProps) {
  const [concordanceData, setConcordanceData] = useState<ConcordanceData | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [selectedView, setSelectedView] = useState<'comparison' | 'metrics' | 'unique'>('comparison')

  const runConcordanceAnalysis = async () => {
    setLoading(true)
    setError('')
    
    try {
      const response = await fetch('http://localhost:8000/api/concordance', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          brand_name: brandName,
          vendor: vendor,
          tracked_phrases: trackedPhrases.slice(0, 2),
          num_runs: 6,
          top_k: 10
        })
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }

      const data = await response.json()
      setConcordanceData(data)
    } catch (err: any) {
      setError(`Failed to run concordance analysis: ${err.message}`)
    } finally {
      setLoading(false)
    }
  }

  const getAgreementIcon = (level: string) => {
    switch(level) {
      case 'perfect':
      case 'strong':
        return <CheckCircleIcon className="h-5 w-5 text-green-500" />
      case 'moderate':
        return <ExclamationCircleIcon className="h-5 w-5 text-yellow-500" />
      case 'weak':
      case 'disagreement':
        return <XCircleIcon className="h-5 w-5 text-red-500" />
      default:
        return null
    }
  }

  const getAgreementColor = (level: string) => {
    switch(level) {
      case 'perfect':
      case 'strong':
        return 'bg-green-50 text-green-800'
      case 'moderate':
        return 'bg-yellow-50 text-yellow-800'
      case 'weak':
      case 'disagreement':
        return 'bg-red-50 text-red-800'
      default:
        return 'bg-gray-50 text-gray-800'
    }
  }

  const getCorrelationColor = (value: number) => {
    if (value > 0.7) return 'text-green-600'
    if (value > 0.4) return 'text-yellow-600'
    return 'text-red-600'
  }

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-2xl font-bold text-gray-900">Concordance Analysis</h2>
            <p className="text-sm text-gray-600 mt-1">
              Compare prompted-list rankings vs embedding similarity
            </p>
          </div>
          <button
            onClick={runConcordanceAnalysis}
            disabled={loading || !brandName}
            className="px-4 py-2 bg-purple-600 text-white rounded-md hover:bg-purple-700 disabled:bg-gray-400 flex items-center space-x-2"
          >
            <ArrowsRightLeftIcon className="h-5 w-5" />
            <span>{loading ? 'Analyzing...' : 'Run Concordance'}</span>
          </button>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-red-50 text-red-700 rounded-lg">{error}</div>
        )}

        {concordanceData && (
          <>
            {/* Insights Section */}
            <div className="mb-6 p-4 bg-purple-50 rounded-lg">
              <h3 className="font-semibold text-purple-900 mb-3">Key Insights</h3>
              <ul className="space-y-2">
                {concordanceData.insights.map((insight, idx) => (
                  <li key={idx} className="text-sm text-purple-800">{insight}</li>
                ))}
              </ul>
            </div>

            {/* View Toggle */}
            <div className="flex space-x-4 mb-6 border-b">
              <button
                onClick={() => setSelectedView('comparison')}
                className={`pb-2 px-1 ${
                  selectedView === 'comparison'
                    ? 'border-b-2 border-purple-600 text-purple-600'
                    : 'text-gray-600 hover:text-gray-800'
                }`}
              >
                Entity Comparison
              </button>
              <button
                onClick={() => setSelectedView('metrics')}
                className={`pb-2 px-1 ${
                  selectedView === 'metrics'
                    ? 'border-b-2 border-purple-600 text-purple-600'
                    : 'text-gray-600 hover:text-gray-800'
                }`}
              >
                Concordance Metrics
              </button>
              <button
                onClick={() => setSelectedView('unique')}
                className={`pb-2 px-1 ${
                  selectedView === 'unique'
                    ? 'border-b-2 border-purple-600 text-purple-600'
                    : 'text-gray-600 hover:text-gray-800'
                }`}
              >
                Unique Entities
              </button>
            </div>

            {/* Comparison Table */}
            {selectedView === 'comparison' && (
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Entity</th>
                      <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase">Prompted Rank</th>
                      <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase">Prompted Score</th>
                      <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase">Embedding Rank</th>
                      <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase">Similarity</th>
                      <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase">Rank Diff</th>
                      <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase">Agreement</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {concordanceData.entity_comparisons.map((comp, idx) => (
                      <tr key={idx} className="hover:bg-gray-50">
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                          {comp.entity}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-center text-gray-600">
                          {comp.prompted_rank ? `#${comp.prompted_rank}` : '-'}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-center text-gray-600">
                          {comp.prompted_score ? comp.prompted_score.toFixed(3) : '-'}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-center text-gray-600">
                          {comp.embedding_rank ? `#${comp.embedding_rank}` : '-'}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-center text-gray-600">
                          {comp.embedding_similarity ? comp.embedding_similarity.toFixed(3) : '-'}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-center">
                          {comp.rank_difference !== null ? (
                            <span className={`px-2 py-1 rounded ${
                              comp.rank_difference <= 2 ? 'bg-green-100 text-green-800' :
                              comp.rank_difference <= 5 ? 'bg-yellow-100 text-yellow-800' :
                              'bg-red-100 text-red-800'
                            }`}>
                              {comp.rank_difference}
                            </span>
                          ) : '-'}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-center">
                          <div className="flex items-center justify-center space-x-1">
                            {getAgreementIcon(comp.agreement_level)}
                            <span className={`px-2 py-1 rounded text-xs ${getAgreementColor(comp.agreement_level)}`}>
                              {comp.agreement_level}
                            </span>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {/* Metrics View */}
            {selectedView === 'metrics' && (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                <div className="bg-gray-50 rounded-lg p-4">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-gray-600">Spearman Correlation</span>
                    <ChartBarIcon className="h-5 w-5 text-gray-400" />
                  </div>
                  <p className={`text-2xl font-bold mt-2 ${getCorrelationColor(concordanceData.metrics.spearman_correlation)}`}>
                    {concordanceData.metrics.spearman_correlation.toFixed(3)}
                  </p>
                  <p className="text-xs text-gray-500 mt-1">Rank correlation coefficient</p>
                </div>

                <div className="bg-gray-50 rounded-lg p-4">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-gray-600">Kendall's Tau</span>
                    <ChartBarIcon className="h-5 w-5 text-gray-400" />
                  </div>
                  <p className={`text-2xl font-bold mt-2 ${getCorrelationColor(concordanceData.metrics.kendall_tau)}`}>
                    {concordanceData.metrics.kendall_tau.toFixed(3)}
                  </p>
                  <p className="text-xs text-gray-500 mt-1">Ordinal association</p>
                </div>

                <div className="bg-gray-50 rounded-lg p-4">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-gray-600">Rank Agreement</span>
                    <CheckCircleIcon className="h-5 w-5 text-gray-400" />
                  </div>
                  <p className="text-2xl font-bold mt-2 text-gray-900">
                    {concordanceData.metrics.rank_agreement_percentage.toFixed(1)}%
                  </p>
                  <p className="text-xs text-gray-500 mt-1">Within 3 positions</p>
                </div>

                <div className="bg-gray-50 rounded-lg p-4">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-gray-600">Top-5 Overlap</span>
                    <ArrowsRightLeftIcon className="h-5 w-5 text-gray-400" />
                  </div>
                  <p className="text-2xl font-bold mt-2 text-gray-900">
                    {concordanceData.metrics.top_5_overlap.toFixed(0)}%
                  </p>
                  <p className="text-xs text-gray-500 mt-1">Common in top 5</p>
                </div>

                <div className="bg-gray-50 rounded-lg p-4">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-gray-600">Top-10 Overlap</span>
                    <ArrowsRightLeftIcon className="h-5 w-5 text-gray-400" />
                  </div>
                  <p className="text-2xl font-bold mt-2 text-gray-900">
                    {concordanceData.metrics.top_10_overlap.toFixed(0)}%
                  </p>
                  <p className="text-xs text-gray-500 mt-1">Common in top 10</p>
                </div>

                <div className="bg-gray-50 rounded-lg p-4">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-gray-600">Mean Rank Difference</span>
                    <ExclamationCircleIcon className="h-5 w-5 text-gray-400" />
                  </div>
                  <p className="text-2xl font-bold mt-2 text-gray-900">
                    {concordanceData.metrics.mean_rank_difference.toFixed(1)}
                  </p>
                  <p className="text-xs text-gray-500 mt-1">Average position difference</p>
                </div>
              </div>
            )}

            {/* Unique Entities View */}
            {selectedView === 'unique' && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <h3 className="font-semibold text-gray-900 mb-3 flex items-center">
                    <span className="mr-2">💭</span>
                    Unique to Prompted-Lists
                  </h3>
                  <div className="bg-blue-50 rounded-lg p-4">
                    {concordanceData.prompted_only.length > 0 ? (
                      <ul className="space-y-2">
                        {concordanceData.prompted_only.map((entity, idx) => (
                          <li key={idx} className="text-sm text-blue-800 flex items-center">
                            <span className="w-2 h-2 bg-blue-400 rounded-full mr-2"></span>
                            {entity}
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p className="text-sm text-blue-600">No unique entities</p>
                    )}
                  </div>
                </div>

                <div>
                  <h3 className="font-semibold text-gray-900 mb-3 flex items-center">
                    <span className="mr-2">🔢</span>
                    Unique to Embeddings
                  </h3>
                  <div className="bg-green-50 rounded-lg p-4">
                    {concordanceData.embedding_only.length > 0 ? (
                      <ul className="space-y-2">
                        {concordanceData.embedding_only.map((entity, idx) => (
                          <li key={idx} className="text-sm text-green-800 flex items-center">
                            <span className="w-2 h-2 bg-green-400 rounded-full mr-2"></span>
                            {entity}
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p className="text-sm text-green-600">No unique entities</p>
                    )}
                  </div>
                </div>
              </div>
            )}
          </>
        )}

        {!concordanceData && !loading && (
          <div className="text-center py-12 text-gray-500">
            <ArrowsRightLeftIcon className="h-12 w-12 mx-auto mb-4 text-gray-300" />
            <p>Run concordance analysis to compare prompted-list vs embedding methods</p>
          </div>
        )}
      </div>
    </div>
  )
}