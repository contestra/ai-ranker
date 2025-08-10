'use client'

import { useState, useEffect } from 'react'
import { trackedPhrasesApi } from '@/lib/api'
import WeeklyTrendChart from './WeeklyTrendChart'
import RankingTimeSeriesChart from './RankingTimeSeriesChart'

interface ModelComparisonProps {
  brandId: number
  brandName: string
  vendor: 'openai' | 'google' | 'anthropic'
}

export default function ModelComparison({ brandId, brandName, vendor }: ModelComparisonProps) {
  const [trackedPhrases, setTrackedPhrases] = useState<any[]>([])
  const [selectedPhrase, setSelectedPhrase] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [weeklyView, setWeeklyView] = useState(true)
  const [analysisResults, setAnalysisResults] = useState<any[]>([])
  const [entityAssociations, setEntityAssociations] = useState<any[]>([])
  const [weeklyData, setWeeklyData] = useState<any>(null)
  const [loadingWeekly, setLoadingWeekly] = useState(false)

  useEffect(() => {
    loadTrackedPhrases()
    loadAnalysisResults()
    loadWeeklyTracking()
    
    // Listen for analysis complete event
    const handleAnalysisComplete = () => {
      loadAnalysisResults()
      loadWeeklyTracking()
    }
    
    window.addEventListener('analysisComplete', handleAnalysisComplete)
    
    return () => {
      window.removeEventListener('analysisComplete', handleAnalysisComplete)
    }
  }, [])

  const loadTrackedPhrases = () => {
    // Load from localStorage instead of API
    const stored = localStorage.getItem('trackedPhrases')
    if (stored) {
      const phrases = JSON.parse(stored)
      // Convert string array to objects with id and phrase properties
      const phraseObjects = phrases.map((phrase: string, index: number) => ({
        id: index + 1,
        phrase: phrase,
        category: 'General'
      }))
      setTrackedPhrases(phraseObjects)
      if (phraseObjects.length > 0) {
        setSelectedPhrase(phraseObjects[0])
      }
    }
    setLoading(false)
  }

  const loadWeeklyTracking = async () => {
    setLoadingWeekly(true)
    try {
      const response = await fetch(`http://localhost:8000/api/weekly-tracking/${brandName}/${vendor}`)
      if (response.ok) {
        const data = await response.json()
        setWeeklyData(data)
        console.log('Loaded weekly tracking data:', data)
      }
    } catch (error) {
      console.error('Failed to load weekly tracking:', error)
    } finally {
      setLoadingWeekly(false)
    }
  }

  const loadAnalysisResults = () => {
    // Load E→B analysis results (phrases to brands)
    let stored = localStorage.getItem(`analysis_results_${brandName}`)
    
    // If not found, try with "AVEA Life" specifically (from test)
    if (!stored && brandName.toLowerCase().includes('avea')) {
      stored = localStorage.getItem('analysis_results_AVEA Life')
    }
    
    console.log(`Loading analysis results for ${brandName} (${vendor}):`, stored)
    if (stored) {
      setAnalysisResults(JSON.parse(stored))
    }
    
    // Load vendor-specific B→E analysis (brand to entities)
    const vendorBeebKey = `analysis_${vendor}_${brandName}`
    const vendorBeebResults = localStorage.getItem(vendorBeebKey)
    
    if (vendorBeebResults) {
      const data = JSON.parse(vendorBeebResults)
      if (data.entities) {
        setEntityAssociations(data.entities)
        console.log(`Loaded ${vendor}-specific entity associations:`, data.entities.length)
      }
    }
  }

  const vendorInfo = {
    openai: { name: 'OpenAI', icon: '🤖', color: 'green' },
    google: { name: 'Google', icon: '🔍', color: 'blue' },
    anthropic: { name: 'Anthropic', icon: '🧠', color: 'purple' }
  }

  const info = vendorInfo[vendor]

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-gray-900 mb-2">
          {info.icon} {info.name} Brand Rankings
        </h2>
        <p className="text-gray-600">
          This section shows brand rankings from {info.name} AI responses for your tracked phrases.
        </p>
      </div>

      {/* Phrase Selector */}
      <div className="bg-white rounded-lg shadow p-4">
        <div className="flex items-center justify-between mb-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Select Tracked Phrase ({trackedPhrases.length} available)
            </label>
            {trackedPhrases.length > 0 ? (
              <select
                className="w-64 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
                value={selectedPhrase?.id || ''}
                onChange={(e) => {
                  const phrase = trackedPhrases.find(p => p.id === parseInt(e.target.value))
                  setSelectedPhrase(phrase)
                }}
              >
                {trackedPhrases.map(phrase => (
                  <option key={phrase.id} value={phrase.id}>
                    {phrase.phrase}
                  </option>
                ))}
              </select>
            ) : (
              <div className="text-sm text-gray-500 bg-gray-50 p-3 rounded">
                No tracked phrases found. Please add phrases in the Settings tab first.
              </div>
            )}
          </div>
          
          <div className="flex items-center">
            <input
              type="checkbox"
              id="weeklyView"
              checked={weeklyView}
              onChange={(e) => setWeeklyView(e.target.checked)}
              className="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded"
            />
            <label htmlFor="weeklyView" className="ml-2 text-sm text-gray-700">
              Weekly View
            </label>
          </div>
        </div>

        {/* Trend Chart */}
        {selectedPhrase && (
          <WeeklyTrendChart 
            brandId={brandId} 
            phraseId={selectedPhrase.id}
            phraseName={selectedPhrase.phrase}
            vendor={vendor}
          />
        )}
      </div>

      {/* Your Brand Section - Vendor-specific B→E Analysis */}
      <div className="bg-white rounded-lg shadow">
        <div className="px-6 py-4 border-b">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-lg font-semibold">Your Brand</h3>
              <p className="text-sm text-gray-500 mt-1">
                This graph shows which entities {info.name} AI models associate your brand with and tracks their rankings over time
              </p>
            </div>
            <div className="flex items-center">
              <input
                type="checkbox"
                id="weeklyViewBrand"
                checked={weeklyView}
                onChange={(e) => setWeeklyView(e.target.checked)}
                className="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded"
              />
              <label htmlFor="weeklyViewBrand" className="ml-2 text-sm text-gray-700">
                Weekly View
              </label>
            </div>
          </div>
        </div>
        <div className="p-6">
          {weeklyData?.entity_tracking && weeklyData.entity_tracking.length > 0 ? (
            <RankingTimeSeriesChart
              title=""
              description=""
              seriesData={weeklyData.entity_tracking}
              height={350}
              showWeeklyView={weeklyView}
            />
          ) : entityAssociations.length > 0 ? (
            <div className="space-y-3">
              <p className="text-sm text-gray-600 mb-2">Current rankings (no historical data yet):</p>
              <div className="grid grid-cols-2 gap-4">
                {entityAssociations.slice(0, 10).map((entity: any, i: number) => (
                  <div key={i} className="flex items-center justify-between text-sm p-2 bg-gray-50 rounded">
                    <span>#{i + 1} {entity.entity}</span>
                    <span className="text-xs text-gray-500">
                      Score: {entity.raw_similarity?.toFixed(2) || entity.weighted_score?.toFixed(2)}
                    </span>
                  </div>
                ))}
              </div>
              <div className="mt-4 p-3 bg-blue-50 rounded text-sm text-blue-800">
                Run analysis multiple times over several weeks to build historical tracking data.
              </div>
            </div>
          ) : (
            <div className="text-center text-gray-500">
              <p className="mb-2">No {vendor} entity associations found.</p>
              <p className="text-sm">Run "Vector Analysis (BEEB)" in Settings to analyze {info.name} embeddings.</p>
            </div>
          )}
        </div>
      </div>

      {/* Your Phrases Section - E→B Analysis */}
      <div className="bg-white rounded-lg shadow">
        <div className="px-6 py-4 border-b">
          <h3 className="text-lg font-semibold">Your Phrases</h3>
          <p className="text-sm text-gray-500 mt-1">
            This section shows which brands {info.name} AI models associate with your tracked phrases and tracks their rankings over time
          </p>
        </div>
        <div className="p-6 space-y-6">
          {/* Show time-series graphs if weekly data exists */}
          {weeklyData?.phrase_tracking && Object.keys(weeklyData.phrase_tracking).length > 0 ? (
            <div className="space-y-8">
              {Object.entries(weeklyData.phrase_tracking).map(([phrase, brandData]: [string, any]) => (
                <div key={phrase} className="border rounded-lg p-4">
                  <h4 className="font-medium text-gray-900 mb-4">
                    Tracked Phrase: "{phrase}"
                  </h4>
                  <RankingTimeSeriesChart
                    title=""
                    description=""
                    seriesData={brandData}
                    height={300}
                    showWeeklyView={weeklyView}
                  />
                </div>
              ))}
            </div>
          ) : analysisResults.length > 0 ? (
            <div className="space-y-4">
              <p className="text-sm text-gray-600">Current analysis results (no historical tracking yet):</p>
              {analysisResults
                .filter((r: any) => r.vendor === vendor)
                .map((result: any, index: number) => (
                  <div key={index} className="border rounded-lg p-4">
                    <h4 className="font-medium text-gray-900 mb-2">
                      Prompt: "{result.phrase || trackedPhrases[index % trackedPhrases.length]?.phrase || 'Tracked phrase'}"
                    </h4>
                    <div className="space-y-1">
                      {result.brands_found?.length > 0 ? (
                        result.brands_found.map((brand: string, i: number) => (
                          <div key={i} className="flex items-center justify-between text-sm">
                            <span className={result.brand_mentioned && brand.toLowerCase().includes(brandName.toLowerCase()) ? 'font-semibold text-indigo-600' : ''}>
                              #{i + 1} {brand}
                            </span>
                            {result.brand_mentioned && brand.toLowerCase().includes(brandName.toLowerCase()) && (
                              <span className="text-xs bg-indigo-100 text-indigo-800 px-2 py-1 rounded">Your Brand</span>
                            )}
                          </div>
                        ))
                      ) : (
                        <div className="text-sm text-gray-500">
                          {result.raw_response ? (
                            <div className="whitespace-pre-wrap">{result.raw_response.slice(0, 200)}...</div>
                          ) : (
                            'No brands found in response'
                          )}
                        </div>
                      )}
                    </div>
                    {!result.brand_mentioned && result.brands_found?.length > 0 && (
                      <p className="text-xs text-red-600 mt-2">Your brand was not mentioned</p>
                    )}
                  </div>
                ))}
            </div>
          ) : (
            <div className="text-center">
              <p className="text-gray-500 mb-4">
                No analysis results yet.
              </p>
              <p className="text-sm text-gray-400">
                1. Add phrases in Settings<br/>
                2. Click "Run AI Analysis"<br/>
                3. Results will appear here
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}