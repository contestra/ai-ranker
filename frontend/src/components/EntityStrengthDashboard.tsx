'use client'

import { useState, useEffect } from 'react'
import { CheckCircleIcon, XCircleIcon, QuestionMarkCircleIcon, ExclamationTriangleIcon, ShieldCheckIcon } from '@heroicons/react/24/outline'

interface EntityClassification {
  label: 'KNOWN_STRONG' | 'KNOWN_WEAK' | 'UNKNOWN' | 'EMPTY' | 'HALLUCINATED'
  confidence: number
  reasoning?: string
  specific_claims: string[]
  generic_claims: string[]
}

interface BrandStrengthResult {
  brand: string
  strength: string
  confidence: number
  error?: string
}

interface EntityStrengthDashboardProps {
  brandName: string
}

export default function EntityStrengthDashboard({ brandName }: EntityStrengthDashboardProps) {
  const [primaryBrand, setPrimaryBrand] = useState<EntityClassification | null>(null)
  const [competitors, setCompetitors] = useState<BrandStrengthResult[]>([])
  const [customBrands, setCustomBrands] = useState<string>('')
  const [loading, setLoading] = useState(false)
  const [batchLoading, setBatchLoading] = useState(false)
  const [vendor, setVendor] = useState('openai')

  // Check primary brand on mount
  useEffect(() => {
    if (brandName) {
      checkBrandStrength(brandName)
    }
  }, [brandName])

  const checkBrandStrength = async (brand: string) => {
    setLoading(true)
    try {
      const response = await fetch('http://localhost:8000/api/brand-entity-strength', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          brand_name: brand,
          vendor: vendor,
          include_reasoning: true
        })
      })

      if (response.ok) {
        const data = await response.json()
        setPrimaryBrand(data.classification)
      }
    } catch (error) {
      console.error('Error checking brand strength:', error)
    }
    setLoading(false)
  }

  const checkCompetitors = async () => {
    if (!customBrands.trim()) return

    setBatchLoading(true)
    const brands = customBrands.split(',').map(b => b.trim()).filter(b => b)
    
    try {
      const response = await fetch('http://localhost:8000/api/brand-entity-strength/batch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          brands: brands,
          vendor: vendor
        })
      })

      if (response.ok) {
        const data = await response.json()
        setCompetitors(data.results)
      }
    } catch (error) {
      console.error('Error checking competitors:', error)
    }
    setBatchLoading(false)
  }

  const getStrengthIcon = (label: string) => {
    switch (label) {
      case 'KNOWN_STRONG':
        return <CheckCircleIcon className="h-5 w-5 text-green-500" />
      case 'KNOWN_WEAK':
        return <ShieldCheckIcon className="h-5 w-5 text-yellow-500" />
      case 'UNKNOWN':
        return <QuestionMarkCircleIcon className="h-5 w-5 text-gray-500" />
      case 'EMPTY':
      case 'ERROR':
        return <XCircleIcon className="h-5 w-5 text-red-500" />
      default:
        return null
    }
  }

  const getStrengthColor = (label: string) => {
    switch (label) {
      case 'KNOWN_STRONG':
        return 'bg-green-100 text-green-800'
      case 'KNOWN_WEAK':
        return 'bg-yellow-100 text-yellow-800'
      case 'UNKNOWN':
        return 'bg-gray-100 text-gray-800'
      case 'EMPTY':
      case 'ERROR':
        return 'bg-red-100 text-red-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  const getStrengthLabel = (label: string) => {
    switch (label) {
      case 'KNOWN_STRONG': return 'Strong Entity'
      case 'KNOWN_WEAK': return 'Weak Entity'
      case 'UNKNOWN': return 'Unknown'
      case 'EMPTY': return 'No Data'
      case 'ERROR': return 'Error'
      default: return label
    }
  }

  const getStrengthScore = (label: string) => {
    switch (label) {
      case 'KNOWN_STRONG': return 100
      case 'KNOWN_WEAK': return 60
      case 'UNKNOWN': return 5  // Very low score - AI doesn't know the brand
      case 'EMPTY': return 0
      case 'ERROR': return 0
      default: return 0
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-gray-900 mb-2">Entity Strength Analysis</h2>
        <p className="text-gray-600">
          Measure how well AI models recognize and understand brands. Strong entities have specific, verifiable knowledge in AI systems.
        </p>
      </div>

      {/* Vendor Selection */}
      <div className="flex items-center space-x-4">
        <label className="text-sm font-medium text-gray-700">AI Model:</label>
        <select
          value={vendor}
          onChange={(e) => setVendor(e.target.value)}
          className="rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
        >
          <option value="openai">OpenAI (GPT-5)</option>
          <option value="google">Google (Gemini 2.5 Pro)</option>
        </select>
      </div>

      {/* Primary Brand Analysis */}
      <div className="bg-white rounded-lg shadow-lg p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-900">Your Brand: {brandName}</h3>
          <button
            onClick={() => checkBrandStrength(brandName)}
            className="text-sm text-indigo-600 hover:text-indigo-700"
            disabled={loading}
          >
            {loading ? 'Checking...' : 'Re-check'}
          </button>
        </div>

        {primaryBrand && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                {getStrengthIcon(primaryBrand.label)}
                <div>
                  <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${getStrengthColor(primaryBrand.label)}`}>
                    {getStrengthLabel(primaryBrand.label)}
                  </span>
                </div>
              </div>
              <div className="text-right">
                <div className="text-3xl font-bold text-gray-900">{primaryBrand.confidence}%</div>
                <div className="text-sm text-gray-500">Confidence</div>
              </div>
            </div>

            {/* Strength Meter */}
            <div className="relative pt-1">
              <div className="flex mb-2 items-center justify-between">
                <div className="text-xs font-semibold inline-block text-gray-600">
                  Entity Strength
                </div>
                <div className="text-xs font-semibold inline-block text-gray-600">
                  {getStrengthScore(primaryBrand.label)}/100
                </div>
              </div>
              <div className="overflow-hidden h-2 mb-4 text-xs flex rounded bg-gray-200">
                <div
                  style={{ width: `${getStrengthScore(primaryBrand.label)}%` }}
                  className={`shadow-none flex flex-col text-center whitespace-nowrap text-white justify-center ${
                    primaryBrand.label === 'KNOWN_STRONG' ? 'bg-green-500' :
                    primaryBrand.label === 'KNOWN_WEAK' ? 'bg-yellow-500' :
                    primaryBrand.label === 'UNKNOWN' ? 'bg-gray-500' :
                    primaryBrand.label === 'HALLUCINATED' ? 'bg-orange-500' :
                    'bg-red-500'
                  }`}
                />
              </div>
            </div>

            {primaryBrand.reasoning && (
              <div className="bg-gray-50 rounded-lg p-4">
                <p className="text-sm text-gray-700">{primaryBrand.reasoning}</p>
              </div>
            )}

            {/* Claims */}
            <div className="grid grid-cols-2 gap-4">
              {primaryBrand.specific_claims.length > 0 && (
                <div>
                  <h4 className="text-sm font-medium text-gray-700 mb-2">Specific Knowledge</h4>
                  <ul className="list-disc list-inside text-sm text-gray-600 space-y-1">
                    {primaryBrand.specific_claims.slice(0, 3).map((claim, idx) => (
                      <li key={idx}>{claim}</li>
                    ))}
                  </ul>
                </div>
              )}
              {primaryBrand.generic_claims.length > 0 && (
                <div>
                  <h4 className="text-sm font-medium text-gray-700 mb-2">Generic Claims</h4>
                  <ul className="list-disc list-inside text-sm text-gray-600 space-y-1">
                    {primaryBrand.generic_claims.slice(0, 3).map((claim, idx) => (
                      <li key={idx}>{claim}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Competitor Analysis */}
      <div className="bg-white rounded-lg shadow-lg p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Compare with Competitors</h3>
        
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Enter competitor brands (comma-separated)
            </label>
            <div className="flex space-x-2">
              <input
                type="text"
                value={customBrands}
                onChange={(e) => setCustomBrands(e.target.value)}
                placeholder="e.g., OpenAI, Google, Microsoft, Meta"
                className="flex-1 rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
              />
              <button
                onClick={checkCompetitors}
                disabled={batchLoading || !customBrands.trim()}
                className="px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50"
              >
                {batchLoading ? 'Checking...' : 'Check Strength'}
              </button>
            </div>
          </div>

          {/* Results Table */}
          {competitors.length > 0 && (
            <div className="overflow-hidden shadow ring-1 ring-black ring-opacity-5 md:rounded-lg">
              <table className="min-w-full divide-y divide-gray-300">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Brand
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Classification
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Confidence
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Strength Score
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {/* Include primary brand for comparison */}
                  {primaryBrand && (
                    <tr className="bg-indigo-50">
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                        {brandName} <span className="text-xs bg-indigo-100 text-indigo-800 px-2 py-1 rounded ml-2">You</span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center space-x-2">
                          {getStrengthIcon(primaryBrand.label)}
                          <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStrengthColor(primaryBrand.label)}`}>
                            {getStrengthLabel(primaryBrand.label)}
                          </span>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {primaryBrand.confidence}%
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center">
                          <div className="w-24 bg-gray-200 rounded-full h-2 mr-2">
                            <div
                              className="bg-indigo-600 h-2 rounded-full"
                              style={{ width: `${getStrengthScore(primaryBrand.label)}%` }}
                            />
                          </div>
                          <span className="text-sm text-gray-900">{getStrengthScore(primaryBrand.label)}</span>
                        </div>
                      </td>
                    </tr>
                  )}
                  {competitors.map((result, idx) => (
                    <tr key={idx}>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                        {result.brand}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center space-x-2">
                          {getStrengthIcon(result.strength)}
                          <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStrengthColor(result.strength)}`}>
                            {getStrengthLabel(result.strength)}
                          </span>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {result.confidence}%
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center">
                          <div className="w-24 bg-gray-200 rounded-full h-2 mr-2">
                            <div
                              className="bg-blue-600 h-2 rounded-full"
                              style={{ width: `${getStrengthScore(result.strength)}%` }}
                            />
                          </div>
                          <span className="text-sm text-gray-900">{getStrengthScore(result.strength)}</span>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {/* Insights */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <h4 className="text-sm font-medium text-blue-900 mb-2">Entity Strength Score Guide</h4>
        <div className="text-sm text-blue-700 space-y-2">
          <p>
            <strong>100 - Strong Entity:</strong> AI has specific, verifiable knowledge. Major brands with extensive training data.
          </p>
          <p>
            <strong>60 - Weak Entity:</strong> AI recognizes the name or industry context but lacks specific details.
          </p>
          <p>
            <strong>5 - Unknown:</strong> AI has no knowledge of this brand. Cannot provide any meaningful information.
          </p>
          <p>
            <strong>0 - No Response:</strong> AI cannot or will not provide information.
          </p>
          <p className="pt-2 font-medium">
            💡 Only brands with scores above 60 have meaningful AI visibility. Scores below 10 indicate zero AI knowledge.
          </p>
        </div>
      </div>
    </div>
  )
}