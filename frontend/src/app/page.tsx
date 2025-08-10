'use client'

import { useState, useEffect } from 'react'
import AIVisibility from '@/components/AIVisibility'
import ModelComparison from '@/components/ModelComparison'
import Settings from '@/components/Settings'
import TestButton from '@/components/TestButton'
import { brandsApi } from '@/lib/api'

export default function Home() {
  const [brandInput, setBrandInput] = useState('')
  const [brandName, setBrandName] = useState('')
  const [brandId, setBrandId] = useState<number>(1)
  const [activeTab, setActiveTab] = useState<'ai-visibility' | 'openai' | 'google' | 'anthropic' | 'settings'>('ai-visibility')

  const tabs = [
    { id: 'ai-visibility', label: 'AI Visibility', icon: '👁️' },
    { id: 'openai', label: 'OpenAI', icon: '🤖' },
    { id: 'google', label: 'Google', icon: '🔍' },
    // { id: 'anthropic', label: 'Anthropic', icon: '🧠' }, // Disabled - no embeddings API
    { id: 'settings', label: 'Settings', icon: '⚙️' }
  ]

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="flex h-screen">
        {/* Left Sidebar */}
        <div className="w-64 bg-white shadow-lg">
          <div className="p-6 border-b">
            <h1 className="text-2xl font-bold text-gray-900">AI RANKER</h1>
            <p className="text-sm text-gray-500 mt-1">by Contestra</p>
          </div>
          
          <div className="p-4">
            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Enter Your Brand
              </label>
              <div className="flex space-x-2">
                <input
                  type="text"
                  value={brandInput}
                  onChange={(e) => setBrandInput(e.target.value)}
                  onKeyPress={(e) => {
                    if (e.key === 'Enter' && brandInput.trim()) {
                      setBrandName(brandInput.trim())
                    }
                  }}
                  placeholder="e.g., Tesla, Apple, Nike"
                  className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
                />
                <button
                  onClick={async () => {
                    if (brandInput.trim()) {
                      const trimmedName = brandInput.trim()
                      setBrandName(trimmedName)
                      
                      // Create or update brand in backend
                      try {
                        const brand = await brandsApi.create({
                          name: trimmedName,
                          domain: '',
                          aliases: [],
                          category: [],
                          wikidata_qid: null,
                          use_canonical_entities: true
                        })
                        setBrandId(brand.id)
                        console.log('Brand created/updated:', brand)
                      } catch (error) {
                        console.error('Failed to create brand:', error)
                        // Use default ID if creation fails
                        setBrandId(1)
                      }
                    }
                  }}
                  className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                >
                  +
                </button>
              </div>
            </div>
            
            {brandName && (
              <div className="bg-gray-50 rounded-lg p-3 space-y-2">
                <p className="text-sm font-medium text-gray-700">Active Brand</p>
                <div className="flex items-center justify-between">
                  <p className="text-lg font-semibold text-indigo-600">{brandName}</p>
                  <button
                    onClick={() => {
                      setBrandName('')
                      setBrandInput('')
                    }}
                    className="text-xs text-gray-500 hover:text-red-600"
                  >
                    Change
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Main Content */}
        <div className="flex-1 flex flex-col">
          {/* Tab Navigation */}
          <div className="bg-white shadow">
            <div className="px-6">
              <nav className="flex space-x-8">
                {tabs.map((tab) => (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id as any)}
                    className={`py-4 px-1 border-b-2 font-medium text-sm transition-colors ${
                      activeTab === tab.id
                        ? 'border-indigo-500 text-indigo-600'
                        : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                    }`}
                  >
                    <span className="mr-2">{tab.icon}</span>
                    {tab.label}
                  </button>
                ))}
              </nav>
            </div>
          </div>

          {/* Tab Content */}
          <div className="flex-1 overflow-auto bg-gray-50">
            {brandName ? (
              <div className="p-6">
                {activeTab === 'ai-visibility' && (
                  <AIVisibility brandId={brandId} brandName={brandName} />
                )}
                {activeTab === 'openai' && (
                  <ModelComparison brandId={brandId} brandName={brandName} vendor="openai" />
                )}
                {activeTab === 'google' && (
                  <ModelComparison brandId={brandId} brandName={brandName} vendor="google" />
                )}
                {/* Anthropic tab disabled - no embeddings API available for BEEB analysis
                {activeTab === 'anthropic' && (
                  <ModelComparison brandId={brandId} brandName={brandName} vendor="anthropic" />
                )}
                */}
                {activeTab === 'settings' && (
                  <Settings brandId={brandId} brandName={brandName} />
                )}
              </div>
            ) : (
              <div className="flex items-center justify-center h-full">
                <div className="text-center">
                  <p className="text-gray-500 mb-4">Please enter your brand name to get started</p>
                  <p className="text-sm text-gray-400">
                    AI Rank shows what happens when people talk to AI models<br />
                    to find information related to your name, brand, products or services.
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}