'use client'

import { useState, useEffect } from 'react'
import { trackedPhrasesApi } from '@/lib/api'

interface SettingsProps {
  brandId: number
  brandName: string
}

export default function Settings({ brandId, brandName }: SettingsProps) {
  const [bulkPhrases, setBulkPhrases] = useState('')
  const [savedPhrases, setSavedPhrases] = useState<string[]>([])
  const [message, setMessage] = useState('')
  const [useCanonical, setUseCanonical] = useState(false)
  const [numRuns, setNumRuns] = useState(12)
  const [analysisVendor, setAnalysisVendor] = useState('openai')

  useEffect(() => {
    // Load saved phrases from localStorage
    const stored = localStorage.getItem('trackedPhrases')
    if (stored) {
      setSavedPhrases(JSON.parse(stored))
    }
  }, [])

  // Adjust recommended runs based on vendor
  useEffect(() => {
    if (analysisVendor === 'openai') {
      setNumRuns(6) // Fewer runs for GPT-5 (fixed temperature)
    } else {
      setNumRuns(12) // More runs for Gemini (varied temperatures)
    }
  }, [analysisVendor])

  const handleBulkImport = async () => {
    console.log('Import button clicked')
    console.log('Current bulk phrases:', bulkPhrases)
    
    if (!bulkPhrases.trim()) {
      setMessage('Please enter phrases to import')
      setTimeout(() => setMessage(''), 3000)
      return
    }

    const phrases = bulkPhrases
      .split('\n')
      .map(p => p.trim())
      .filter(p => p.length > 0)

    console.log('Parsed phrases:', phrases)

    try {
      // Save to backend
      await trackedPhrasesApi.bulkCreate(brandId, phrases)
      
      // Also save to localStorage for quick access
      const allPhrases = [...new Set([...savedPhrases, ...phrases])]
      localStorage.setItem('trackedPhrases', JSON.stringify(allPhrases))
      setSavedPhrases(allPhrases)
      
      setMessage(`Successfully imported ${phrases.length} phrases. Total: ${allPhrases.length} phrases`)
      setBulkPhrases('')
    } catch (error) {
      console.error('Failed to save to backend:', error)
      // Still save locally even if backend fails
      const allPhrases = [...new Set([...savedPhrases, ...phrases])]
      localStorage.setItem('trackedPhrases', JSON.stringify(allPhrases))
      setSavedPhrases(allPhrases)
      
      setMessage(`Saved ${phrases.length} phrases locally`)
      setBulkPhrases('')
    }
    
    // Clear message after 3 seconds
    setTimeout(() => setMessage(''), 3000)
  }

  const removePhrase = (phrase: string) => {
    const updated = savedPhrases.filter(p => p !== phrase)
    localStorage.setItem('trackedPhrases', JSON.stringify(updated))
    setSavedPhrases(updated)
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-gray-900 mb-2">Settings</h2>
        <p className="text-gray-600">
          Add tracked phrases to see how AI models respond when people search for these terms.
        </p>
        <div className="mt-4 p-4 bg-blue-50 rounded-lg border border-blue-200">
          <p className="text-sm text-blue-800">
            <strong>How it works:</strong> Enter phrases your customers might search for (e.g., "best longevity supplements", "NMN products", "anti-aging solutions"). 
            AI Ranker will query multiple AI models with these phrases and show you which brands they recommend.
          </p>
        </div>
      </div>

      {/* Bulk Import Section */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold mb-4">Bulk Import Tracked Phrases</h3>
        <p className="text-sm text-gray-600 mb-4">
          Enter one phrase per line. These will be tracked across all AI models.
        </p>
        
        <textarea
          value={bulkPhrases}
          onChange={(e) => setBulkPhrases(e.target.value)}
          placeholder="best longevity supplements
NMN supplements
NAD+ boosters
anti-aging products
cellular health supplements
mitochondrial support
resveratrol benefits
healthspan extension"
          className="w-full h-48 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
        />
        
        {message && (
          <div className={`mt-2 text-sm ${message.includes('Success') ? 'text-green-600' : 'text-red-600'}`}>
            {message}
          </div>
        )}
        
        <button
          onClick={handleBulkImport}
          className="mt-4 px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700"
        >
          Import Phrases
        </button>
      </div>

      {/* Saved Phrases */}
      {savedPhrases.length > 0 && (
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold">
              Tracked Phrases ({savedPhrases.length})
            </h3>
            <button
              onClick={async () => {
                if (!brandName) {
                  setMessage('Please enter a brand name first')
                  setTimeout(() => setMessage(''), 3000)
                  return
                }
                
                if (savedPhrases.length === 0) {
                  setMessage('Please add some phrases first')
                  setTimeout(() => setMessage(''), 3000)
                  return
                }
                
                setMessage('🔄 Querying AI models... (this may take a moment)')
                
                try {
                  console.log('Starting analysis for:', brandName)
                  console.log('Phrases to analyze:', savedPhrases)
                  
                  // Add delay to show it's working
                  await new Promise(resolve => setTimeout(resolve, 1000))
                  
                  // Try real analysis first, fall back to simple if it fails
                  let endpoint = 'http://localhost:8000/api/real-analysis'
                  let response = await fetch(endpoint, {
                    method: 'POST',
                    headers: {
                      'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                      brand_name: brandName,
                      phrases: savedPhrases
                    })
                  })
                  
                  if (!response.ok) {
                    const errorText = await response.text()
                    throw new Error(`HTTP ${response.status}: ${errorText}`)
                  }
                  
                  const data = await response.json()
                  console.log('✅ Analysis results received:', data)
                  
                  // Validate the response
                  if (!data.entities || !data.competitor_brands || !data.analysis_results) {
                    throw new Error('Invalid response format from backend')
                  }
                  
                  // Aggregate brand mentions from all vendor results
                  const brandCounts: Record<string, {count: number, positions: number[]}> = {}
                  
                  data.analysis_results.forEach((result: any) => {
                    result.brands_found.forEach((brand: string, index: number) => {
                      if (!brandCounts[brand]) {
                        brandCounts[brand] = { count: 0, positions: [] }
                      }
                      brandCounts[brand].count++
                      brandCounts[brand].positions.push(index + 1)
                    })
                  })
                  
                  // Only add user's brand if it actually appeared in results
                  const userBrandMentions = data.analysis_results.filter((r: any) => r.brand_mentioned).length
                  if (userBrandMentions > 0) {
                    const positions = data.analysis_results
                      .filter((r: any) => r.position)
                      .map((r: any) => r.position)
                    
                    // Only add if positions exist
                    if (positions.length > 0) {
                      brandCounts[brandName] = {
                        count: userBrandMentions,
                        positions: positions
                      }
                    }
                  }
                  
                  // Convert to sorted array for AI Visibility
                  const sortedBrands = Object.entries(brandCounts)
                    .sort(([, a], [, b]) => b.count - a.count)
                    .slice(0, 15)
                    .map(([brand, stats], i) => ({
                      brand,
                      frequency: stats.count,
                      avg_position: stats.positions.reduce((a, b) => a + b, 0) / stats.positions.length,
                      weighted_score: Math.max(0.2, 1 - (i * 0.06))
                    }))
                  
                  // Store results for AI Visibility tab
                  const aiVisData = {
                    entities: data.entities.map((e: string, i: number) => ({
                      entity: e,
                      frequency: Math.max(5, 20 - i * 2),
                      avg_position: 1 + (i * 0.3),
                      weighted_score: Math.max(0.2, 0.9 - (i * 0.08))
                    })),
                    brands: sortedBrands
                  }
                  
                  localStorage.setItem(`analysis_${brandName}`, JSON.stringify(aiVisData))
                  console.log('✅ Stored AI Visibility data')
                  
                  // Store analysis results for vendor tabs
                  localStorage.setItem(`analysis_results_${brandName}`, JSON.stringify(data.analysis_results))
                  console.log(`✅ Stored ${data.analysis_results.length} vendor results`)
                  
                  // Count results by vendor
                  const vendorCounts: Record<string, number> = {}
                  data.analysis_results.forEach((r: any) => {
                    vendorCounts[r.vendor] = (vendorCounts[r.vendor] || 0) + 1
                  })
                  
                  setMessage(`✅ Analysis complete! Found results from: ${Object.entries(vendorCounts).map(([v, c]) => `${v} (${c})`).join(', ')}`)
                  
                  // Dispatch custom event
                  window.dispatchEvent(new CustomEvent('analysisComplete', { detail: { brandName } }))
                  
                } catch (error: any) {
                  console.error('❌ Analysis failed:', error)
                  setMessage(`❌ Analysis failed: ${error.message}`)
                }
                
                setTimeout(() => setMessage(''), 8000)
              }}
              className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:bg-gray-400"
              disabled={message.includes('Querying')}
            >
              {message.includes('Querying') ? '⏳ Running...' : 'Run AI Analysis'}
            </button>
            
            <button
              onClick={async () => {
                // TEST WITH ACTUAL API CALL
                console.log('Vector Analysis button clicked!')
                
                // Check prerequisites
                if (!brandName) {
                  setMessage('Please enter a brand name first')
                  setTimeout(() => setMessage(''), 3000)
                  return
                }
                
                if (savedPhrases.length === 0) {
                  setMessage('Please add some phrases first')
                  setTimeout(() => setMessage(''), 3000)
                  return
                }
                
                try {
                  // Step 1: Show starting message
                  setMessage('📝 Step 1/4: Querying OpenAI about ' + brandName + '...')
                  console.log('Step 1 message set')
                  
                  // Make the API call
                  console.log('Making API call to entity-beeb endpoint...')
                  
                  const openaiResponse = await fetch('http://localhost:8000/api/entity-beeb', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                      brand_name: brandName,
                      tracked_phrases: savedPhrases.slice(0, 2), // Send first 2 phrases for brand associations
                      vendor: 'openai'
                    })
                  })
                  
                  console.log('Response received:', openaiResponse.status)
                  
                  if (!openaiResponse.ok) {
                    const errorText = await openaiResponse.text()
                    console.error('Response error:', errorText)
                    throw new Error(`OpenAI HTTP ${openaiResponse.status}: ${errorText}`)
                  }
                  
                  const openaiData = await openaiResponse.json()
                  console.log('✅ OpenAI entity extraction complete:', openaiData)
                  
                  // Step 2: Show extraction results
                  setMessage(`🔍 Step 2/4: Extracted ${openaiData.extracted_entities?.length || 0} entities`)
                  await new Promise(resolve => setTimeout(resolve, 2000))
                  
                  // Step 3: Show embedding calculation
                  setMessage('📊 Step 3/4: Calculated embedding similarities')
                  await new Promise(resolve => setTimeout(resolve, 2000))
                  
                  // Store OpenAI results
                  if (openaiData.entity_associations) {
                    const openaiStorage = {
                      entities: openaiData.entity_associations,
                      brands: openaiData.brand_associations || [],
                      extracted_entities: openaiData.extracted_entities
                    }
                    localStorage.setItem(`analysis_openai_${brandName}`, JSON.stringify(openaiStorage))
                    localStorage.setItem(`analysis_${brandName}`, JSON.stringify(openaiStorage))
                  }
                  
                  // Step 4: Final message
                  setMessage('✅ Step 4/4: Analysis complete!')
                  await new Promise(resolve => setTimeout(resolve, 2000))
                  
                  // Show summary
                  const summary = `✅ Found ${openaiData.extracted_entities?.length || 0} entities`
                  setMessage(summary)
                  
                  // Clear after 5 seconds
                  setTimeout(() => setMessage(''), 5000)
                  
                } catch (error: any) {
                  console.error('❌ Analysis failed:', error)
                  console.error('Error stack:', error.stack)
                  const errorMsg = error.message || 'Unknown error occurred'
                  setMessage(`❌ Analysis failed: ${errorMsg}`)
                  // Don't clear error messages automatically
                  setTimeout(() => setMessage(''), 15000) // Keep error visible for 15 seconds
                  return // Exit early on error
                }
              }}
              className="ml-2 px-4 py-2 bg-purple-600 text-white rounded-md hover:bg-purple-700"
            >
              Run Vector Analysis (BEEB)
            </button>
            
            <button
              onClick={async () => {
                // NEW: Contestra V2 Analysis with prompted lists
                if (!brandName) {
                  setMessage('Please enter a brand name first')
                  setTimeout(() => setMessage(''), 3000)
                  return
                }
                
                try {
                  setMessage(`🚀 Starting Contestra V2 Analysis (${numRuns} runs)...`)
                  
                  const response = await fetch('http://localhost:8000/api/contestra-v2', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                      brand_name: brandName,
                      direction: 'brand_to_entity',
                      vendor: analysisVendor,
                      mode: 'ungrounded',
                      num_runs: numRuns,
                      top_k: 10,
                      tracked_phrases: savedPhrases.slice(0, 2),
                      use_canonical: useCanonical
                    })
                  })
                  
                  if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`)
                  }
                  
                  const data = await response.json()
                  console.log('Contestra V2 Results:', data)
                  
                  // Store results
                  const storage = {
                    entities: data.entities.map((e: any) => ({
                      entity: e.name,
                      frequency: e.frequency,
                      avg_position: e.avg_position,
                      weighted_score: e.weighted_score,
                      variants: e.variants
                    })),
                    brand_associations: data.brand_associations || [],
                    metadata: data.metadata,
                    method: 'contestra_v2'
                  }
                  
                  localStorage.setItem(`contestra_v2_${brandName}`, JSON.stringify(storage))
                  localStorage.setItem(`analysis_${brandName}`, JSON.stringify(storage))
                  
                  // Save weekly tracking data
                  try {
                    // Prepare entity rankings (top 10)
                    const entityRankings: Record<string, number> = {}
                    data.entities.slice(0, 10).forEach((entity: any, index: number) => {
                      entityRankings[entity.entity] = index + 1
                    })
                    
                    // Prepare brand rankings per phrase
                    const brandRankings: Record<string, Record<string, number>> = {}
                    if (data.brand_associations && data.brand_associations.length > 0) {
                      // Group by phrase
                      const phraseGroups: Record<string, any[]> = {}
                      data.brand_associations.forEach((assoc: any) => {
                        if (!phraseGroups[assoc.phrase]) {
                          phraseGroups[assoc.phrase] = []
                        }
                        phraseGroups[assoc.phrase].push(assoc)
                      })
                      
                      // Get rankings per phrase
                      Object.entries(phraseGroups).forEach(([phrase, assocs]) => {
                        brandRankings[phrase] = {}
                        assocs.sort((a, b) => a.position - b.position)
                        assocs.slice(0, 10).forEach((assoc, index) => {
                          brandRankings[phrase][assoc.brand] = index + 1
                        })
                      })
                    }
                    
                    // Send to weekly tracking API
                    await fetch('http://localhost:8000/api/weekly-tracking/update', {
                      method: 'POST',
                      headers: { 'Content-Type': 'application/json' },
                      body: JSON.stringify({
                        brand_name: brandName,
                        vendor: 'openai',
                        entity_rankings: entityRankings,
                        brand_rankings: brandRankings
                      })
                    })
                    console.log('Weekly tracking data saved successfully')
                  } catch (trackingError) {
                    console.error('Failed to save weekly tracking:', trackingError)
                  }
                  
                  setMessage(`✅ Contestra V2 Complete! Found ${data.entities.length} entities from ${data.num_runs} runs`)
                  
                  // Dispatch event for UI update
                  window.dispatchEvent(new CustomEvent('analysisComplete', { detail: { brandName, method: 'contestra_v2' } }))
                  
                  setTimeout(() => setMessage(''), 5000)
                  
                } catch (error: any) {
                  console.error('Contestra V2 failed:', error)
                  setMessage(`❌ Analysis failed: ${error.message}`)
                  setTimeout(() => setMessage(''), 10000)
                }
              }}
              className="ml-2 px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700"
            >
              Run Contestra V2 Analysis (New!)
            </button>
            
            <button
              onClick={async () => {
                // Grounded vs Ungrounded comparison for Google Gemini
                if (!brandName) {
                  setMessage('Please enter a brand name first')
                  setTimeout(() => setMessage(''), 3000)
                  return
                }
                
                try {
                  setMessage(`🔬 Running Grounded vs Ungrounded comparison (Google Gemini, ${numRuns} runs each)...`)
                  
                  const response = await fetch('http://localhost:8000/api/contestra-v2/compare', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                      brand_name: brandName,
                      direction: 'brand_to_entity',
                      vendor: 'google',
                      mode: 'ungrounded', // Will be overridden in the endpoint
                      num_runs: numRuns,
                      top_k: 10,
                      tracked_phrases: savedPhrases.slice(0, 2),
                      use_canonical: useCanonical
                    })
                  })
                  
                  if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`)
                  }
                  
                  const data = await response.json()
                  console.log('Grounded vs Ungrounded Results:', data)
                  
                  // Store both result sets
                  if (data.ungrounded) {
                    const ungroundedStorage = {
                      entities: data.ungrounded.entities.map((e: any) => ({
                        entity: e.name,
                        frequency: e.frequency,
                        avg_position: e.avg_position,
                        weighted_score: e.weighted_score,
                        variants: e.variants
                      })),
                      brand_associations: data.ungrounded.brand_associations || [],
                      metadata: data.ungrounded.metadata,
                      method: 'contestra_v2_ungrounded'
                    }
                    localStorage.setItem(`google_ungrounded_${brandName}`, JSON.stringify(ungroundedStorage))
                  }
                  
                  if (data.grounded) {
                    const groundedStorage = {
                      entities: data.grounded.entities.map((e: any) => ({
                        entity: e.name,
                        frequency: e.frequency,
                        avg_position: e.avg_position,
                        weighted_score: e.weighted_score,
                        variants: e.variants
                      })),
                      brand_associations: data.grounded.brand_associations || [],
                      metadata: data.grounded.metadata,
                      method: 'contestra_v2_grounded'
                    }
                    localStorage.setItem(`google_grounded_${brandName}`, JSON.stringify(groundedStorage))
                  }
                  
                  // Compute comparison metrics
                  const ungroundedEntities = data.ungrounded?.entities || []
                  const groundedEntities = data.grounded?.entities || []
                  
                  const ungroundedSet = new Set(ungroundedEntities.map((e: any) => e.name.toLowerCase()))
                  const groundedSet = new Set(groundedEntities.map((e: any) => e.name.toLowerCase()))
                  
                  const overlap = Array.from(ungroundedSet).filter(e => groundedSet.has(e)).length
                  const overlapPercent = Math.round((overlap / Math.max(ungroundedSet.size, groundedSet.size)) * 100)
                  
                  setMessage(`✅ Comparison Complete! Ungrounded: ${ungroundedEntities.length} entities, Grounded: ${groundedEntities.length} entities, Overlap: ${overlapPercent}%`)
                  
                  // Dispatch event for UI update
                  window.dispatchEvent(new CustomEvent('comparisonComplete', { 
                    detail: { 
                      brandName, 
                      ungrounded: data.ungrounded,
                      grounded: data.grounded
                    } 
                  }))
                  
                  setTimeout(() => setMessage(''), 8000)
                  
                } catch (error: any) {
                  console.error('Comparison failed:', error)
                  setMessage(`❌ Comparison failed: ${error.message}`)
                  setTimeout(() => setMessage(''), 10000)
                }
              }}
              className="ml-2 px-4 py-2 bg-purple-600 text-white rounded-md hover:bg-purple-700"
            >
              Compare Grounded vs Ungrounded (Google)
            </button>
          </div>
          <div className="space-y-2 max-h-60 overflow-y-auto">
            {savedPhrases.map((phrase, index) => (
              <div key={index} className="flex items-center justify-between p-2 bg-gray-50 rounded">
                <span className="text-sm text-gray-700">{phrase}</span>
                <button
                  onClick={() => removePhrase(phrase)}
                  className="text-red-500 hover:text-red-700 text-sm"
                >
                  Remove
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Model Configuration */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold mb-4">Model Configuration</h3>
        
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              OpenAI Model
            </label>
            <select className="w-full px-3 py-2 border border-gray-300 rounded-md">
              <option value="gpt-5">GPT-5</option>
            </select>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Google Model
            </label>
            <select className="w-full px-3 py-2 border border-gray-300 rounded-md">
              <option value="gemini-2.5-pro">Gemini 2.5 Pro</option>
            </select>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Anthropic Model
            </label>
            <select className="w-full px-3 py-2 border border-gray-300 rounded-md">
              <option value="claude-3-5-sonnet">Claude 3.5 Sonnet</option>
              <option value="claude-3-opus">Claude 3 Opus</option>
            </select>
          </div>
        </div>
      </div>

      {/* Contestra V2 Settings */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold mb-4">Contestra V2 Analysis Settings</h3>
        
        <div className="space-y-4">
          {/* Vendor Selection */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              AI Model for Analysis
            </label>
            <select
              value={analysisVendor}
              onChange={(e) => setAnalysisVendor(e.target.value)}
              className="w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
            >
              <option value="openai">OpenAI (GPT-5)</option>
              <option value="google">Google (Gemini 2.5 Pro)</option>
            </select>
          </div>
          
          {/* Temperature Note */}
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 text-sm">
            <p className="text-blue-800">
              {analysisVendor === 'openai' ? (
                <><strong>GPT-5:</strong> Uses fixed temperature (1.0). Recommended: 3-6 runs for basic analysis.</>
              ) : (
                <><strong>Gemini 2.5 Pro:</strong> Uses varied temperatures (0.5, 0.7, 0.9) for diversity. Recommended: 9-15 runs.</>
              )}
            </p>
          </div>
          
          <div className="flex items-center">
            <input
              type="checkbox"
              id="useCanonical"
              checked={useCanonical}
              onChange={(e) => setUseCanonical(e.target.checked)}
              className="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded"
            />
            <label htmlFor="useCanonical" className="ml-2 block text-sm text-gray-700">
              Use Canonical Entities (group similar variants)
            </label>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Number of Runs ({numRuns})
            </label>
            <input
              type="range"
              min="3"
              max="24"
              value={numRuns}
              onChange={(e) => setNumRuns(parseInt(e.target.value))}
              className="w-full"
            />
            <div className="flex justify-between text-xs text-gray-500">
              <span>3 (fast)</span>
              <span>12 (balanced)</span>
              <span>24 (thorough)</span>
            </div>
          </div>
        </div>
      </div>

      {/* Advanced Settings */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold mb-4">Advanced Settings</h3>
        
        <div className="space-y-4">
          <div className="flex items-center">
            <input
              type="checkbox"
              id="canonical"
              defaultChecked
              className="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded"
            />
            <label htmlFor="canonical" className="ml-2 text-sm text-gray-700">
              Use canonical entity resolution
            </label>
          </div>
          
          <div className="flex items-center">
            <input
              type="checkbox"
              id="weekly"
              defaultChecked
              className="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded"
            />
            <label htmlFor="weekly" className="ml-2 text-sm text-gray-700">
              Enable weekly aggregation
            </label>
          </div>
          
          <div className="flex items-center">
            <input
              type="checkbox"
              id="grounded"
              className="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded"
            />
            <label htmlFor="grounded" className="ml-2 text-sm text-gray-700">
              Enable grounded mode analysis
            </label>
          </div>
        </div>
      </div>
    </div>
  )
}