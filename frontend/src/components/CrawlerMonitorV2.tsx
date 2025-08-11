'use client'

import { useState, useEffect, useRef } from 'react'
import { CheckCircleIcon, XCircleIcon, ExclamationTriangleIcon, BoltIcon, PlusIcon, GlobeAltIcon, TrashIcon, ChartBarIcon, SignalIcon } from '@heroicons/react/24/outline'
import BotAnalytics from './BotAnalytics'

interface Domain {
  id: number
  url: string
  is_trackable: boolean
  technology: string
  total_bot_hits: number
  bot_hits_24h: number
  last_bot_hit: string | null
  validation_status: string
  validation_message: string
}

interface DomainValidation {
  domain: string
  is_trackable: boolean
  technology: string[]
  tracking_methods: string[]
  messages: string[]
  recommendation: string
  success: boolean
  error?: string
}

interface BotEvent {
  id: number
  is_bot: boolean
  provider?: string
  bot_name?: string
  bot_type?: string
  purpose?: string
  verified?: boolean
  potential_spoof?: boolean
  spoof_reason?: string
  method: string
  path: string
  status: number
  user_agent: string
  client_ip: string
  timestamp: string
  country?: string
  referrer?: string
}

interface Stats {
  total_hits: number
  bot_hits: number
  on_demand_hits: number
  verified_hits: number
  spoofed_hits: number
  bot_percentage: number
  verification_rate: number
  spoof_rate: number
  by_provider: Record<string, number>
  by_type: Record<string, number>
  top_paths: Record<string, number>
  top_bots: Record<string, number>
}

export default function CrawlerMonitorV2({ brandId, brandName }: { brandId: number, brandName: string }) {
  const [domains, setDomains] = useState<Domain[]>([])
  const [selectedDomain, setSelectedDomain] = useState<string>('')
  const [selectedDomainId, setSelectedDomainId] = useState<number | null>(null)
  const [events, setEvents] = useState<BotEvent[]>([])
  const [stats, setStats] = useState<Stats | null>(null)
  const [connected, setConnected] = useState(false)
  const [filter, setFilter] = useState<'all' | 'bots' | 'on_demand' | 'spoofed'>('all')
  const [showAddDomain, setShowAddDomain] = useState(false)
  const [newDomain, setNewDomain] = useState('')
  const [validating, setValidating] = useState(false)
  const [validation, setValidation] = useState<DomainValidation | null>(null)
  const [viewMode, setViewMode] = useState<'live' | 'analytics'>('live')
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout>()

  // Load domains for brand
  useEffect(() => {
    if (brandId && brandId > 0) {
      loadDomains()
    }
  }, [brandId])

  // Connect WebSocket when domain is selected
  useEffect(() => {
    if (selectedDomain && selectedDomain.trim()) {
      connectWebSocket()
      loadDomainStats()
    }

    return () => {
      if (wsRef.current) {
        wsRef.current.close()
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
      }
    }
  }, [selectedDomain])

  const loadDomains = async () => {
    try {
      const response = await fetch(`http://localhost:8000/api/crawler/v2/monitor/brand/${brandId}/domains`)
      if (response.ok) {
        const data = await response.json()
        setDomains(data)
        // Auto-select first domain if available
        if (data.length > 0 && !selectedDomain) {
          setSelectedDomain(data[0].url)
          setSelectedDomainId(data[0].id)
        }
      }
    } catch (error) {
      console.error('Failed to load domains:', error)
    }
  }

  const loadDomainStats = async () => {
    if (!selectedDomain) return
    
    try {
      const response = await fetch(`http://localhost:8000/api/crawler/v2/monitor/stats/${selectedDomain}`)
      if (response.ok) {
        const data = await response.json()
        setStats(data)
      }
    } catch (error) {
      console.error('Failed to load stats:', error)
    }
  }

  const connectWebSocket = () => {
    if (!selectedDomain) return
    
    try {
      const ws = new WebSocket(`ws://localhost:8000/api/crawler/v2/ws/monitor/${selectedDomain}`)
      
      ws.onopen = () => {
        console.log('WebSocket connected for domain:', selectedDomain)
        setConnected(true)
      }

      ws.onmessage = (event) => {
        const data = JSON.parse(event.data)
        
        if (data.type === 'initial') {
          setStats(data.stats)
          setEvents(data.recent_events || [])
        } else if (data.type === 'new_event') {
          // New bot event
          setEvents(prev => [data, ...prev].slice(0, 100))
          
          // Update stats locally
          if (data.is_bot) {
            setStats(prev => {
              if (!prev) return null
              return {
                ...prev,
                bot_hits: prev.bot_hits + 1,
                total_hits: prev.total_hits + 1,
                on_demand_hits: data.bot_type === 'on_demand' ? prev.on_demand_hits + 1 : prev.on_demand_hits,
                verified_hits: data.verified ? prev.verified_hits + 1 : prev.verified_hits,
                spoofed_hits: data.potential_spoof ? prev.spoofed_hits + 1 : prev.spoofed_hits
              }
            })
          }
        }
      }

      ws.onerror = (error) => {
        console.error('WebSocket error:', error)
      }

      ws.onclose = () => {
        console.log('WebSocket disconnected')
        setConnected(false)
        
        // Reconnect after 3 seconds
        reconnectTimeoutRef.current = setTimeout(() => {
          connectWebSocket()
        }, 3000)
      }

      wsRef.current = ws
    } catch (error) {
      console.error('Failed to connect WebSocket:', error)
      setConnected(false)
    }
  }

  const validateDomain = async () => {
    if (!newDomain.trim()) return
    
    setValidating(true)
    setValidation(null)
    
    try {
      console.log('Validating domain:', newDomain.trim())
      const response = await fetch(`http://localhost:8000/api/domains/validate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: newDomain.trim() })
      })
      
      console.log('Response status:', response.status)
      if (response.ok) {
        const data = await response.json()
        console.log('Validation result:', data)
        setValidation(data)
      } else {
        const errorText = await response.text()
        console.error('Validation failed:', response.status, errorText)
        setValidation({
          domain: newDomain,
          is_trackable: false,
          technology: [],
          tracking_methods: [],
          messages: [`Server error: ${response.status}`],
          recommendation: 'Please try again later',
          success: false,
          error: errorText
        })
      }
    } catch (error) {
      console.error('Failed to validate domain:', error)
      setValidation({
        domain: newDomain,
        is_trackable: false,
        technology: [],
        tracking_methods: [],
        messages: ['Failed to validate domain'],
        recommendation: 'Please check the domain and try again',
        success: false,
        error: 'Validation failed'
      })
    } finally {
      setValidating(false)
    }
  }

  const addDomain = async () => {
    if (!validation || !validation.success) return
    
    try {
      const response = await fetch(`http://localhost:8000/api/domains/brands/${brandId}/domains`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: validation.domain })
      })
      
      if (response.ok) {
        const newDomainData = await response.json()
        setDomains(prev => [...prev, newDomainData])
        setSelectedDomain(newDomainData.url)
        setSelectedDomainId(newDomainData.id)
        setShowAddDomain(false)
        setNewDomain('')
        setValidation(null)
      }
    } catch (error) {
      console.error('Failed to add domain:', error)
    }
  }

  const deleteDomain = async (domainId: number, domainUrl: string) => {
    if (!confirm(`Are you sure you want to remove ${domainUrl}?`)) return
    
    try {
      const response = await fetch(`http://localhost:8000/api/domains/domains/${domainId}`, {
        method: 'DELETE'
      })
      
      if (response.ok) {
        // Remove from list
        setDomains(prev => prev.filter(d => d.id !== domainId))
        
        // If this was the selected domain, clear selection
        if (selectedDomain === domainUrl) {
          setSelectedDomain('')
          setSelectedDomainId(null)
        }
      } else {
        console.error('Failed to delete domain')
      }
    } catch (error) {
      console.error('Failed to delete domain:', error)
    }
  }

  const filteredEvents = events.filter(event => {
    switch (filter) {
      case 'bots':
        return event.is_bot
      case 'on_demand':
        return event.is_bot && event.bot_type === 'on_demand'
      case 'spoofed':
        return event.potential_spoof
      default:
        return true
    }
  })

  const getTechnologyColor = (tech: string) => {
    const techLower = tech?.toLowerCase() || ''
    if (techLower.includes('wordpress')) return 'text-green-600 bg-green-100'
    if (techLower.includes('shopify')) return 'text-red-600 bg-red-100'
    if (techLower.includes('wix') || techLower.includes('squarespace')) return 'text-red-600 bg-red-100'
    if (techLower.includes('vercel') || techLower.includes('netlify')) return 'text-blue-600 bg-blue-100'
    if (techLower.includes('cloudflare')) return 'text-orange-600 bg-orange-100'
    return 'text-gray-600 bg-gray-100'
  }

  const getBotTypeColor = (type?: string) => {
    switch (type) {
      case 'on_demand':
        return 'bg-green-100 text-green-800 border-green-200'
      case 'indexing':
        return 'bg-blue-100 text-blue-800 border-blue-200'
      case 'training':
        return 'bg-purple-100 text-purple-800 border-purple-200'
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200'
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Real-Time AI Crawler Monitor</h2>
          <p className="text-gray-600 mt-1">
            Track AI bot traffic for {brandName || 'your brand'}
          </p>
        </div>
        <div className="flex items-center space-x-2">
          {selectedDomain && (
            <div className={`flex items-center px-3 py-1 rounded-full text-sm ${connected ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
              <div className={`w-2 h-2 rounded-full mr-2 ${connected ? 'bg-green-500' : 'bg-red-500'}`} />
              {connected ? 'Connected' : 'Disconnected'}
            </div>
          )}
        </div>
      </div>

      {/* Domain Management */}
      <div className="bg-white rounded-lg shadow p-4">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-900">Tracked Domains</h3>
          <button
            onClick={() => setShowAddDomain(true)}
            className="flex items-center px-3 py-1.5 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 text-sm"
          >
            <PlusIcon className="h-4 w-4 mr-1" />
            Add Domain
          </button>
        </div>

        {/* Domain List */}
        {domains.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            No domains added yet. Add your first domain to start tracking AI bot traffic.
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {domains.map(domain => (
              <div
                key={domain.id}
                className={`p-3 rounded-lg border transition-all ${
                  selectedDomain === domain.url 
                    ? 'border-indigo-500 bg-indigo-50' 
                    : 'border-gray-200 hover:border-gray-300'
                }`}
              >
                <div className="flex items-start justify-between">
                  <div 
                    className="flex-1 cursor-pointer"
                    onClick={() => {
                      setSelectedDomain(domain.url)
                      setSelectedDomainId(domain.id)
                    }}
                  >
                    <div className="flex items-center">
                      <GlobeAltIcon className="h-4 w-4 text-gray-400 mr-1" />
                      <span className="font-medium text-gray-900">{domain.url}</span>
                    </div>
                    {domain.technology && (
                      <span className={`inline-block mt-1 px-2 py-0.5 rounded-full text-xs font-medium ${getTechnologyColor(domain.technology)}`}>
                        {domain.technology}
                      </span>
                    )}
                  </div>
                  <div className="flex items-start ml-2 space-x-1">
                    {domain.is_trackable ? (
                      <CheckCircleIcon className="h-5 w-5 text-green-500" title="Trackable" />
                    ) : (
                      <XCircleIcon className="h-5 w-5 text-red-500" title="Not trackable" />
                    )}
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        deleteDomain(domain.id, domain.url)
                      }}
                      className="text-gray-400 hover:text-red-600 transition-colors"
                      title="Remove domain"
                    >
                      <TrashIcon className="h-4 w-4" />
                    </button>
                  </div>
                </div>
                <div 
                  className="mt-2 text-xs text-gray-500 cursor-pointer"
                  onClick={() => {
                    setSelectedDomain(domain.url)
                    setSelectedDomainId(domain.id)
                  }}
                >
                  <div>{domain.bot_hits_24h || 0} hits (24h)</div>
                  <div>{domain.total_bot_hits || 0} total hits</div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Add Domain Form */}
        {showAddDomain && (
          <div className="mt-4 p-4 bg-gray-50 rounded-lg">
            <div className="flex items-end space-x-3">
              <div className="flex-1">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Add New Domain
                </label>
                <input
                  type="text"
                  value={newDomain}
                  onChange={(e) => setNewDomain(e.target.value)}
                  onBlur={validateDomain}
                  placeholder="example.com or blog.example.com"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
                />
                <p className="text-xs text-gray-500 mt-1">Enter domain without https://</p>
              </div>
              <button
                onClick={validateDomain}
                disabled={validating || !newDomain.trim()}
                className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 disabled:opacity-50"
              >
                {validating ? 'Checking...' : 'Validate'}
              </button>
              <button
                onClick={() => {
                  setShowAddDomain(false)
                  setNewDomain('')
                  setValidation(null)
                }}
                className="px-4 py-2 border border-gray-300 rounded-md hover:bg-gray-50"
              >
                Cancel
              </button>
            </div>

            {/* Validation Result */}
            {validation && (
              <div className={`mt-3 p-3 rounded-lg ${validation.is_trackable ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'}`}>
                <div className="flex items-start">
                  {validation.is_trackable ? (
                    <CheckCircleIcon className="h-5 w-5 text-green-500 mt-0.5" />
                  ) : (
                    <XCircleIcon className="h-5 w-5 text-red-500 mt-0.5" />
                  )}
                  <div className="ml-2 flex-1">
                    <p className={`font-medium ${validation.is_trackable ? 'text-green-900' : 'text-red-900'}`}>
                      {validation.is_trackable ? 'Domain is trackable!' : 'Domain cannot be tracked'}
                    </p>
                    {validation.technology.length > 0 && (
                      <p className="text-sm mt-1">
                        Technology detected: {validation.technology.join(', ')}
                      </p>
                    )}
                    <p className="text-sm mt-1">{validation.recommendation}</p>
                    {validation.is_trackable && (
                      <button
                        onClick={addDomain}
                        className="mt-2 px-3 py-1 bg-green-600 text-white text-sm rounded-md hover:bg-green-700"
                      >
                        Add Domain
                      </button>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* View Mode Toggle - only show if domain is selected */}
      {selectedDomain && (
        <div className="bg-white rounded-lg shadow p-2">
          <div className="flex items-center space-x-2">
            <button
              onClick={() => setViewMode('live')}
              className={`flex items-center px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                viewMode === 'live'
                  ? 'bg-indigo-100 text-indigo-700'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              <SignalIcon className="h-4 w-4 mr-2" />
              Live Monitor
            </button>
            <button
              onClick={() => setViewMode('analytics')}
              className={`flex items-center px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                viewMode === 'analytics'
                  ? 'bg-indigo-100 text-indigo-700'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              <ChartBarIcon className="h-4 w-4 mr-2" />
              Analytics
            </button>
          </div>
        </div>
      )}

      {/* Show view based on mode */}
      {selectedDomain ? (
        viewMode === 'live' ? (
        <>
          {/* Stats Cards */}
          {stats && (
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="bg-white rounded-lg shadow p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-500">Total Hits</p>
                    <p className="text-2xl font-bold text-gray-900">{stats.total_hits.toLocaleString()}</p>
                  </div>
                  <div className="text-gray-400">
                    <BoltIcon className="h-8 w-8" />
                  </div>
                </div>
              </div>

              <div className="bg-white rounded-lg shadow p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-500">Bot Traffic</p>
                    <p className="text-2xl font-bold text-indigo-600">{stats.bot_hits.toLocaleString()}</p>
                    <p className="text-xs text-gray-500">{stats.bot_percentage.toFixed(1)}% of total</p>
                  </div>
                  <div className="text-indigo-400">
                    <svg className="h-8 w-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                    </svg>
                  </div>
                </div>
              </div>

              <div className="bg-white rounded-lg shadow p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-500">Live Queries</p>
                    <p className="text-2xl font-bold text-green-600">{stats.on_demand_hits.toLocaleString()}</p>
                    <p className="text-xs text-gray-500">On-demand bot hits</p>
                  </div>
                  <div className="text-green-400">
                    <BoltIcon className="h-8 w-8" />
                  </div>
                </div>
              </div>

              <div className="bg-white rounded-lg shadow p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-500">Spoofed</p>
                    <p className="text-2xl font-bold text-red-600">{stats.spoofed_hits.toLocaleString()}</p>
                    <p className="text-xs text-gray-500">{stats.spoof_rate.toFixed(1)}% of bots</p>
                  </div>
                  <div className="text-red-400">
                    <ExclamationTriangleIcon className="h-8 w-8" />
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Filter Tabs */}
          <div className="bg-white rounded-lg shadow">
            <div className="border-b border-gray-200">
              <nav className="flex space-x-8 px-6" aria-label="Tabs">
                {[
                  { id: 'all', label: 'All Traffic' },
                  { id: 'bots', label: 'Bot Traffic' },
                  { id: 'on_demand', label: 'Live Queries' },
                  { id: 'spoofed', label: 'Spoofed' }
                ].map((tab) => (
                  <button
                    key={tab.id}
                    onClick={() => setFilter(tab.id as any)}
                    className={`py-3 px-1 border-b-2 font-medium text-sm ${
                      filter === tab.id
                        ? 'border-indigo-500 text-indigo-600'
                        : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                    }`}
                  >
                    {tab.label}
                    {tab.id === 'on_demand' && stats?.on_demand_hits ? (
                      <span className="ml-2 bg-green-100 text-green-800 px-2 py-0.5 rounded-full text-xs">
                        {stats.on_demand_hits}
                      </span>
                    ) : null}
                    {tab.id === 'spoofed' && stats?.spoofed_hits ? (
                      <span className="ml-2 bg-red-100 text-red-800 px-2 py-0.5 rounded-full text-xs">
                        {stats.spoofed_hits}
                      </span>
                    ) : null}
                  </button>
                ))}
              </nav>
            </div>

            {/* Live Event Stream */}
            <div className="p-4">
              <div className="mb-2 text-sm text-gray-500">
                Showing events for: <span className="font-medium text-gray-900">{selectedDomain}</span>
              </div>
              <div className="space-y-2 max-h-96 overflow-y-auto">
                {filteredEvents.length === 0 ? (
                  <div className="text-center py-8 text-gray-500">
                    No events yet. Waiting for traffic...
                  </div>
                ) : (
                  filteredEvents.map((event) => (
                    <div
                      key={event.id}
                      className={`flex items-center justify-between p-3 rounded-lg border ${
                        event.potential_spoof 
                          ? 'bg-red-50 border-red-200' 
                          : event.bot_type === 'on_demand'
                          ? 'bg-green-50 border-green-200'
                          : event.is_bot
                          ? 'bg-blue-50 border-blue-200'
                          : 'bg-gray-50 border-gray-200'
                      }`}
                    >
                      <div className="flex items-center space-x-4">
                        {/* Bot Icon/Badge */}
                        {event.is_bot && (
                          <div className="flex items-center">
                            {event.verified ? (
                              <CheckCircleIcon className="h-5 w-5 text-green-500" />
                            ) : event.potential_spoof ? (
                              <ExclamationTriangleIcon className="h-5 w-5 text-red-500" />
                            ) : (
                              <XCircleIcon className="h-5 w-5 text-gray-400" />
                            )}
                          </div>
                        )}

                        {/* Bot Info */}
                        <div className="flex-1">
                          <div className="flex items-center space-x-2">
                            {event.is_bot ? (
                              <>
                                <span className="font-semibold text-gray-900">
                                  {event.bot_name || 'Unknown Bot'}
                                </span>
                                <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${getBotTypeColor(event.bot_type)}`}>
                                  {event.bot_type || 'unknown'}
                                </span>
                                {event.bot_type === 'on_demand' && (
                                  <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                                    LIVE QUERY
                                  </span>
                                )}
                                {event.potential_spoof && (
                                  <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
                                    SPOOFED
                                  </span>
                                )}
                              </>
                            ) : (
                              <span className="text-gray-600">Regular Traffic</span>
                            )}
                          </div>
                          <div className="text-sm text-gray-500 mt-1">
                            <span className="font-medium">{event.status}</span>
                            <span className="mx-2">{event.method}</span>
                            <span className="font-mono">{event.path}</span>
                          </div>
                        </div>
                      </div>

                      {/* Timestamp */}
                      <div className="text-xs text-gray-500">
                        {new Date(event.timestamp).toLocaleTimeString()}
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        </>
        ) : (
          // Analytics View
          <BotAnalytics domainId={selectedDomainId!} domainUrl={selectedDomain} />
        )
      ) : (
        <div className="bg-gray-50 rounded-lg p-8 text-center">
          <GlobeAltIcon className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <p className="text-gray-600">Select or add a domain to view AI bot traffic</p>
        </div>
      )}
    </div>
  )
}