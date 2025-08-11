'use client'

import { useState, useEffect, useRef } from 'react'
import { CheckCircleIcon, XCircleIcon, ExclamationTriangleIcon, BoltIcon } from '@heroicons/react/24/outline'

interface BotEvent {
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

export default function CrawlerMonitor() {
  const [events, setEvents] = useState<BotEvent[]>([])
  const [stats, setStats] = useState<Stats | null>(null)
  const [connected, setConnected] = useState(false)
  const [filter, setFilter] = useState<'all' | 'bots' | 'on_demand' | 'spoofed'>('all')
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout>()

  useEffect(() => {
    connectWebSocket()
    loadInitialStats()

    return () => {
      if (wsRef.current) {
        wsRef.current.close()
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
      }
    }
  }, [])

  const connectWebSocket = () => {
    try {
      const ws = new WebSocket('ws://localhost:8000/api/crawler/ws/monitor')
      
      ws.onopen = () => {
        console.log('WebSocket connected')
        setConnected(true)
      }

      ws.onmessage = (event) => {
        const data = JSON.parse(event.data)
        
        if (data.type === 'initial') {
          setStats(data.stats)
          setEvents(data.recent_events || [])
        } else if (data.is_bot !== undefined) {
          // New bot event
          setEvents(prev => [data, ...prev].slice(0, 100))
          
          // Update stats locally for instant feedback
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

  const loadInitialStats = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/crawler/monitor/stats')
      if (response.ok) {
        const data = await response.json()
        setStats(data)
      }
    } catch (error) {
      console.error('Failed to load stats:', error)
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

  const getStatusColor = (status: number) => {
    if (status >= 200 && status < 300) return 'text-green-600'
    if (status >= 400 && status < 500) return 'text-yellow-600'
    if (status >= 500) return 'text-red-600'
    return 'text-gray-600'
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Real-Time AI Crawler Monitor</h2>
          <p className="text-gray-600 mt-1">
            Live monitoring of AI bot traffic hitting your site
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <div className={`flex items-center px-3 py-1 rounded-full text-sm ${connected ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
            <div className={`w-2 h-2 rounded-full mr-2 ${connected ? 'bg-green-500' : 'bg-red-500'}`} />
            {connected ? 'Connected' : 'Disconnected'}
          </div>
        </div>
      </div>

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
          <div className="space-y-2 max-h-96 overflow-y-auto">
            {filteredEvents.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                No events yet. Waiting for traffic...
              </div>
            ) : (
              filteredEvents.map((event, idx) => (
                <div
                  key={`${event.timestamp}-${idx}`}
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
                                LIVE QUERY!
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
                        <span className={getStatusColor(event.status)}>{event.status}</span>
                        <span className="mx-2">{event.method}</span>
                        <span className="font-mono">{event.path}</span>
                        {event.country && (
                          <span className="ml-2 text-xs">({event.country})</span>
                        )}
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

      {/* Bot Distribution */}
      {stats && Object.keys(stats.by_provider).length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-lg font-semibold mb-4">Bot Providers</h3>
            <div className="space-y-2">
              {Object.entries(stats.by_provider).map(([provider, count]) => (
                <div key={provider} className="flex items-center justify-between">
                  <span className="text-gray-700 capitalize">{provider}</span>
                  <span className="font-semibold">{count}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-lg font-semibold mb-4">Bot Types</h3>
            <div className="space-y-2">
              {Object.entries(stats.by_type).map(([type, count]) => (
                <div key={type} className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <span className="text-gray-700 capitalize">{type}</span>
                    {type === 'on_demand' && (
                      <span className="text-xs bg-green-100 text-green-800 px-2 py-0.5 rounded">Live</span>
                    )}
                  </div>
                  <span className="font-semibold">{count}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Info Box */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <h4 className="text-sm font-medium text-blue-900 mb-2">How to Connect Your Site</h4>
        <div className="text-sm text-blue-700 space-y-2">
          <p>
            <strong>Cloudflare:</strong> Deploy our Worker script or use Logpush to forward logs to <code className="bg-blue-100 px-1 rounded">POST http://localhost:8000/api/crawler/ingest/cloudflare</code>
          </p>
          <p>
            <strong>Vercel:</strong> Configure Log Drains to <code className="bg-blue-100 px-1 rounded">POST http://localhost:8000/api/crawler/ingest/vercel</code>
          </p>
          <p>
            <strong>Other:</strong> Send logs to <code className="bg-blue-100 px-1 rounded">POST http://localhost:8000/api/crawler/ingest/generic</code>
          </p>
          <p className="pt-2 font-medium">
            ✨ Real-time detection of ChatGPT, Perplexity, Claude, and other AI crawlers with IP verification and spoof detection.
          </p>
        </div>
      </div>
    </div>
  )
}