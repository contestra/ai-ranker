'use client'

import { useState, useEffect } from 'react'
import { trackedPhrasesApi } from '@/lib/api'
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
  const [usingContestraV2, setUsingContestraV2] = useState(false)

  useEffect(() => {
    loadTrackedPhrases()
    loadAnalysisResults()
    // Don't load old weekly tracking data - only use Contestra V2
    // loadWeeklyTracking()
    
    // Listen for analysis complete event
    const handleAnalysisComplete = () => {
      loadAnalysisResults()
      // loadWeeklyTracking()
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
    // ONLY use Contestra V2 data (the correct method)
    const contestraV2Key = `contestra_v2_${brandName}`
    const contestraV2Results = localStorage.getItem(contestraV2Key)
    
    if (contestraV2Results && vendor === 'openai') {
      const data = JSON.parse(contestraV2Results)
      if (data.entities) {
        setEntityAssociations(data.entities)
        setUsingContestraV2(true)
        console.log(`Loaded Contestra V2 entity associations:`, data.entities.length)
      }
    } else {
      // No Contestra V2 data available - clear any old data
      setEntityAssociations([])
      setUsingContestraV2(false)
      console.log(`No Contestra V2 data available for ${vendor}`)
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
          {info.icon} {info.name} Analysis
        </h2>
        <p className="text-gray-600">
          View entity associations and brand competition for your tracked phrases
        </p>
        <p className="text-sm text-gray-500 mt-1">
          💡 For historical trend graphs, use the <span className="font-medium">Weekly Trends</span> tab
        </p>
        {usingContestraV2 && vendor === 'openai' && (
          <div className="mt-3 inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-green-100 text-green-800">
            <svg className="w-4 h-4 mr-2" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
            </svg>
            Using Contestra V2 Data (Prompted Lists with Rank Aggregation)
          </div>
        )}
      </div>


      {/* Your Brand Section - Vendor-specific B→E Analysis */}
      <div className="bg-white rounded-lg shadow">
        <div className="px-6 py-4 border-b">
          <div>
            <h3 className="text-lg font-semibold">Your Brand</h3>
            <p className="text-sm text-gray-500 mt-1">
              Entities that {info.name} AI models currently associate with your brand
            </p>
          </div>
        </div>
        <div className="p-6">
          {/* Show current Contestra V2 data as a bar chart */}
          {entityAssociations.length > 0 ? (
            <div className="space-y-3">
              <p className="text-sm text-gray-600 mb-4">Top 10 entity associations by weighted score:</p>
              <div className="space-y-3">
                {entityAssociations.slice(0, 10).map((entity: any, i: number) => (
                  <div key={i}>
                    <div className="flex items-center justify-between mb-1">
                      <div className="text-sm text-gray-700">
                        <span className="font-medium">#{i + 1}</span> {entity.entity}
                        {entity.variants && entity.variants.length > 1 && (
                          <span className="ml-1 text-xs text-gray-500">({entity.variants.length} variants)</span>
                        )}
                      </div>
                      <div className="text-xs text-gray-500">
                        Score: {(entity.weighted_score || 0).toFixed(3)}
                      </div>
                    </div>
                    <div className="h-6 bg-gray-100 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-gradient-to-r from-blue-400 to-blue-600 rounded-full transition-all duration-500"
                        style={{
                          width: `${(entity.weighted_score || 0) * 100}%`
                        }}
                      />
                    </div>
                    <div className="flex justify-between text-xs text-gray-500 mt-1">
                      <span>Frequency: {entity.frequency || 1}</span>
                      <span>Avg Position: {entity.avg_position?.toFixed(1) || 'N/A'}</span>
                    </div>
                  </div>
                ))}
              </div>
              <div className="mt-4 p-3 bg-blue-50 rounded text-sm text-blue-800">
                Run Contestra V2 analysis multiple times to build tracking data.
              </div>
            </div>
          ) : (
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <div className="flex">
                <div className="flex-shrink-0">
                  <svg className="h-5 w-5 text-blue-400" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                  </svg>
                </div>
                <div className="ml-3">
                  <h3 className="text-sm font-medium text-blue-800">
                    No Contestra V2 Analysis Data Available
                  </h3>
                  <div className="mt-2 text-sm text-blue-700">
                    <p>To see {info.name} entity associations:</p>
                    <ol className="list-decimal list-inside mt-2">
                      <li>Go to the Settings tab</li>
                      <li>Click <strong>"Run Contestra V2 Analysis"</strong></li>
                    </ol>
                    <p className="mt-2">
                      This uses the correct prompted-list methodology with rank aggregation.
                    </p>
                  </div>
                </div>
              </div>
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