'use client'

import { useState, useEffect } from 'react'
import { CheckCircleIcon, XCircleIcon, QuestionMarkCircleIcon, ExclamationTriangleIcon, ShieldCheckIcon } from '@heroicons/react/24/outline'

interface EntityClassification {
  label: 'KNOWN_STRONG' | 'KNOWN_WEAK' | 'UNKNOWN' | 'EMPTY' | 'CONFUSED'
  confidence: number
  reasoning: string
  natural_response?: string  // The unbiased response from Step 1 (v2)
  response_text?: string  // The AI's natural language response (v1)
  classifier_analysis?: {  // Analysis from Step 2 (v2)
    specific_facts: number
    generic_claims: number
    entities_mentioned: number
    multiple_entities: boolean
    classification: string
    confidence: number
    reasoning: string
  }
  specific_facts_count?: number  // v2
  generic_claims_count?: number  // v2
  entities_mentioned?: string[]  // v2
  specific_claims?: string[]  // v1
  generic_claims?: string[]  // v1
  disambiguation_needed?: boolean
  confusion_detected?: boolean
  confusion_type?: string
  ai_thinks_industry?: string
  actual_industry?: string
  other_entities_list?: string[]
  methodology?: 'single-step' | 'two-step'
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
  const [brandDomain, setBrandDomain] = useState<string>('')
  const [loading, setLoading] = useState(false)
  const [batchLoading, setBatchLoading] = useState(false)
  const [vendor, setVendor] = useState('google')  // Default to Google Gemini as GPT models return empty
  const [duplicateWarning, setDuplicateWarning] = useState<string>('')

  // Don't automatically check on mount - wait for user to click button
  // useEffect(() => {
  //   if (brandName) {
  //     checkBrandStrength(brandName)
  //   }
  // }, [brandName])

  const checkBrandStrength = async (brand: string) => {
    setLoading(true)
    try {
      // Create an AbortController for timeout
      const controller = new AbortController()
      // Set timeout to 120 seconds for GPT-5 (which is slow)
      const timeoutId = setTimeout(() => controller.abort(), 120000)
      
      // Use the new v2 endpoint for two-step approach
      const response = await fetch('http://localhost:8000/api/brand-entity-strength-v2', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          brand_name: brand,
          domain: brandDomain || undefined,
          information_vendor: vendor,  // Changed from 'vendor' to 'information_vendor'
          classifier_vendor: 'openai'  // Always use GPT-4o-mini for classification
        }),
        signal: controller.signal
      })
      
      clearTimeout(timeoutId)

      if (response.ok) {
        const data = await response.json()
        console.log('API Response received:', data)
        console.log('Classification object:', data.classification)
        console.log('Raw response exists?', !!data.raw_response)
        console.log('Specific claims count:', data.classification?.specific_claims?.length || 0)
        
        if (data && data.classification) {
          console.log('Setting primary brand with:', data.classification)
          // Force a state reset first to ensure re-render
          setPrimaryBrand(null)
          setTimeout(() => {
            setPrimaryBrand(data.classification)
            console.log('State update triggered with delay')
          }, 10)
        } else {
          console.error('Invalid response structure:', data)
          alert('Invalid response structure from API')
        }
      } else {
        const errorText = await response.text()
        console.error('API Error:', response.status, errorText)
        alert(`Error: ${response.status} - ${errorText}`)
      }
    } catch (error: any) {
      console.error('Error checking brand strength:', error)
      if (error.name === 'AbortError') {
        alert('Request timed out after 2 minutes. GPT-5 is very slow - please try again or use Google (Gemini) for faster results.')
      } else {
        alert(`Network error: ${error.message || error}`)
      }
    }
    setLoading(false)
  }

  const checkCompetitors = async () => {
    if (!customBrands.trim()) return

    setDuplicateWarning('') // Clear any previous warnings
    
    const brands = customBrands.split(',').map(b => b.trim()).filter(b => b)
    
    // Check for duplicates before making API call
    const existingBrands = new Set(competitors.map(c => c.brand.toLowerCase()))
    // Also check against the primary brand
    if (brandName) {
      existingBrands.add(brandName.toLowerCase())
    }
    
    const duplicates = brands.filter(b => existingBrands.has(b.toLowerCase()))
    const newBrands = brands.filter(b => !existingBrands.has(b.toLowerCase()))
    
    if (duplicates.length > 0) {
      setDuplicateWarning(`Already in list: ${duplicates.join(', ')}`)
      
      // If all brands are duplicates, don't make API call
      if (newBrands.length === 0) {
        return
      }
      
      // Update input to only show new brands
      setCustomBrands(newBrands.join(', '))
      return
    }

    setBatchLoading(true)
    
    try {
      const response = await fetch('http://localhost:8000/api/brand-entity-strength-v2/batch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          brands: newBrands,
          information_vendor: vendor
        })
      })

      if (response.ok) {
        const data = await response.json()
        // Append new results to existing competitors
        setCompetitors(prev => [...prev, ...data.results])
        // Clear the input field after successful addition
        setCustomBrands('')
        setDuplicateWarning('')
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
          <option value="google">Google (Gemini 2.5 Pro) - Recommended</option>
          <option value="openai">OpenAI (GPT-4o) - Currently Broken</option>
        </select>
      </div>

      {/* Primary Brand Analysis */}
      <div className="bg-white rounded-lg shadow-lg p-6">
        <div className="mb-4">
          <h3 className="text-lg font-semibold text-gray-900 mb-3">Your Brand: {brandName}</h3>
          
          {/* Domain input field */}
          <div className="flex items-center space-x-3 mb-3">
            <label className="text-sm font-medium text-gray-700 whitespace-nowrap">
              Your Website:
            </label>
            <input
              type="text"
              value={brandDomain}
              onChange={(e) => {
                // Clean the domain - remove https://, http://, trailing slashes
                let domain = e.target.value.trim()
                domain = domain.replace(/^https?:\/\//, '') // Remove http:// or https://
                domain = domain.replace(/\/$/, '') // Remove trailing slash
                setBrandDomain(domain)
              }}
              placeholder="example.com or www.example.com"
              className="flex-1 rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
            />
            <button
              onClick={() => checkBrandStrength(brandName)}
              className="px-4 py-2 text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 rounded-md disabled:opacity-50"
              disabled={loading || !brandName}
            >
              {loading ? 'Checking...' : 'Check Strength'}
            </button>
          </div>
          <div className="text-xs text-gray-500 mb-2">
            <p>• Enter domain without https:// (e.g., "avea-life.com" or "www.avea-life.com")</p>
            {brandDomain && (
              <p>• We'll verify the AI is talking about YOUR {brandName}, not another company with the same name</p>
            )}
          </div>
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
              <div className={`rounded-lg p-4 ${
                primaryBrand.reasoning.toLowerCase().includes('wrong') || 
                primaryBrand.reasoning.toLowerCase().includes('confusion') ||
                primaryBrand.reasoning.toLowerCase().includes('different') ||
                primaryBrand.reasoning.toLowerCase().includes('but actual brand') ?
                'bg-amber-50 border border-amber-200' : 'bg-gray-50'
              }`}>
                {(primaryBrand.reasoning.toLowerCase().includes('wrong') || 
                  primaryBrand.reasoning.toLowerCase().includes('but actual brand')) && (
                  <div className="flex items-start mb-2">
                    <ExclamationTriangleIcon className="h-5 w-5 text-amber-600 mr-2 mt-0.5" />
                    <h4 className="text-sm font-semibold text-amber-900">Entity Confusion Detected</h4>
                  </div>
                )}
                <p className="text-sm text-gray-700">{primaryBrand.reasoning}</p>
              </div>
            )}

            {/* Show disambiguation warning if multiple entities share the name */}
            {primaryBrand.disambiguation_needed && primaryBrand.other_entities_list && primaryBrand.other_entities_list.length > 0 && (
              <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 mb-4">
                <div className="flex items-start mb-3">
                  <ExclamationTriangleIcon className="h-6 w-6 text-amber-600 mr-2" />
                  <div className="flex-1">
                    <h4 className="text-sm font-semibold text-amber-900 mb-1">
                      Brand Name Conflict - Multiple Entities Share This Name
                    </h4>
                    <p className="text-sm text-amber-800 mb-2">
                      AI identified {primaryBrand.other_entities_list.length} different entities named "{brandName}"
                    </p>
                  </div>
                </div>
                <div className="bg-white bg-opacity-50 rounded p-3 mb-3">
                  <h5 className="text-xs font-semibold text-amber-900 mb-2 uppercase">Other Entities With Same Name:</h5>
                  <ul className="text-sm text-amber-700 space-y-1">
                    {primaryBrand.other_entities_list.slice(0, 5).map((entity, idx) => (
                      <li key={idx}>• {entity}</li>
                    ))}
                  </ul>
                </div>
                <div className="bg-white bg-opacity-50 rounded p-3">
                  <h5 className="text-xs font-semibold text-amber-900 mb-2 uppercase">Impact on Your Brand:</h5>
                  <ul className="text-sm text-amber-700 space-y-1">
                    <li>• Your brand lacks unique recognition in AI systems</li>
                    <li>• Users must provide additional context to find your company</li>
                    <li>• AI may provide information about the wrong entity</li>
                    <li>• Brand strength is significantly weakened by name confusion</li>
                  </ul>
                </div>
              </div>
            )}

            {/* Show confusion details if detected */}
            {primaryBrand.confusion_detected && !primaryBrand.disambiguation_needed && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-4">
                <div className="flex items-start mb-3">
                  <ExclamationTriangleIcon className="h-6 w-6 text-red-600 mr-2" />
                  <div className="flex-1">
                    <h4 className="text-sm font-semibold text-red-900 mb-1">
                      Entity Confusion Detected - AI is Identifying Wrong Company
                    </h4>
                    {primaryBrand.ai_thinks_industry && primaryBrand.actual_industry && (
                      <p className="text-sm text-red-800 mb-2">
                        AI thinks your brand is in <strong>{primaryBrand.ai_thinks_industry}</strong>, 
                        but you actually operate in <strong>{primaryBrand.actual_industry}</strong>
                      </p>
                    )}
                  </div>
                </div>
                <div className="bg-white bg-opacity-50 rounded p-3 mb-3">
                  <h5 className="text-xs font-semibold text-red-900 mb-2 uppercase">Impact on Your Brand:</h5>
                  <ul className="text-sm text-red-700 space-y-1">
                    <li>• AI assistants will provide wrong information about your company</li>
                    <li>• Potential customers won't find your actual products/services</li>
                    <li>• Your brand's AI visibility score is effectively zero</li>
                    <li>• Competitors with clear AI recognition have a major advantage</li>
                  </ul>
                </div>
                {primaryBrand.confusion_type === 'mixed_entities' && (
                  <p className="text-xs text-red-600 italic">
                    Note: The AI appears to be mixing multiple companies with similar names.
                  </p>
                )}
              </div>
            )}

            {/* Claims - Handle both v1 and v2 formats */}
            <div className="grid grid-cols-2 gap-4">
              {/* For v2: Show facts count and entities */}
              {primaryBrand.methodology === 'two-step' ? (
                <>
                  <div>
                    <h4 className="text-sm font-medium text-gray-700 mb-2">Knowledge Quality</h4>
                    <div className="space-y-1 text-sm text-gray-600">
                      <div>• Specific Facts: {primaryBrand.specific_facts_count || 0}</div>
                      <div>• Generic Claims: {primaryBrand.generic_claims_count || 0}</div>
                      <div>• Fact Ratio: {
                        primaryBrand.specific_facts_count && (primaryBrand.specific_facts_count + (primaryBrand.generic_claims_count || 0)) > 0
                          ? Math.round((primaryBrand.specific_facts_count / (primaryBrand.specific_facts_count + (primaryBrand.generic_claims_count || 0))) * 100)
                          : 0
                      }%</div>
                    </div>
                  </div>
                  {primaryBrand.entities_mentioned && primaryBrand.entities_mentioned.length > 0 && (
                    <div>
                      <h4 className="text-sm font-medium text-gray-700 mb-2">Entities Detected</h4>
                      <ul className="list-disc list-inside text-sm text-gray-600 space-y-1">
                        {primaryBrand.entities_mentioned.slice(0, 3).map((entity, idx) => (
                          <li key={idx}>{entity}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </>
              ) : (
                <>
                  {/* For v1: Show specific and generic claims */}
                  {primaryBrand.specific_claims && primaryBrand.specific_claims.length > 0 && (
                    <div>
                      <h4 className="text-sm font-medium text-gray-700 mb-2">
                        {primaryBrand.reasoning && primaryBrand.reasoning.toLowerCase().includes('but actual brand') 
                          ? "What AI Thinks (WRONG)" 
                          : "Specific Knowledge"}
                      </h4>
                      <ul className="list-disc list-inside text-sm text-gray-600 space-y-1">
                        {primaryBrand.specific_claims.slice(0, 3).map((claim, idx) => (
                          <li key={idx}>{claim}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {primaryBrand.generic_claims && primaryBrand.generic_claims.length > 0 && (
                    <div>
                      <h4 className="text-sm font-medium text-gray-700 mb-2">Generic Claims</h4>
                      <ul className="list-disc list-inside text-sm text-gray-600 space-y-1">
                        {primaryBrand.generic_claims.slice(0, 3).map((claim, idx) => (
                          <li key={idx}>{claim}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </>
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
                onChange={(e) => {
                  setCustomBrands(e.target.value)
                  setDuplicateWarning('') // Clear warning when user types
                }}
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
            {duplicateWarning && (
              <p className="mt-2 text-sm text-amber-600">
                ⚠️ {duplicateWarning}
              </p>
            )}
          </div>

          {/* Clear button when competitors exist */}
          {competitors.length > 0 && (
            <div className="flex justify-end">
              <button
                onClick={() => setCompetitors([])}
                className="text-sm text-gray-500 hover:text-gray-700 underline"
              >
                Clear all competitors
              </button>
            </div>
          )}

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

      {/* Raw AI Response */}
      {primaryBrand && (
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
          <h4 className="text-sm font-medium text-gray-900 mb-3">
            AI Model Response {primaryBrand.methodology === 'two-step' && <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded ml-2">Two-Step Analysis</span>}
          </h4>
          
          {/* Show the AI's actual response text if available */}
          {(primaryBrand.natural_response || primaryBrand.response_text) && (
            <div className="mb-4 p-3 bg-white rounded-lg border border-gray-300">
              <h5 className="text-xs font-semibold text-gray-700 mb-2 uppercase">
                {primaryBrand.methodology === 'two-step' ? 'Step 1: Natural AI Response' : 'What the AI Said:'}
              </h5>
              <p className="text-sm text-gray-800 whitespace-pre-wrap">{primaryBrand.natural_response || primaryBrand.response_text}</p>
            </div>
          )}
          
          {/* Show classifier analysis for two-step */}
          {primaryBrand.methodology === 'two-step' && primaryBrand.classifier_analysis && (
            <div className="mb-4 p-3 bg-blue-50 rounded-lg border border-blue-200">
              <h5 className="text-xs font-semibold text-blue-900 mb-2 uppercase">Step 2: Classification Analysis (GPT-4o-mini)</h5>
              <div className="grid grid-cols-2 gap-2 text-sm">
                <div>
                  <span className="font-medium text-blue-700">Specific Facts:</span>{' '}
                  <span className="text-blue-900">{primaryBrand.classifier_analysis.specific_facts}</span>
                </div>
                <div>
                  <span className="font-medium text-blue-700">Generic Claims:</span>{' '}
                  <span className="text-blue-900">{primaryBrand.classifier_analysis.generic_claims}</span>
                </div>
                <div>
                  <span className="font-medium text-blue-700">Entities Found:</span>{' '}
                  <span className="text-blue-900">{primaryBrand.classifier_analysis.entities_mentioned}</span>
                </div>
                <div>
                  <span className="font-medium text-blue-700">Multiple Entities:</span>{' '}
                  <span className="text-blue-900">{primaryBrand.classifier_analysis.multiple_entities ? 'Yes' : 'No'}</span>
                </div>
              </div>
              <div className="mt-2">
                <span className="font-medium text-blue-700 text-sm">Classifier Reasoning:</span>{' '}
                <span className="text-blue-900 text-sm">{primaryBrand.classifier_analysis.reasoning}</span>
              </div>
            </div>
          )}
          
          <div className="space-y-2 text-sm">
            <div>
              <span className="font-medium text-gray-700">Classification:</span>{' '}
              <span className="text-gray-900">{primaryBrand.label}</span>
            </div>
            <div>
              <span className="font-medium text-gray-700">Confidence:</span>{' '}
              <span className="text-gray-900">{primaryBrand.confidence}%</span>
            </div>
            {primaryBrand.reasoning && (
              <div>
                <span className="font-medium text-gray-700">System Analysis:</span>{' '}
                <span className="text-gray-900">{primaryBrand.reasoning}</span>
              </div>
            )}
            {primaryBrand.disambiguation_needed && (
              <div>
                <span className="font-medium text-gray-700">Disambiguation Required:</span>{' '}
                <span className="text-orange-600">Yes - Multiple entities share this name</span>
              </div>
            )}
            {primaryBrand.confusion_detected && (
              <div>
                <span className="font-medium text-gray-700">Confusion Type:</span>{' '}
                <span className="text-red-600">{primaryBrand.confusion_type || 'Entity mismatch detected'}</span>
              </div>
            )}
            <details className="mt-3">
              <summary className="cursor-pointer text-gray-600 hover:text-gray-900">
                View Full JSON Response
              </summary>
              <pre className="mt-2 p-3 bg-white rounded border border-gray-300 text-xs overflow-x-auto">
                {JSON.stringify(primaryBrand, null, 2)}
              </pre>
            </details>
          </div>
        </div>
      )}

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