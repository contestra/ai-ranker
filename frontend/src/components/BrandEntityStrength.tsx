'use client'

import { useState, useEffect } from 'react'
import { ExclamationTriangleIcon, CheckCircleIcon, XCircleIcon, QuestionMarkCircleIcon, ShieldCheckIcon } from '@heroicons/react/24/outline'

interface EntityClassification {
  label: 'KNOWN_STRONG' | 'KNOWN_WEAK' | 'UNKNOWN' | 'EMPTY' | 'HALLUCINATED'
  confidence: number
  reasoning?: string
  specific_claims: string[]
  generic_claims: string[]
}

interface BrandEntityStrengthProps {
  brandName: string
  vendor?: string
  onClassificationChange?: (classification: EntityClassification) => void
}

export default function BrandEntityStrength({ brandName, vendor = 'openai', onClassificationChange }: BrandEntityStrengthProps) {
  const [classification, setClassification] = useState<EntityClassification | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [showDetails, setShowDetails] = useState(false)

  const checkEntityStrength = async () => {
    if (!brandName) return
    
    setLoading(true)
    setError('')
    
    try {
      const response = await fetch('http://localhost:8000/api/brand-entity-strength', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          brand_name: brandName,
          vendor: vendor,
          include_reasoning: true
        })
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }

      const data = await response.json()
      setClassification(data.classification)
      
      if (onClassificationChange) {
        onClassificationChange(data.classification)
      }
    } catch (err: any) {
      setError(`Failed to check entity strength: ${err.message}`)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (brandName) {
      checkEntityStrength()
    }
  }, [brandName, vendor])

  const getStrengthIcon = () => {
    if (!classification) return null
    
    switch (classification.label) {
      case 'KNOWN_STRONG':
        return <CheckCircleIcon className="h-6 w-6 text-green-500" />
      case 'KNOWN_WEAK':
        return <ShieldCheckIcon className="h-6 w-6 text-yellow-500" />
      case 'UNKNOWN':
        return <QuestionMarkCircleIcon className="h-6 w-6 text-gray-500" />
      case 'EMPTY':
        return <XCircleIcon className="h-6 w-6 text-red-500" />
      default:
        return null
    }
  }

  const getStrengthColor = () => {
    if (!classification) return 'bg-gray-100'
    
    switch (classification.label) {
      case 'KNOWN_STRONG':
        return 'bg-green-50 border-green-200'
      case 'KNOWN_WEAK':
        return 'bg-yellow-50 border-yellow-200'
      case 'UNKNOWN':
        return 'bg-gray-50 border-gray-200'
      case 'EMPTY':
        return 'bg-red-50 border-red-200'
      default:
        return 'bg-gray-50 border-gray-200'
    }
  }

  const getStrengthLabel = () => {
    if (!classification) return 'Checking...'
    
    switch (classification.label) {
      case 'KNOWN_STRONG':
        return 'Strong Entity'
      case 'KNOWN_WEAK':
        return 'Weak Entity'
      case 'UNKNOWN':
        return 'Unknown Entity'
      case 'HALLUCINATED':
        return 'Hallucinated'
      case 'EMPTY':
        return 'No Data'
      default:
        return 'Unknown'
    }
  }

  const getStrengthDescription = () => {
    if (!classification) return ''
    
    switch (classification.label) {
      case 'KNOWN_STRONG':
        return 'AI has specific, verifiable knowledge about this brand'
      case 'KNOWN_WEAK':
        return 'AI recognizes the brand but has limited specific information'
      case 'UNKNOWN':
        return 'AI has no knowledge of this brand'
      case 'EMPTY':
        return 'AI cannot or will not provide information about this brand'
      default:
        return ''
    }
  }

  if (loading) {
    return (
      <div className="animate-pulse">
        <div className="h-16 bg-gray-100 rounded-lg"></div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="p-3 bg-red-50 text-red-700 rounded-lg text-sm">
        {error}
      </div>
    )
  }

  if (!classification) {
    return null
  }

  return (
    <div className={`p-4 rounded-lg border-2 ${getStrengthColor()}`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          {getStrengthIcon()}
          <div>
            <h3 className="font-semibold text-gray-900">{getStrengthLabel()}</h3>
            <p className="text-sm text-gray-600">{getStrengthDescription()}</p>
          </div>
        </div>
        <div className="flex items-center space-x-3">
          <div className="text-right">
            <p className="text-sm font-medium text-gray-500">Confidence</p>
            <p className="text-2xl font-bold text-gray-900">{classification.confidence}%</p>
          </div>
          <button
            onClick={() => setShowDetails(!showDetails)}
            className="text-sm text-gray-500 hover:text-gray-700"
          >
            {showDetails ? 'Hide' : 'Show'} Details
          </button>
        </div>
      </div>

      {showDetails && (
        <div className="mt-4 pt-4 border-t border-gray-200 space-y-3">
          {classification.reasoning && (
            <div>
              <h4 className="text-sm font-medium text-gray-700 mb-1">Reasoning</h4>
              <p className="text-sm text-gray-600">{classification.reasoning}</p>
            </div>
          )}
          
          {classification.specific_claims.length > 0 && (
            <div>
              <h4 className="text-sm font-medium text-gray-700 mb-1">Specific Claims</h4>
              <ul className="list-disc list-inside text-sm text-gray-600">
                {classification.specific_claims.map((claim, idx) => (
                  <li key={idx}>{claim}</li>
                ))}
              </ul>
            </div>
          )}
          
          {classification.generic_claims.length > 0 && (
            <div>
              <h4 className="text-sm font-medium text-gray-700 mb-1">Generic Claims</h4>
              <ul className="list-disc list-inside text-sm text-gray-600">
                {classification.generic_claims.map((claim, idx) => (
                  <li key={idx}>{claim}</li>
                ))}
              </ul>
            </div>
          )}
          
          <button
            onClick={checkEntityStrength}
            className="text-sm text-indigo-600 hover:text-indigo-700"
          >
            Re-check Entity Strength
          </button>
        </div>
      )}
    </div>
  )
}