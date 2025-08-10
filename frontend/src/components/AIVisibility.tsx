'use client'

import { useState, useEffect } from 'react'
import { dashboardApi } from '@/lib/api'

interface AIVisibilityProps {
  brandId: number
  brandName: string
}

interface EntityData {
  entity: string
  frequency: number
  avg_position: number | null
  weighted_score: number
}

interface BrandData {
  brand: string
  frequency: number
  avg_position: number | null
  weighted_score: number
}

export default function AIVisibility({ brandId, brandName }: AIVisibilityProps) {
  const [topEntities, setTopEntities] = useState<EntityData[]>([])
  const [topBrands, setTopBrands] = useState<BrandData[]>([])
  const [loading, setLoading] = useState(false)
  const [hasRealData, setHasRealData] = useState(false)
  const [trackedPhrases, setTrackedPhrases] = useState<string[]>([])

  useEffect(() => {
    const loadData = () => {
      // Check if we have tracked phrases
      const stored = localStorage.getItem('trackedPhrases')
      if (stored) {
        const phrases = JSON.parse(stored)
        setTrackedPhrases(phrases)
      }
      
      // Only load data for the exact brand name entered
      const analysisData = localStorage.getItem(`analysis_${brandName}`)
      
      console.log('Checking for analysis data:', `analysis_${brandName}`)
      console.log('Found data:', analysisData ? 'Yes' : 'No')
      
      if (analysisData) {
        const data = JSON.parse(analysisData)
        console.log('Parsed analysis data:', data)
        if (data.entities && data.entities.length > 0) {
          setTopEntities(data.entities)
          setHasRealData(true)
        }
        if (data.brands && data.brands.length > 0) {
          setTopBrands(data.brands)
          setHasRealData(true)
        }
      } else {
        // No data found - show empty state
        console.log('No analysis data found')
        setTopEntities([])
        setTopBrands([])
        setHasRealData(false)
      }
    }
    
    // Initial load
    loadData()
    
    // Listen for analysis complete event
    const handleAnalysisComplete = (event: any) => {
      console.log('Analysis complete event received:', event.detail)
      if (event.detail.brandName === brandName) {
        loadData()
      }
    }
    
    window.addEventListener('analysisComplete', handleAnalysisComplete)
    
    return () => {
      window.removeEventListener('analysisComplete', handleAnalysisComplete)
    }
  }, [brandName])

  const generateMockData = () => {
    console.log('generateMockData called for brand:', brandName)
    // For AVEA Life - health/wellness/longevity brand entities
    const aveaEntities: EntityData[] = [
      { entity: 'longevity', frequency: 52, avg_position: 1.3, weighted_score: 0.88 },
      { entity: 'supplements', frequency: 48, avg_position: 1.5, weighted_score: 0.82 },
      { entity: 'NMN', frequency: 45, avg_position: 1.8, weighted_score: 0.78 },
      { entity: 'NAD+', frequency: 42, avg_position: 2.0, weighted_score: 0.72 },
      { entity: 'anti-aging', frequency: 38, avg_position: 2.2, weighted_score: 0.68 },
      { entity: 'resveratrol', frequency: 35, avg_position: 2.5, weighted_score: 0.62 },
      { entity: 'cellular health', frequency: 32, avg_position: 2.8, weighted_score: 0.58 },
      { entity: 'biohacking', frequency: 28, avg_position: 3.0, weighted_score: 0.52 },
      { entity: 'healthspan', frequency: 25, avg_position: 3.2, weighted_score: 0.48 },
      { entity: 'mitochondria', frequency: 22, avg_position: 3.5, weighted_score: 0.42 },
      { entity: 'collagen', frequency: 20, avg_position: 3.8, weighted_score: 0.38 },
      { entity: 'vitamins', frequency: 18, avg_position: 4.0, weighted_score: 0.35 },
      { entity: 'wellness', frequency: 16, avg_position: 4.2, weighted_score: 0.32 },
      { entity: 'nutrition', frequency: 14, avg_position: 4.5, weighted_score: 0.28 },
      { entity: 'science-backed', frequency: 12, avg_position: 4.8, weighted_score: 0.25 },
    ]

    // For AVEA Life - competitive brands in longevity/wellness space
    const aveaBrands: BrandData[] = [
      { brand: 'AVEA Life', frequency: 38, avg_position: 2.1, weighted_score: 0.65 },
      { brand: 'Elysium Health', frequency: 45, avg_position: 1.8, weighted_score: 0.75 },
      { brand: 'Tru Niagen', frequency: 42, avg_position: 1.9, weighted_score: 0.72 },
      { brand: 'Life Extension', frequency: 40, avg_position: 2.0, weighted_score: 0.68 },
      { brand: 'Thorne', frequency: 35, avg_position: 2.3, weighted_score: 0.62 },
      { brand: 'InsideTracker', frequency: 32, avg_position: 2.5, weighted_score: 0.58 },
      { brand: 'Ritual', frequency: 28, avg_position: 2.8, weighted_score: 0.52 },
      { brand: 'Athletic Greens', frequency: 25, avg_position: 3.0, weighted_score: 0.48 },
      { brand: 'Bulletproof', frequency: 22, avg_position: 3.2, weighted_score: 0.42 },
      { brand: 'Qualia', frequency: 20, avg_position: 3.5, weighted_score: 0.38 },
      { brand: 'Timeline Nutrition', frequency: 18, avg_position: 3.8, weighted_score: 0.35 },
      { brand: 'Basis', frequency: 15, avg_position: 4.0, weighted_score: 0.32 },
      { brand: 'ChromaDex', frequency: 12, avg_position: 4.2, weighted_score: 0.28 },
      { brand: 'ProHealth', frequency: 10, avg_position: 4.5, weighted_score: 0.25 },
      { brand: 'Pure Encapsulations', frequency: 8, avg_position: 4.8, weighted_score: 0.22 },
    ]

    // Check if brand is AVEA-related, otherwise use generic data
    if (brandName.toLowerCase().includes('avea')) {
      setTopEntities(aveaEntities)
      setTopBrands(aveaBrands)
    } else {
      // Generic data for other brands
      const genericEntities: EntityData[] = [
        { entity: 'quality', frequency: 45, avg_position: 1.5, weighted_score: 0.78 },
        { entity: 'innovation', frequency: 38, avg_position: 1.8, weighted_score: 0.72 },
        { entity: 'value', frequency: 32, avg_position: 2.2, weighted_score: 0.62 },
        { entity: 'service', frequency: 28, avg_position: 2.5, weighted_score: 0.55 },
        { entity: 'reliability', frequency: 25, avg_position: 2.8, weighted_score: 0.48 },
      ]
      
      const genericBrands: BrandData[] = [
        { brand: brandName, frequency: 35, avg_position: 2.0, weighted_score: 0.65 },
        { brand: 'Market Leader', frequency: 42, avg_position: 1.5, weighted_score: 0.75 },
        { brand: 'Competitor', frequency: 28, avg_position: 2.5, weighted_score: 0.55 },
      ]
      
      setTopEntities(genericEntities)
      setTopBrands(genericBrands)
    }
  }

  // Remove automatic loading from API - only use localStorage data
  // The loadData function is no longer needed since we're using embedding analysis

  const getScoreColor = (score: number) => {
    const opacity = Math.min(score * 2, 1) // Scale 0-0.5 to 0-1 opacity
    return `rgba(59, 130, 246, ${opacity})` // Blue with variable opacity
  }

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="animate-pulse">
          <div className="h-8 bg-gray-200 rounded w-1/4 mb-4"></div>
          <div className="grid grid-cols-2 gap-6">
            <div className="h-96 bg-gray-200 rounded"></div>
            <div className="h-96 bg-gray-200 rounded"></div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-gray-900 mb-2">AI Visibility Overview</h2>
        <p className="text-gray-600">
          AI Rank shows what happens when people talk to AI models to find information related to your name, brand, products or services.
        </p>
      </div>

      {/* Show notice if no data */}
      {topEntities.length === 0 && topBrands.length === 0 && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div className="flex">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-blue-400" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="ml-3">
              <h3 className="text-sm font-medium text-blue-800">
                No Analysis Data Available
              </h3>
              <div className="mt-2 text-sm text-blue-700">
                <p>To see your brand's AI visibility metrics:</p>
                <ol className="list-decimal list-inside mt-2">
                  <li>Go to the Settings tab</li>
                  <li>Add tracked phrases for your market</li>
                  <li>Click <strong>"Run Vector Analysis (BEEB)"</strong> to calculate embedding similarities</li>
                </ol>
                <p className="mt-2">
                  BEEB analysis uses vector embeddings to measure semantic similarity between your brand and key entities/competitors.
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-2 gap-6">
        {/* Top 20 Entities (B→E) */}
        <div className="bg-white rounded-lg shadow">
          <div className="px-6 py-4 border-b">
            <h3 className="text-lg font-semibold">Top 20 Entities</h3>
            <p className="text-sm text-gray-500 mt-1">Entities AIs associate with your brand.</p>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Entity
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Frequency
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Avg Position
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Weight
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {topEntities.map((entity, index) => (
                  <tr key={index} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                      {entity.entity}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {entity.frequency}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {entity.avg_position?.toFixed(2) || '-'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      <div className="flex items-center">
                        <div className="w-16 h-2 bg-gray-200 rounded-full overflow-hidden">
                          <div
                            className="h-full rounded-full"
                            style={{
                              width: `${entity.weighted_score * 100}%`,
                              backgroundColor: getScoreColor(entity.weighted_score)
                            }}
                          />
                        </div>
                        <span className="ml-2 text-xs">{entity.weighted_score.toFixed(3)}</span>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Top 20 Brands (E→B) */}
        <div className="bg-white rounded-lg shadow">
          <div className="px-6 py-4 border-b">
            <h3 className="text-lg font-semibold">Top 20 Brands</h3>
            <p className="text-sm text-gray-500 mt-1">Brands AIs associate with your tracked phrases.</p>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Brand
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Frequency
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Avg Position
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Weight
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {topBrands.map((brand, index) => (
                  <tr 
                    key={index} 
                    className={`hover:bg-gray-50 ${
                      brand.brand.toLowerCase() === brandName.toLowerCase() 
                        ? 'bg-indigo-50' 
                        : ''
                    }`}
                  >
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                      {brand.brand}
                      {brand.brand.toLowerCase() === brandName.toLowerCase() && (
                        <span className="ml-2 text-xs bg-indigo-100 text-indigo-800 px-2 py-1 rounded">
                          You
                        </span>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {brand.frequency}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {brand.avg_position?.toFixed(2) || '-'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      <div className="flex items-center">
                        <div className="w-16 h-2 bg-gray-200 rounded-full overflow-hidden">
                          <div
                            className="h-full rounded-full"
                            style={{
                              width: `${brand.weighted_score * 100}%`,
                              backgroundColor: getScoreColor(brand.weighted_score)
                            }}
                          />
                        </div>
                        <span className="ml-2 text-xs">{brand.weighted_score.toFixed(3)}</span>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Association Bar Charts */}
      <div className="grid grid-cols-2 gap-6">
        {/* Top Associations - Entities */}
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold mb-4">Top Associations</h3>
          <div className="space-y-3">
            {topEntities.slice(0, 10).map((entity, index) => (
              <div key={index} className="flex items-center">
                <div className="w-32 text-sm text-gray-600 truncate">{entity.entity}</div>
                <div className="flex-1 ml-4">
                  <div className="h-6 bg-gray-100 rounded-full overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all duration-500"
                      style={{
                        width: `${entity.weighted_score * 200}%`, // Scale to make visible
                        backgroundColor: getScoreColor(entity.weighted_score)
                      }}
                    />
                  </div>
                </div>
                <div className="ml-2 text-xs text-gray-500 w-12 text-right">
                  {entity.weighted_score.toFixed(2)}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Top Associations - Brands */}
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold mb-4">Top Associations</h3>
          <div className="space-y-3">
            {topBrands.slice(0, 10).map((brand, index) => (
              <div key={index} className="flex items-center">
                <div className="w-32 text-sm text-gray-600 truncate">
                  {brand.brand}
                  {brand.brand.toLowerCase() === brandName.toLowerCase() && (
                    <span className="ml-1 text-xs text-indigo-600">●</span>
                  )}
                </div>
                <div className="flex-1 ml-4">
                  <div className="h-6 bg-gray-100 rounded-full overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all duration-500"
                      style={{
                        width: `${brand.weighted_score * 200}%`, // Scale to make visible
                        backgroundColor: getScoreColor(brand.weighted_score)
                      }}
                    />
                  </div>
                </div>
                <div className="ml-2 text-xs text-gray-500 w-12 text-right">
                  {brand.weighted_score.toFixed(2)}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}