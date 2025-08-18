'use client'

import { useState, useEffect } from 'react'
import Countries from './Countries'
import GroundingTestGrid from './GroundingTestGrid'
import { GROUNDING_MODES, getGroundingDisplayLabel, getProviderFromModel, mapLegacyMode } from '../constants/grounding'
import { 
  ExclamationCircleIcon, 
  PlayIcon, 
  PlusIcon, 
  TrashIcon, 
  GlobeAltIcon, 
  CircleStackIcon, 
  ChartBarIcon, 
  MapPinIcon, 
  CheckCircleIcon, 
  XCircleIcon,
  PencilIcon,
  DocumentDuplicateIcon,
  DocumentTextIcon,
  ClipboardDocumentListIcon,
  ChartPieIcon,
  ClockIcon,
  BeakerIcon,
  SparklesIcon,
  CpuChipIcon,
  CodeBracketIcon,
  ChevronDownIcon,
  LinkIcon,
  EyeIcon
} from '@heroicons/react/24/outline'

interface PromptTemplate {
  id: number
  brand_name: string
  template_name: string
  prompt_text: string
  prompt_type: string
  model_name?: string
  provider?: string
  countries: string[]
  grounding_modes: string[]
  is_active: boolean
  created_at: string
  prompt_hash?: string
  prompt_hash_full?: string
  last_run_at?: string | null
  total_runs?: number
  successful_runs?: number
  canonical_json?: string
  temperature?: number
  seed?: number
  top_p?: number
  max_tokens?: number
}

interface PromptRun {
  id: number
  template_id: number
  template_name?: string
  brand_name: string
  model_name: string
  provider?: string
  country_code: string
  grounding_mode: string
  grounding_mode_canonical?: string
  status: string
  started_at: string | null
  completed_at: string | null
  error_message: string | null
  created_at: string
  prompt_hash?: string
  prompt_hash_full?: string
  response_api?: string
  tool_choice?: string
  grounded_effective?: boolean
  tool_call_count?: number
  citations_count?: number
  finish_reason?: string | null
  content_filtered?: boolean
}

interface PromptResult {
  run_id: number
  country: string
  grounding_mode: string
  brand_mentioned: boolean
  mention_count: number
  response_preview: string
  error?: string
}

interface Analytics {
  brand_name: string
  statistics: {
    total_runs: number
    successful_runs: number
    failed_runs: number
    mention_rate: number
    avg_mentions_per_response: number
    avg_confidence: number
  }
  grounding_comparison: {
    [key: string]: {
      run_count: number
      mention_rate: number
    }
  }
  country_comparison: {
    [key: string]: {
      run_count: number
      mention_rate: number
    }
  }
}

interface PromptTrackingProps {
  brandName: string
  brandId: number
}

export default function PromptTrackingFixed({ brandName, brandId }: PromptTrackingProps) {
  const [activeTab, setActiveTab] = useState('templates')
  const [templates, setTemplates] = useState<PromptTemplate[]>([])
  const [runs, setRuns] = useState<PromptRun[]>([])
  const [analytics, setAnalytics] = useState<Analytics | null>(null)
  const [loading, setLoading] = useState(false)
  const [runningTemplates, setRunningTemplates] = useState<Set<number>>(new Set())
  const [editingTemplate, setEditingTemplate] = useState<number | null>(null)
  const [expandedResults, setExpandedResults] = useState<{ [key: number]: any }>({})
  const [loadingResults, setLoadingResults] = useState<{ [key: number]: boolean }>({})
  const [showTemplateForm, setShowTemplateForm] = useState(true) // Always show by default
  const [expandedTemplates, setExpandedTemplates] = useState<{ [key: number]: boolean }>({})
  const [showCanonicalJson, setShowCanonicalJson] = useState<{ [key: number]: boolean }>({})
  const [showSuccessMessage, setShowSuccessMessage] = useState<string | null>(null)
  const [deletingTemplate, setDeletingTemplate] = useState<number | null>(null)
  
  // Form state for new/edit template
  const [newTemplate, setNewTemplate] = useState({
    template_name: '',
    prompt_text: '',
    prompt_type: 'custom',
    model_name: 'gemini-2.5-pro',
    countries: ['NONE'],
    grounding_modes: [GROUNDING_MODES.NOT_GROUNDED]
  })

  // Available options
  const countries = [
    { value: 'NONE', label: '🌐 Base Model (No Location)' },
    { value: 'US', label: '🇺🇸 United States' },
    { value: 'GB', label: '🇬🇧 United Kingdom' },
    { value: 'DE', label: '🇩🇪 Germany' },
    { value: 'CH', label: '🇨🇭 Switzerland' },
    { value: 'AE', label: '🇦🇪 UAE' },
    { value: 'SG', label: '🇸🇬 Singapore' },
    { value: 'IT', label: '🇮🇹 Italy' },
    { value: 'FR', label: '🇫🇷 France' }
  ]

  const promptTypes = [
    { value: 'recognition', label: 'Brand Recognition' },
    { value: 'competitive', label: 'Competitor Analysis' },
    { value: 'product', label: 'Product Knowledge' },
    { value: 'industry', label: 'Industry Position' },
    { value: 'custom', label: 'Custom' }
  ]
  
  const models = [
    { value: 'gpt-5', label: 'GPT-5' },
    { value: 'gpt-5-mini', label: 'GPT-5 Mini' },
    { value: 'gpt-4o', label: 'GPT-4o' },
    { value: 'gemini-2.5-pro', label: 'Gemini 2.5 Pro' },
    { value: 'gemini-2.0-flash', label: 'Gemini 2.0 Flash' }
  ]

  // Generate immutable prompts based on selections
  const generatePrompts = () => {
    const basePrompts = {
      recognition: [
        `What is {brand_name}?`,
        `Tell me about {brand_name} company`,
        `Have you heard of {brand_name}?`
      ],
      competitive: [
        `What are the main competitors of {brand_name}?`,
        `How does {brand_name} compare to its competitors?`,
        `What makes {brand_name} different from other companies in its industry?`
      ],
      product: [
        `What products does {brand_name} offer?`,
        `What is {brand_name}'s main product or service?`,
        `List the top products from {brand_name}`
      ],
      industry: [
        `What industry is {brand_name} in?`,
        `What is {brand_name}'s position in the market?`,
        `How influential is {brand_name} in its sector?`
      ]
    }

    const selectedPrompts = basePrompts[newTemplate.prompt_type as keyof typeof basePrompts] || []
    
    // Create templates for each combination
    const combinations: any[] = []
    selectedPrompts.forEach((prompt, idx) => {
      newTemplate.countries.forEach(country => {
        newTemplate.grounding_modes.forEach(mode => {
          combinations.push({
            template_name: `${newTemplate.prompt_type}_${country}_${mode}_${idx + 1}`,
            prompt_text: prompt,
            prompt_type: newTemplate.prompt_type,
            model_name: newTemplate.model_name,
            countries: [country],
            grounding_modes: [mode],
            brand_name: brandName
          })
        })
      })
    })

    return combinations
  }

  // Fetch templates
  const fetchTemplates = async () => {
    try {
      const response = await fetch(`http://localhost:8000/api/prompt-tracking/templates?brand_name=${brandName}`)
      const data = await response.json()
      setTemplates(data.templates || [])
    } catch (error) {
      console.error('Failed to fetch templates:', error)
    }
  }

  // Fetch runs
  const fetchRuns = async () => {
    try {
      const response = await fetch(`http://localhost:8000/api/prompt-tracking/runs?brand_name=${brandName}&limit=20`)
      const data = await response.json()
      const runsWithNames = (data.runs || []).map((run: PromptRun) => {
        const template = templates.find(t => t.id === run.template_id)
        return {
          ...run,
          template_name: template?.template_name || `Template #${run.template_id}`
        }
      })
      setRuns(runsWithNames)
    } catch (error) {
      console.error('Failed to fetch runs:', error)
    }
  }

  // Fetch analytics
  const fetchAnalytics = async () => {
    try {
      const response = await fetch(`http://localhost:8000/api/prompt-tracking/analytics/${brandName}`)
      const data = await response.json()
      setAnalytics(data)
    } catch (error) {
      console.error('Failed to fetch analytics:', error)
    }
  }

  useEffect(() => {
    if (brandName) {
      fetchTemplates()
      fetchAnalytics()
    }
  }, [brandName])
  
  useEffect(() => {
    if (brandName && templates.length >= 0) {
      fetchRuns()
    }
  }, [brandName, templates])

  // Create or update template
  const saveTemplate = async () => {
    if (!newTemplate.template_name || !newTemplate.prompt_text) {
      alert('Please fill in template name and prompt text')
      return
    }

    try {
      const url = editingTemplate 
        ? `http://localhost:8000/api/prompt-tracking/templates/${editingTemplate}`
        : 'http://localhost:8000/api/prompt-tracking/templates'
      
      const response = await fetch(url, {
        method: editingTemplate ? 'PUT' : 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          brand_name: brandName,
          ...newTemplate
        })
      })
      
      if (response.ok) {
        await fetchTemplates()
        setNewTemplate({
          template_name: '',
          prompt_text: '',
          prompt_type: 'custom',
          model_name: 'gemini-2.5-pro',
          countries: ['NONE'],
          grounding_modes: [GROUNDING_MODES.NOT_GROUNDED]
        })
        setEditingTemplate(null)
        
        // Show success message
        setShowSuccessMessage(editingTemplate ? 'Template updated successfully!' : 'Template created successfully!')
        setTimeout(() => setShowSuccessMessage(null), 3000)
      }
    } catch (error) {
      console.error('Failed to save template:', error)
    }
  }

  // Batch create templates
  const createBatchTemplates = async () => {
    const templates = generatePrompts()
    
    for (const template of templates) {
      try {
        await fetch('http://localhost:8000/api/prompt-tracking/templates', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(template)
        })
      } catch (error) {
        console.error('Failed to create template:', error)
      }
    }
    
    await fetchTemplates()
    setShowSuccessMessage(`Created ${templates.length} templates successfully!`)
    setTimeout(() => setShowSuccessMessage(null), 3000)
  }

  // Copy template settings to form
  const copyTemplate = (template: PromptTemplate) => {
    setNewTemplate({
      template_name: `${template.template_name} (Copy)`,
      prompt_text: template.prompt_text,
      prompt_type: template.prompt_type,
      model_name: template.model_name || 'gemini-2.5-pro',
      countries: template.countries,
      grounding_modes: template.grounding_modes
    })
    // Scroll to top where the form is
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  // Delete template
  const deleteTemplate = async (templateId: number) => {
    if (!confirm('Are you sure you want to delete this template?')) {
      return
    }

    setDeletingTemplate(templateId)
    try {
      const response = await fetch(`http://localhost:8000/api/prompt-tracking/templates/${templateId}`, {
        method: 'DELETE'
      })
      
      if (response.ok) {
        await fetchTemplates()
        setShowSuccessMessage('Template deleted successfully!')
        setTimeout(() => setShowSuccessMessage(null), 3000)
      }
    } catch (error) {
      console.error('Failed to delete template:', error)
    } finally {
      setDeletingTemplate(null)
    }
  }

  // Run prompt test
  const runPrompt = async (templateId: number) => {
    setRunningTemplates(prev => new Set(prev).add(templateId))
    
    const template = templates.find(t => t.id === templateId)
    const modelToUse = template?.model_name || 'gemini-2.5-pro'
    
    try {
      const controller = new AbortController()
      const timeoutId = setTimeout(() => controller.abort(), 120000)
      
      const response = await fetch('http://localhost:8000/api/prompt-tracking/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          template_id: templateId,
          model_name: modelToUse,
          brand_name: brandName
        }),
        signal: controller.signal
      })
      
      clearTimeout(timeoutId)
      
      if (response.ok) {
        await fetchRuns()
        await fetchAnalytics()
        setShowSuccessMessage('Test completed successfully!')
        setTimeout(() => setShowSuccessMessage(null), 3000)
      }
    } catch (error: any) {
      console.error('Failed to run prompt:', error)
      if (error.name === 'AbortError') {
        alert('Request timed out after 2 minutes.')
      }
    } finally {
      setRunningTemplates(prev => {
        const newSet = new Set(prev)
        newSet.delete(templateId)
        return newSet
      })
    }
  }

  // Fetch detailed result
  const fetchResult = async (runId: number) => {
    if (expandedResults[runId]) {
      setExpandedResults(prev => {
        const newExpanded = { ...prev }
        delete newExpanded[runId]
        return newExpanded
      })
      return
    }
    
    setLoadingResults(prev => ({ ...prev, [runId]: true }))
    
    try {
      const response = await fetch(`http://localhost:8000/api/prompt-tracking/results/${runId}`)
      if (response.ok) {
        const data = await response.json()
        // The API returns {run: {...}, result: {...}} structure
        // We need to merge them for easier access
        const mergedData = {
          ...data.run,
          ...data.result,
          // Keep original structure too
          _run: data.run,
          _result: data.result
        }
        setExpandedResults(prev => ({ ...prev, [runId]: mergedData }))
      } else {
        console.error('Failed to fetch result, status:', response.status)
        setExpandedResults(prev => ({ ...prev, [runId]: { error: 'Failed to load result' } }))
      }
    } catch (error) {
      console.error('Failed to fetch result:', error)
      setExpandedResults(prev => ({ ...prev, [runId]: { error: 'Network error' } }))
    } finally {
      setLoadingResults(prev => ({ ...prev, [runId]: false }))
    }
  }

  return (
    <div className="space-y-6">
      {/* Success Message */}
      {showSuccessMessage && (
        <div className="fixed top-4 right-4 z-50 animate-in slide-in-from-top-2 fade-in duration-300">
          <div className="bg-green-50 border border-green-200 text-green-800 px-4 py-3 rounded-lg shadow-lg flex items-center gap-2">
            <CheckCircleIcon className="w-5 h-5 text-green-600" />
            <span className="font-medium">{showSuccessMessage}</span>
          </div>
        </div>
      )}
      
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-3xl font-bold tracking-tight bg-gradient-to-r from-gray-900 to-gray-600 bg-clip-text text-transparent">Prompt Tracking</h2>
          <p className="text-gray-500 mt-1">
            Test how AI models respond to prompts about {brandName} across different countries and grounding modes
          </p>
        </div>
      </div>

      {/* Tab navigation */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex space-x-8">
          {['templates', 'results', 'analytics', 'grounding-test', 'countries'].map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`py-2 px-1 border-b-2 font-medium text-sm capitalize ${
                activeTab === tab
                  ? 'border-indigo-500 text-indigo-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              {tab === 'grounding-test' ? 'Grounding Test' : tab}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab content */}
      <div className="mt-4">
        {/* Templates Tab */}
        {activeTab === 'templates' && (
          <div className="space-y-6">
            {/* Prompt Builder Section */}
            <div className="bg-gradient-to-r from-indigo-50 to-purple-50 rounded-lg shadow-lg border border-indigo-200">
              <div className="px-6 py-4 border-b border-indigo-200 bg-white/50 backdrop-blur">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <SparklesIcon className="w-6 h-6 text-indigo-600" />
                    <h3 className="text-lg font-semibold text-gray-900">Prompt Configuration Builder</h3>
                  </div>
                  <span className="text-sm text-gray-600">Generate immutable test prompts</span>
                </div>
              </div>
              
              <div className="p-6 space-y-6">
                {/* Model, Type, Countries Selection */}
                <div className="grid grid-cols-3 gap-6">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      <CpuChipIcon className="w-4 h-4 inline mr-1" />
                      AI Model
                    </label>
                    <select
                      value={newTemplate.model_name}
                      onChange={(e) => setNewTemplate({ ...newTemplate, model_name: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                    >
                      {models.map(model => (
                        <option key={model.value} value={model.value}>
                          {model.label}
                        </option>
                      ))}
                    </select>
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      <DocumentTextIcon className="w-4 h-4 inline mr-1" />
                      Prompt Type
                    </label>
                    <select
                      value={newTemplate.prompt_type}
                      onChange={(e) => setNewTemplate({ ...newTemplate, prompt_type: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                    >
                      {promptTypes.map(type => (
                        <option key={type.value} value={type.value}>
                          {type.label}
                        </option>
                      ))}
                    </select>
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Template Name
                    </label>
                    <input
                      type="text"
                      value={newTemplate.template_name}
                      onChange={(e) => setNewTemplate({ ...newTemplate, template_name: e.target.value })}
                      placeholder="Optional - auto-generated if empty"
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                    />
                  </div>
                </div>

                {/* Countries Selection */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-3">
                    <MapPinIcon className="w-4 h-4 inline mr-1" />
                    Select Countries
                  </label>
                  <div className="flex flex-wrap gap-2">
                    {countries.map(country => (
                      <button
                        key={country.value}
                        onClick={() => {
                          const updated = newTemplate.countries.includes(country.value)
                            ? newTemplate.countries.filter(c => c !== country.value)
                            : [...newTemplate.countries, country.value]
                          setNewTemplate({ ...newTemplate, countries: updated })
                        }}
                        className={`px-4 py-2 rounded-full text-sm font-medium transition-all ${
                          newTemplate.countries.includes(country.value)
                            ? 'bg-indigo-600 text-white shadow-md scale-105'
                            : 'bg-white text-gray-700 border border-gray-300 hover:border-indigo-300'
                        }`}
                      >
                        {country.label}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Grounding Modes */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-3">
                    <GlobeAltIcon className="w-4 h-4 inline mr-1" />
                    Grounding Modes
                  </label>
                  <div className="flex gap-3">
                    <button
                      onClick={() => {
                        const updated = newTemplate.grounding_modes.includes(GROUNDING_MODES.NOT_GROUNDED)
                          ? newTemplate.grounding_modes.filter(m => m !== GROUNDING_MODES.NOT_GROUNDED)
                          : [...newTemplate.grounding_modes, GROUNDING_MODES.NOT_GROUNDED]
                        setNewTemplate({ ...newTemplate, grounding_modes: updated })
                      }}
                      className={`flex items-center px-4 py-2 rounded-full text-sm font-medium transition-all ${
                        newTemplate.grounding_modes.includes(GROUNDING_MODES.NOT_GROUNDED)
                          ? 'bg-blue-600 text-white shadow-md'
                          : 'bg-white text-gray-700 border border-gray-300 hover:border-blue-300'
                      }`}
                    >
                      <CircleStackIcon className="w-4 h-4 mr-2" />
                      {newTemplate.model_name?.startsWith('gpt') ? 'OFF' : 'Model Knowledge Only'}
                    </button>
                    {newTemplate.model_name?.startsWith('gpt') && (
                      <button
                        onClick={() => {
                          const updated = newTemplate.grounding_modes.includes('preferred')
                            ? newTemplate.grounding_modes.filter(m => m !== 'preferred')
                            : [...newTemplate.grounding_modes, 'preferred']
                          setNewTemplate({ ...newTemplate, grounding_modes: updated })
                        }}
                        className={`flex items-center px-4 py-2 rounded-full text-sm font-medium transition-all ${
                          newTemplate.grounding_modes.includes('preferred')
                            ? 'bg-yellow-600 text-white shadow-md'
                            : 'bg-white text-gray-700 border border-gray-300 hover:border-yellow-300'
                        }`}
                      >
                        <GlobeAltIcon className="w-4 h-4 mr-2" />
                        PREFERRED
                      </button>
                    )}
                    <button
                      onClick={() => {
                        const grounded = newTemplate.model_name?.startsWith('gpt') ? 'required' : GROUNDING_MODES.GROUNDED
                        const updated = newTemplate.grounding_modes.includes(grounded)
                          ? newTemplate.grounding_modes.filter(m => m !== grounded)
                          : [...newTemplate.grounding_modes, grounded]
                        setNewTemplate({ ...newTemplate, grounding_modes: updated })
                      }}
                      className={`flex items-center px-4 py-2 rounded-full text-sm font-medium transition-all ${
                        (newTemplate.grounding_modes.includes(GROUNDING_MODES.GROUNDED) || newTemplate.grounding_modes.includes('required'))
                          ? 'bg-green-600 text-white shadow-md'
                          : 'bg-white text-gray-700 border border-gray-300 hover:border-green-300'
                      }`}
                    >
                      <GlobeAltIcon className="w-4 h-4 mr-2" />
                      {newTemplate.model_name?.startsWith('gpt') ? 'REQUIRED' : 'Grounded (Web Search)'}
                    </button>
                  </div>
                </div>

                {/* Custom Prompt Text */}
                {newTemplate.prompt_type === 'custom' && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Custom Prompt Text
                    </label>
                    <textarea
                      value={newTemplate.prompt_text}
                      onChange={(e) => setNewTemplate({ ...newTemplate, prompt_text: e.target.value })}
                      placeholder="Enter your custom prompt. Use {brand_name} as placeholder."
                      rows={3}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                    />
                  </div>
                )}

                {/* Action Buttons */}
                <div className="flex gap-3">
                  {newTemplate.prompt_type !== 'custom' ? (
                    <button
                      onClick={createBatchTemplates}
                      className="flex-1 flex items-center justify-center px-6 py-3 bg-gradient-to-r from-indigo-600 to-purple-600 text-white rounded-lg hover:from-indigo-700 hover:to-purple-700 shadow-lg transition-all"
                    >
                      <SparklesIcon className="w-5 h-5 mr-2" />
                      Generate {generatePrompts().length} Templates
                    </button>
                  ) : (
                    <button
                      onClick={saveTemplate}
                      className="flex-1 flex items-center justify-center px-6 py-3 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 shadow-lg transition-all"
                    >
                      <PlusIcon className="w-5 h-5 mr-2" />
                      Create Custom Template
                    </button>
                  )}
                </div>

                {/* Preview */}
                {newTemplate.prompt_type !== 'custom' && (
                  <div className="bg-white rounded-lg p-4 border border-gray-200">
                    <h4 className="text-sm font-medium text-gray-700 mb-2">Preview Prompts to Generate:</h4>
                    <div className="space-y-1 text-sm text-gray-600 max-h-32 overflow-y-auto">
                      {generatePrompts().slice(0, 5).map((p, i) => (
                        <div key={i} className="flex items-center gap-2">
                          <span className="text-xs bg-gray-100 px-2 py-1 rounded">{p.countries[0]}</span>
                          <span className="text-xs bg-gray-100 px-2 py-1 rounded">{p.grounding_modes[0]}</span>
                          <span className="truncate">{p.prompt_text}</span>
                        </div>
                      ))}
                      {generatePrompts().length > 5 && (
                        <div className="text-gray-400 italic">...and {generatePrompts().length - 5} more</div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Existing Templates */}
            <div className="space-y-4">
              <h3 className="text-lg font-medium text-gray-900">Existing Templates</h3>
              {/* Template List with Enhanced Display */}
              <div className="grid gap-4">
                {templates.filter(t => t.brand_name === brandName).length === 0 ? (
                  <div className="bg-gray-50 rounded-lg border-2 border-dashed border-gray-300 p-12 text-center">
                    <DocumentTextIcon className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                    <h3 className="text-lg font-medium text-gray-900 mb-2">No templates yet</h3>
                    <p className="text-gray-500 mb-4">Create your first template using the configuration builder above</p>
                  </div>
                ) : (
                  templates.filter(t => t.brand_name === brandName).map(template => (
                  <div key={template.id} className="bg-white rounded-lg shadow hover:shadow-lg transition-all duration-200 hover:-translate-y-1">
                    <div className="px-6 py-4">
                      <div className="flex justify-between items-start">
                        <div className="flex-1">
                          <div className="flex items-center gap-3">
                            <h4 className="text-lg font-medium text-gray-900">{template.template_name}</h4>
                            <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                              template.provider === 'openai' ? 'bg-green-100 text-green-800' : 
                              template.provider === 'vertex' ? 'bg-blue-100 text-blue-800' :
                              'bg-gray-100 text-gray-800'
                            }`}>
                              {template.provider || 'Unknown'}
                            </span>
                          </div>
                          <p className="text-gray-600 mt-1">{template.prompt_text?.substring(0, 80)}{template.prompt_text?.length > 80 ? '...' : ''}</p>
                          {/* Main metadata row */}
                          <div className="flex gap-4 mt-3 text-sm">
                            <div className="flex items-center gap-2">
                              <CpuChipIcon className="w-4 h-4 text-gray-400" />
                              <span className="font-medium">
                                {models.find(m => m.value === template.model_name)?.label || template.model_name}
                              </span>
                            </div>
                            <div className="flex items-center gap-2">
                              <MapPinIcon className="w-4 h-4 text-gray-400" />
                              <span>{template.countries.join(', ')}</span>
                            </div>
                            <div className="flex items-center gap-2">
                              {template.grounding_modes.map(mode => (
                                <span key={mode} className="px-2 py-1 bg-gray-100 rounded text-xs">
                                  {mode === GROUNDING_MODES.NOT_GROUNDED ? 'Model Knowledge' : 'Grounded'}
                                </span>
                              ))}
                            </div>
                            {template.last_run_at && (
                              <div className="flex items-center gap-1 text-gray-500">
                                <ClockIcon className="w-4 h-4" />
                                <span>Last run: {new Date(template.last_run_at).toLocaleDateString()}</span>
                              </div>
                            )}
                            {template.total_runs > 0 && (
                              <div className="flex items-center gap-1 text-gray-500">
                                <ChartBarIcon className="w-4 h-4" />
                                <span>{template.total_runs} runs</span>
                              </div>
                            )}
                          </div>
                        
                          {/* System Parameters Section (expandable) */}
                          {expandedTemplates[template.id] && (
                            <div className="mt-4 pt-4 border-t space-y-4">
                              {/* Section 1: System Parameters */}
                              <div>
                                <h5 className="text-sm font-semibold text-gray-900 mb-2">System Parameters</h5>
                                <div className="grid grid-cols-4 gap-3 text-sm">
                                  <div className="bg-gray-50 p-2 rounded">
                                    <span className="text-gray-500">Temperature:</span>
                                    <span className="ml-2 font-mono">{template.temperature || 0.7}</span>
                                  </div>
                                  <div className="bg-gray-50 p-2 rounded">
                                    <span className="text-gray-500">Seed:</span>
                                    <span className="ml-2 font-mono">{template.seed || 'None'}</span>
                                  </div>
                                  <div className="bg-gray-50 p-2 rounded">
                                    <span className="text-gray-500">Top-p:</span>
                                    <span className="ml-2 font-mono">{template.top_p || 1.0}</span>
                                  </div>
                                  <div className="bg-gray-50 p-2 rounded">
                                    <span className="text-gray-500">Max tokens:</span>
                                    <span className="ml-2 font-mono">{template.max_tokens || 'Default'}</span>
                                  </div>
                                </div>
                              </div>

                              {/* Section 2: SHA-256 Hash */}
                              {template.prompt_hash_full && (
                                <div>
                                  <h5 className="text-sm font-semibold text-gray-900 mb-2">Configuration Hash</h5>
                                  <div className="bg-gray-50 p-3 rounded font-mono text-xs break-all">
                                    SHA-256: {template.prompt_hash_full}
                                  </div>
                                </div>
                              )}

                              {/* Section 3: Metadata */}
                              <div>
                                <h5 className="text-sm font-semibold text-gray-900 mb-2">Metadata</h5>
                                <div className="text-sm text-gray-600 space-y-1">
                                  <div>Created: {new Date(template.created_at).toLocaleString()}</div>
                                  {template.last_run_at && (
                                    <div>Last run: {new Date(template.last_run_at).toLocaleString()}</div>
                                  )}
                                  <div>Total runs: {template.total_runs || 0} ({template.successful_runs || 0} successful)</div>
                                </div>
                              </div>
                            </div>
                          )}
                        </div>
                        
                        {/* Expandable Canonical JSON */}
                        {template.canonical_json && (
                          <div className="mt-2">
                            <button
                              onClick={() => setShowCanonicalJson(prev => ({ ...prev, [template.id]: !prev[template.id] }))}
                              className="text-xs text-blue-600 hover:text-blue-800 flex items-center gap-1"
                            >
                              <CodeBracketIcon className="w-3 h-3" />
                              {showCanonicalJson[template.id] ? 'Hide' : 'Show'} Canonical JSON
                            </button>
                            {showCanonicalJson[template.id] && (
                              <div className="mt-2 p-3 bg-gray-50 rounded-lg overflow-x-auto">
                                <pre className="text-xs font-mono text-gray-700">{template.canonical_json}</pre>
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                      <div className="flex items-center gap-2 ml-4">
                        <button
                          onClick={() => setExpandedTemplates(prev => ({ ...prev, [template.id]: !prev[template.id] }))}
                          className="p-2 text-gray-600 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg transition-all"
                          title={expandedTemplates[template.id] ? "Collapse details" : "Expand details"}
                        >
                          <ChevronDownIcon className={`w-4 h-4 transition-transform ${expandedTemplates[template.id] ? 'rotate-180' : ''}`} />
                        </button>
                        <button
                          onClick={() => copyTemplate(template)}
                          className="p-2 text-gray-600 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-all hover:scale-110"
                          title="Copy template settings to form"
                        >
                          <DocumentDuplicateIcon className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => deleteTemplate(template.id)}
                          disabled={deletingTemplate === template.id}
                          className="p-2 text-gray-600 hover:text-red-600 hover:bg-red-50 rounded-lg transition-all hover:scale-110 disabled:opacity-50"
                          title="Delete this template"
                        >
                          {deletingTemplate === template.id ? (
                            <div className="w-4 h-4 border-2 border-red-600 border-t-transparent rounded-full animate-spin" />
                          ) : (
                            <TrashIcon className="w-4 h-4" />
                          )}
                        </button>
                        <button
                          onClick={() => runPrompt(template.id)}
                          disabled={runningTemplates.has(template.id)}
                          className="flex items-center px-4 py-2 bg-gradient-to-r from-green-600 to-green-500 text-white rounded-lg hover:from-green-700 hover:to-green-600 disabled:from-gray-400 disabled:to-gray-400 shadow-md hover:shadow-lg transition-all"
                        >
                          {runningTemplates.has(template.id) ? (
                            <>
                              <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2" />
                              Running...
                            </>
                          ) : (
                            <>
                              <PlayIcon className="w-4 h-4 mr-2" />
                              Run Test
                            </>
                          )}
                        </button>
                      </div>
                    </div>
                  </div>
                  ))
                )}
              </div>
            </div>
          </div>
        )}

        {/* Results Tab */}
        {activeTab === 'results' && (
          <div className="bg-white rounded-lg shadow">
            <div className="px-6 py-4 border-b flex justify-between items-start">
              <div>
                <h3 className="text-lg font-medium">Recent Test Runs</h3>
                <p className="text-sm text-gray-500 mt-1">
                  View the history of prompt tests for {brandName}
                </p>
              </div>
              <button
                onClick={() => {
                  fetchRuns()
                  fetchAnalytics()
                }}
                className="px-3 py-1 bg-blue-600 text-white rounded-md hover:bg-blue-700 text-sm"
              >
                Refresh Results
              </button>
            </div>
            <div className="p-6">
              <div className="space-y-4">
                {runs.map(run => (
                  <div key={run.id} className="border rounded-lg">
                    <div className="flex items-center justify-between p-4">
                      <div className="flex items-center gap-4">
                        {run.status === 'completed' ? (
                          <CheckCircleIcon className="w-5 h-5 text-green-500" />
                        ) : run.status === 'failed' ? (
                          <XCircleIcon className="w-5 h-5 text-red-500" />
                        ) : (
                          <ExclamationCircleIcon className="w-5 h-5 text-yellow-500" />
                        )}
                        <div>
                          <p className="font-medium">{run.template_name}</p>
                          <div className="flex items-center gap-2 text-sm text-gray-500">
                            <span>{run.country_code === 'NONE' ? 'Base Model' : run.country_code}</span>
                            <span>•</span>
                            <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                              run.grounding_mode === 'web' ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                            }`}>
                              {run.grounding_mode === 'none' ? '📚 Model Knowledge' : '🌐 Grounded'}
                            </span>
                            <span>•</span>
                            <span className={`font-medium ${
                              run.provider === 'openai' ? 'text-green-600' : 
                              run.provider === 'vertex' ? 'text-blue-600' : 
                              'text-gray-600'
                            }`}>
                              {run.model_name}
                            </span>
                          </div>
                          {/* Metadata row */}
                          <div className="flex items-center gap-3 mt-1 text-xs text-gray-400">
                            {run.tool_call_count !== undefined && run.tool_call_count > 0 && (
                              <span className="flex items-center gap-1">
                                <BeakerIcon className="w-3 h-3" />
                                {run.tool_call_count} tool calls
                              </span>
                            )}
                            {run.citations_count !== undefined && run.citations_count > 0 && (
                              <span className="flex items-center gap-1">
                                <DocumentTextIcon className="w-3 h-3" />
                                {run.citations_count} citations
                              </span>
                            )}
                            {run.finish_reason && (
                              <span className={`${
                                run.finish_reason === 'stop' ? 'text-green-600' :
                                run.finish_reason === 'length' ? 'text-yellow-600' :
                                'text-red-600'
                              }`}>
                                {run.finish_reason === 'length' ? '⚠️ Token limit' : 
                                 run.finish_reason === 'stop' ? '✓ Complete' : 
                                 `⚠️ ${run.finish_reason}`}
                              </span>
                            )}
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => {
                            // Navigate to template
                            const templateId = run.template_id
                            if (templateId) {
                              setActiveTab('templates')
                              setTimeout(() => {
                                setExpandedTemplates(prev => ({ ...prev, [templateId]: true }))
                                // Scroll to template
                                const element = document.getElementById(`template-${templateId}`)
                                if (element) {
                                  element.scrollIntoView({ behavior: 'smooth', block: 'center' })
                                }
                              }, 100)
                            }
                          }}
                          className="px-2 py-1 text-indigo-600 hover:bg-indigo-50 rounded text-sm flex items-center gap-1"
                          title="View template"
                        >
                          <LinkIcon className="w-3 h-3" />
                          Template
                        </button>
                        <button
                          onClick={() => fetchResult(run.id)}
                          disabled={loadingResults[run.id]}
                          className="px-3 py-1 bg-blue-600 text-white rounded-md hover:bg-blue-700 text-sm"
                        >
                          {loadingResults[run.id] ? 'Loading...' : expandedResults[run.id] ? 'Hide Details' : 'View Details'}
                        </button>
                        <span className={`px-2 py-1 rounded text-xs ${
                          run.status === 'completed' ? 'bg-green-100 text-green-700' :
                          run.status === 'failed' ? 'bg-red-100 text-red-700' :
                          'bg-gray-100 text-gray-700'
                        }`}>
                          {run.status}
                        </span>
                      </div>
                    </div>
                    {expandedResults[run.id] && (
                      <div className="px-4 pb-4 border-t">
                        {expandedResults[run.id].error ? (
                          <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
                            <p className="text-red-800">Error loading result: {expandedResults[run.id].error}</p>
                          </div>
                        ) : (
                          <div className="mt-4">
                            <div className="mb-3">
                              <span className="font-semibold text-sm">Prompt:</span>
                              <p className="text-sm mt-1 text-gray-700 bg-gray-50 p-2 rounded">{expandedResults[run.id].prompt_text || 'No prompt text'}</p>
                            </div>
                            <div className="mb-3">
                              <span className="font-semibold text-sm">Response:</span>
                              <pre className="text-sm mt-1 whitespace-pre-wrap font-sans text-gray-700 max-h-96 overflow-y-auto bg-gray-50 p-3 rounded border border-gray-200">
                                {expandedResults[run.id].model_response || 'No response available'}
                              </pre>
                            </div>
                            {/* Metadata Section */}
                            <div className="mt-4 pt-4 border-t space-y-3">
                              {/* Basic Metrics */}
                              <div className="flex items-center gap-4 text-sm">
                                <span className={`font-medium ${
                                  expandedResults[run.id].brand_mentioned ? 'text-green-600' : 'text-gray-500'
                                }`}>
                                  Brand mentioned: {expandedResults[run.id].brand_mentioned ? '✓ Yes' : '✗ No'}
                                </span>
                                <span>Mentions: {expandedResults[run.id].mention_count || 0}</span>
                                <span>Confidence: {expandedResults[run.id].confidence_score ? (expandedResults[run.id].confidence_score * 100).toFixed(0) : 0}%</span>
                              </div>
                            
                            {/* Grounding Metadata */}
                            {expandedResults[run.id].grounding_metadata && (
                              <div className="bg-blue-50 rounded-lg p-3">
                                <h4 className="text-xs font-semibold text-blue-900 mb-2">Grounding Metadata</h4>
                                <pre className="text-xs text-blue-800 whitespace-pre-wrap">
                                  {JSON.stringify(expandedResults[run.id].grounding_metadata, null, 2)}
                                </pre>
                              </div>
                            )}
                            
                            {/* Citations */}
                            {expandedResults[run.id].citations && expandedResults[run.id].citations.length > 0 && (
                              <div className="bg-green-50 rounded-lg p-3">
                                <h4 className="text-xs font-semibold text-green-900 mb-2">Citations</h4>
                                <div className="space-y-1">
                                  {expandedResults[run.id].citations.map((citation: any, idx: number) => (
                                    <a 
                                      key={idx}
                                      href={citation.uri || citation.url || '#'}
                                      target="_blank"
                                      rel="noopener noreferrer"
                                      className="block text-xs text-green-700 hover:text-green-900 hover:underline"
                                    >
                                      🔗 {citation.title || citation.uri || citation.url}
                                    </a>
                                  ))}
                                </div>
                              </div>
                            )}
                            
                            {/* System Fingerprint & Model Version */}
                            <div className="flex gap-4 text-xs text-gray-500">
                              {expandedResults[run.id].system_fingerprint && (
                                <div>
                                  <span className="font-medium">Fingerprint:</span> {expandedResults[run.id].system_fingerprint}
                                </div>
                              )}
                              {expandedResults[run.id].model_version && (
                                <div>
                                  <span className="font-medium">Model Version:</span> {expandedResults[run.id].model_version}
                                </div>
                              )}
                            </div>
                            
                              {/* Prompt Hash */}
                              {expandedResults[run.id].prompt_hash_full && (
                                <div className="text-xs text-gray-400 font-mono">
                                  SHA-256: {expandedResults[run.id].prompt_hash_full}
                                </div>
                              )}
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Analytics Tab */}
        {activeTab === 'analytics' && analytics && (
          <>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
              <div className="bg-white rounded-lg shadow-md hover:shadow-lg transition-all p-6 border-t-4 border-indigo-500">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-500 font-medium">Total Runs</p>
                    <p className="text-3xl font-bold text-gray-900 mt-1">{analytics.statistics.total_runs}</p>
                  </div>
                  <div className="bg-indigo-100 rounded-full p-3">
                    <ChartBarIcon className="w-8 h-8 text-indigo-600" />
                  </div>
                </div>
              </div>
              <div className="bg-white rounded-lg shadow-md hover:shadow-lg transition-all p-6 border-t-4 border-green-500">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-500 font-medium">Success Rate</p>
                    <p className="text-3xl font-bold text-gray-900 mt-1">
                      {analytics.statistics.total_runs > 0 
                        ? Math.round((analytics.statistics.successful_runs / analytics.statistics.total_runs) * 100)
                        : 0}%
                    </p>
                  </div>
                  <div className="bg-green-100 rounded-full p-3">
                    <CheckCircleIcon className="w-8 h-8 text-green-600" />
                  </div>
                </div>
              </div>
              <div className="bg-white rounded-lg shadow-md hover:shadow-lg transition-all p-6 border-t-4 border-purple-500">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-500 font-medium">Mention Rate</p>
                    <p className="text-3xl font-bold text-gray-900 mt-1">{Math.round(analytics.statistics.mention_rate)}%</p>
                  </div>
                  <div className="bg-purple-100 rounded-full p-3">
                    <ChartPieIcon className="w-8 h-8 text-purple-600" />
                  </div>
                </div>
              </div>
            </div>
          </>
        )}

        {/* Grounding Test Tab */}
        {activeTab === 'grounding-test' && (
          <GroundingTestGrid brandName={brandName} />
        )}

        {/* Countries Tab */}
        {activeTab === 'countries' && (
          <Countries />
        )}
      </div>
    </div>
  )
}