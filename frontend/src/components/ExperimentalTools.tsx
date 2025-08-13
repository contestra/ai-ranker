'use client'

import { useState } from 'react'
import AIVisibility from '@/components/AIVisibility'
import ModelComparison from '@/components/ModelComparison'
import ComparisonView from '@/components/ComparisonView'
import LLMCrawlability from '@/components/LLMCrawlability'
import WeeklyTrends from '@/components/WeeklyTrends'
import ConcordanceAnalysis from '@/components/ConcordanceAnalysis'
import EntityStrengthDashboard from '@/components/EntityStrengthDashboard'
import CrawlerMonitorV2 from '@/components/CrawlerMonitorV2'
import { ChevronLeftIcon } from '@heroicons/react/24/outline'

interface ExperimentalToolsProps {
  brandId: number
  brandName: string
  onBack: () => void
}

export default function ExperimentalTools({ brandId, brandName, onBack }: ExperimentalToolsProps) {
  const [activeTab, setActiveTab] = useState<'ai-visibility' | 'openai' | 'google' | 'comparison' | 'concordance' | 'entity-strength' | 'crawlability' | 'crawler-monitor' | 'trends'>('ai-visibility')

  const tabs = [
    { id: 'ai-visibility', label: 'AI Visibility', icon: '👁️', description: 'Overall AI presence analysis' },
    { id: 'openai', label: 'OpenAI', icon: '🤖', description: 'GPT model analysis' },
    { id: 'google', label: 'Google', icon: '🔍', description: 'Gemini model analysis' },
    { id: 'comparison', label: 'Comparison', icon: '🔬', description: 'Compare across models' },
    { id: 'concordance', label: 'Concordance', icon: '🔄', description: 'Response consistency' },
    { id: 'entity-strength', label: 'Entity Strength', icon: '💪', description: 'Brand recognition strength' },
    { id: 'crawlability', label: 'LLM Crawlability', icon: '🕷️', description: 'Website AI readiness' },
    { id: 'crawler-monitor', label: 'Crawler Monitor', icon: '📡', description: 'Bot traffic analysis' },
    { id: 'trends', label: 'Weekly Trends', icon: '📈', description: 'Trend analysis over time' },
  ]

  return (
    <div className="h-full flex flex-col">
      {/* Header with Back Button */}
      <div className="bg-white border-b px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button
              onClick={onBack}
              className="flex items-center gap-2 text-gray-600 hover:text-gray-900"
            >
              <ChevronLeftIcon className="w-5 h-5" />
              Back to Prompt Tracking
            </button>
            <div className="h-6 w-px bg-gray-300" />
            <div>
              <h2 className="text-xl font-semibold text-gray-900">Experimental Tools</h2>
              <p className="text-sm text-gray-500">Advanced analysis and monitoring features</p>
            </div>
          </div>
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="bg-white shadow">
        <div className="px-6">
          <nav className="flex space-x-6">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`py-3 px-1 border-b-2 font-medium text-sm transition-colors ${
                  activeTab === tab.id
                    ? 'border-indigo-500 text-indigo-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
                title={tab.description}
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
        {/* LLM Crawlability and Crawler Monitor don't need a brand */}
        {(activeTab === 'crawlability' || activeTab === 'crawler-monitor') ? (
          <div className="p-6">
            {activeTab === 'crawlability' && (
              <LLMCrawlability brandId={brandId} brandName={brandName || ''} />
            )}
            {activeTab === 'crawler-monitor' && (
              <CrawlerMonitorV2 brandId={brandId} brandName={brandName || ''} />
            )}
          </div>
        ) : brandName ? (
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
            {activeTab === 'comparison' && (
              <ComparisonView brandId={brandId} brandName={brandName} />
            )}
            {activeTab === 'concordance' && (
              <ConcordanceAnalysis 
                brandName={brandName} 
                vendor="openai"
                trackedPhrases={JSON.parse(localStorage.getItem('trackedPhrases') || '[]')}
              />
            )}
            {activeTab === 'entity-strength' && (
              <EntityStrengthDashboard brandName={brandName} />
            )}
            {activeTab === 'trends' && (
              <WeeklyTrends brandId={brandId} brandName={brandName} vendor="openai" />
            )}
          </div>
        ) : (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <p className="text-gray-500 mb-4">Please enter your brand name to use experimental tools</p>
              <p className="text-sm text-gray-400">
                Note: LLM Crawlability checker and Crawler Monitor are available without entering a brand
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}