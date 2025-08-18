'use client'

import { useState, useEffect } from 'react'
import { format } from 'date-fns'
import { 
  PlayIcon, 
  PlusIcon, 
  TrashIcon,
  ChevronDownIcon,
  ChevronRightIcon,
  ClipboardDocumentIcon as CopyIcon,
  ArrowTopRightOnSquareIcon as ExternalLinkIcon,
  ExclamationCircleIcon as AlertCircleIcon,
  CheckCircleIcon,
  XCircleIcon,
  ClockIcon,
  HashtagIcon as HashIcon,
  CodeBracketIcon as CodeIcon,
  GlobeAltIcon,
  ServerIcon,
  DocumentTextIcon,
  LinkIcon,
  ShieldCheckIcon,
  ExclamationTriangleIcon
} from '@heroicons/react/24/outline'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'
import { Separator } from '@/components/ui/separator'
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle, SheetTrigger } from '@/components/ui/sheet'
import { cn } from '@/lib/utils'
import Countries from './Countries'
import GroundingTestGrid from './GroundingTestGrid'
import { GROUNDING_MODES, getGroundingDisplayLabel, getProviderFromModel } from '../constants/grounding'

interface PromptTemplate {
  id: number
  brand_name: string
  template_name: string
  prompt_text: string
  prompt_type: string
  model_name?: string
  countries: string[]
  grounding_modes: string[]
  is_active: boolean
  created_at: string
  // Enhanced metadata
  provider?: string
  last_run_at?: string
  total_runs?: number
  config_hash?: string
  canonical_json?: any
  prompt_hash?: string
  prompt_hash_full?: string
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
  country_code: string
  grounding_mode: string
  status: string
  started_at: string | null
  completed_at: string | null
  error_message: string | null
  created_at: string
  // Enhanced metadata
  provider?: string
  api_used?: string
  grounded_effective?: boolean
  tool_call_count?: number
  citations?: any[]
  system_fingerprint?: string
  temperature?: number
  seed?: number
  finish_reason?: string
  content_filtered?: boolean
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

// Helper function to get provider badge color
const getProviderColor = (provider: string) => {
  switch (provider?.toLowerCase()) {
    case 'openai':
      return 'bg-green-100 text-green-800'
    case 'vertex':
    case 'gemini':
      return 'bg-blue-100 text-blue-800'
    default:
      return 'bg-gray-100 text-gray-800'
  }
}

// Helper function to get status badge
const getStatusBadge = (status: string) => {
  switch (status?.toLowerCase()) {
    case 'completed':
      return <Badge className="bg-green-100 text-green-800">Completed</Badge>
    case 'running':
      return <Badge className="bg-yellow-100 text-yellow-800">Running</Badge>
    case 'failed':
      return <Badge className="bg-red-100 text-red-800">Failed</Badge>
    default:
      return <Badge className="bg-gray-100 text-gray-800">{status}</Badge>
  }
}

export default function PromptTrackingEnhanced({ brandName, brandId }: PromptTrackingProps) {
  const [activeTab, setActiveTab] = useState('templates')
  const [templates, setTemplates] = useState<PromptTemplate[]>([])
  const [runs, setRuns] = useState<PromptRun[]>([])
  const [analytics, setAnalytics] = useState<Analytics | null>(null)
  const [loading, setLoading] = useState(false)

  // Fetch templates
  const fetchTemplates = async () => {
    try {
      const response = await fetch('/api/prompt-tracking/templates')
      if (response.ok) {
        const data = await response.json()
        // Handle both array and object with templates property
        setTemplates(Array.isArray(data) ? data : (data.templates || []))
      }
    } catch (error) {
      console.error('Error fetching templates:', error)
    }
  }

  // Fetch runs
  const fetchRuns = async () => {
    try {
      const response = await fetch('/api/prompt-tracking/runs')
      if (response.ok) {
        const data = await response.json()
        // Handle both array and object with runs property
        setRuns(Array.isArray(data) ? data : (data.runs || []))
      }
    } catch (error) {
      console.error('Error fetching runs:', error)
    }
  }

  // Fetch analytics
  const fetchAnalytics = async () => {
    try {
      const response = await fetch(`/api/prompt-tracking/analytics/${encodeURIComponent(brandName)}`)
      if (response.ok) {
        const data = await response.json()
        setAnalytics(data)
      }
    } catch (error) {
      console.error('Error fetching analytics:', error)
    }
  }

  useEffect(() => {
    fetchTemplates()
    fetchRuns()
    fetchAnalytics()
  }, [brandName])

  return (
    <TooltipProvider>
      <div className="p-6">
        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="grid w-full grid-cols-5">
            <TabsTrigger value="templates">Templates</TabsTrigger>
            <TabsTrigger value="results">Results</TabsTrigger>
            <TabsTrigger value="analytics">Analytics</TabsTrigger>
            <TabsTrigger value="countries">Countries</TabsTrigger>
            <TabsTrigger value="grounding-test">Grounding Test</TabsTrigger>
          </TabsList>

          <TabsContent value="templates" className="mt-6">
            <div className="space-y-4">
              <div className="flex justify-between items-center mb-4">
                <h3 className="text-lg font-semibold">Prompt Templates</h3>
                <Button>
                  <PlusIcon className="h-4 w-4 mr-2" />
                  New Template
                </Button>
              </div>

              <div className="space-y-3">
                {templates && templates.length > 0 ? (
                  templates.map((template) => (
                    <Card key={template.id} className="hover:shadow-lg transition-shadow">
                      <CardHeader className="pb-3">
                        <div className="flex justify-between items-start">
                          <div className="flex-1">
                            <CardTitle className="text-base flex items-center gap-2">
                              {template.template_name}
                              <Badge className={cn("ml-2", getProviderColor(template.provider || getProviderFromModel(template.model_name || '')))}>
                                {template.provider || getProviderFromModel(template.model_name || '')}
                              </Badge>
                            </CardTitle>
                            <CardDescription className="mt-1 text-sm">
                              Model: {template.model_name || 'Not set'}
                            </CardDescription>
                          </div>
                          <div className="flex gap-2">
                            <TooltipProvider>
                              <Tooltip>
                                <TooltipTrigger asChild>
                                  <Button variant="outline" size="sm">
                                    <PlayIcon className="h-4 w-4" />
                                  </Button>
                                </TooltipTrigger>
                                <TooltipContent>Run Template</TooltipContent>
                              </Tooltip>
                            </TooltipProvider>
                            <Sheet>
                              <SheetTrigger asChild>
                                <Button variant="outline" size="sm">
                                  <ChevronRightIcon className="h-4 w-4" />
                                </Button>
                              </SheetTrigger>
                              <SheetContent className="w-[600px] overflow-y-auto">
                                <SheetHeader>
                                  <SheetTitle>{template.template_name}</SheetTitle>
                                  <SheetDescription>Template Configuration & Metadata</SheetDescription>
                                </SheetHeader>
                                
                                <div className="mt-6 space-y-4">
                                  {/* System Parameters Section */}
                                  <div className="space-y-3">
                                    <h3 className="font-semibold flex items-center gap-2">
                                      <ServerIcon className="h-4 w-4" />
                                      System Parameters
                                    </h3>
                                    <div className="bg-gray-50 rounded-lg p-4 space-y-2 text-sm">
                                      <div className="flex justify-between">
                                        <span className="text-gray-600">Provider:</span>
                                        <span className="font-mono">{template.provider || getProviderFromModel(template.model_name || '')}</span>
                                      </div>
                                      <div className="flex justify-between">
                                        <span className="text-gray-600">Model:</span>
                                        <span className="font-mono">{template.model_name}</span>
                                      </div>
                                      <div className="flex justify-between">
                                        <span className="text-gray-600">Temperature:</span>
                                        <span className="font-mono">{template.temperature || 0.7}</span>
                                      </div>
                                      <div className="flex justify-between">
                                        <span className="text-gray-600">Seed:</span>
                                        <span className="font-mono">{template.seed || 42}</span>
                                      </div>
                                      <div className="flex justify-between">
                                        <span className="text-gray-600">Countries:</span>
                                        <span className="font-mono">{template.countries?.join(', ') || 'None'}</span>
                                      </div>
                                      <div className="flex justify-between">
                                        <span className="text-gray-600">Grounding Modes:</span>
                                        <span className="font-mono">{template.grounding_modes?.join(', ') || 'None'}</span>
                                      </div>
                                    </div>
                                  </div>

                                  <Separator />

                                  {/* Canonical JSON Section */}
                                  <div className="space-y-3">
                                    <h3 className="font-semibold flex items-center gap-2">
                                      <CodeIcon className="h-4 w-4" />
                                      Canonical JSON
                                    </h3>
                                    <div className="bg-gray-50 rounded-lg p-4">
                                      <div className="flex items-center justify-between mb-2">
                                        <span className="text-sm text-gray-600">SHA-256 Hash:</span>
                                        <code className="text-xs font-mono bg-white px-2 py-1 rounded">
                                          {template.prompt_hash_full || template.prompt_hash || 'Not computed'}
                                        </code>
                                      </div>
                                      <pre className="text-xs font-mono overflow-x-auto bg-white p-3 rounded border">
                                        {JSON.stringify(template.canonical_json || {
                                          prompt: template.prompt_text,
                                          model: template.model_name,
                                          countries: template.countries,
                                          grounding_modes: template.grounding_modes,
                                          temperature: template.temperature,
                                          seed: template.seed
                                        }, null, 2)}
                                      </pre>
                                    </div>
                                  </div>

                                  <Separator />

                                  {/* Metadata Section */}
                                  <div className="space-y-3">
                                    <h3 className="font-semibold flex items-center gap-2">
                                      <DocumentTextIcon className="h-4 w-4" />
                                      Metadata
                                    </h3>
                                    <div className="bg-gray-50 rounded-lg p-4 space-y-2 text-sm">
                                      <div className="flex justify-between">
                                        <span className="text-gray-600">Created:</span>
                                        <span>{template.created_at ? format(new Date(template.created_at), 'PPp') : 'Unknown'}</span>
                                      </div>
                                      <div className="flex justify-between">
                                        <span className="text-gray-600">Last Run:</span>
                                        <span>{template.last_run_at ? format(new Date(template.last_run_at), 'PPp') : 'Never'}</span>
                                      </div>
                                      <div className="flex justify-between">
                                        <span className="text-gray-600">Total Runs:</span>
                                        <span>{template.total_runs || 0}</span>
                                      </div>
                                      <div className="flex justify-between">
                                        <span className="text-gray-600">Status:</span>
                                        <Badge className={template.is_active ? "bg-green-100 text-green-800" : "bg-gray-100 text-gray-800"}>
                                          {template.is_active ? 'Active' : 'Inactive'}
                                        </Badge>
                                      </div>
                                    </div>
                                  </div>

                                  {/* Prompt Text */}
                                  <div className="space-y-3">
                                    <h3 className="font-semibold">Prompt Text</h3>
                                    <div className="bg-gray-50 rounded-lg p-4">
                                      <p className="text-sm whitespace-pre-wrap">{template.prompt_text}</p>
                                    </div>
                                  </div>
                                </div>
                              </SheetContent>
                            </Sheet>
                          </div>
                        </div>
                      </CardHeader>
                      <CardContent>
                        <div className="grid grid-cols-3 gap-4 text-sm">
                          <div>
                            <span className="text-gray-600">Last Run:</span>
                            <p className="font-medium">{template.last_run_at ? format(new Date(template.last_run_at), 'PP') : 'Never'}</p>
                          </div>
                          <div>
                            <span className="text-gray-600">Total Runs:</span>
                            <p className="font-medium">{template.total_runs || 0}</p>
                          </div>
                          <div>
                            <span className="text-gray-600">Countries:</span>
                            <p className="font-medium">{template.countries?.length || 0} selected</p>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  ))
                ) : (
                  <div className="text-center py-8 text-gray-500">
                    No templates found. Create your first template to get started.
                  </div>
                )}
              </div>
            </div>
          </TabsContent>

          <TabsContent value="results" className="mt-6">
            <div className="space-y-4">
              <div className="flex justify-between items-center mb-4">
                <h3 className="text-lg font-semibold">Run Results</h3>
                <Button variant="outline" onClick={fetchRuns}>
                  Refresh
                </Button>
              </div>

              <div className="space-y-3">
                {runs && runs.length > 0 ? (
                  runs.map((run) => (
                    <Card key={run.id} className="hover:shadow-lg transition-shadow">
                      <CardHeader className="pb-3">
                        {/* Provenance Strip */}
                        <div className="flex flex-wrap gap-2 mb-3">
                          <Badge variant="outline" className="text-xs">
                            <ServerIcon className="h-3 w-3 mr-1" />
                            {run.provider || getProviderFromModel(run.model_name)}
                          </Badge>
                          <Badge variant="outline" className="text-xs">
                            <HashIcon className="h-3 w-3 mr-1" />
                            {run.system_fingerprint?.slice(0, 8) || 'No fingerprint'}
                          </Badge>
                          <Badge variant="outline" className="text-xs">
                            {run.api_used || 'API'}
                          </Badge>
                          {run.grounded_effective && (
                            <Badge className="bg-blue-100 text-blue-800 text-xs">
                              <GlobeAltIcon className="h-3 w-3 mr-1" />
                              Grounded
                            </Badge>
                          )}
                          {run.content_filtered && (
                            <Badge className="bg-yellow-100 text-yellow-800 text-xs">
                              <ExclamationTriangleIcon className="h-3 w-3 mr-1" />
                              Filtered
                            </Badge>
                          )}
                        </div>

                        <div className="flex justify-between items-start">
                          <div className="flex-1">
                            <CardTitle className="text-base">
                              {run.template_name || `Run #${run.id}`}
                            </CardTitle>
                            <CardDescription className="mt-1 text-sm">
                              {run.model_name} • {run.country_code} • {getGroundingDisplayLabel(run.grounding_mode)}
                            </CardDescription>
                          </div>
                          <div className="flex items-center gap-2">
                            {getStatusBadge(run.status)}
                            <Sheet>
                              <SheetTrigger asChild>
                                <Button variant="outline" size="sm">
                                  <ChevronRightIcon className="h-4 w-4" />
                                </Button>
                              </SheetTrigger>
                              <SheetContent className="w-[600px] overflow-y-auto">
                                <SheetHeader>
                                  <SheetTitle>Run Details</SheetTitle>
                                  <SheetDescription>Complete run information and metadata</SheetDescription>
                                </SheetHeader>

                                <Accordion type="single" collapsible className="mt-6">
                                  {/* Provenance Section */}
                                  <AccordionItem value="provenance">
                                    <AccordionTrigger>
                                      <div className="flex items-center gap-2">
                                        <ServerIcon className="h-4 w-4" />
                                        Provenance
                                      </div>
                                    </AccordionTrigger>
                                    <AccordionContent>
                                      <div className="space-y-2 text-sm">
                                        <div className="grid grid-cols-2 gap-2">
                                          <div>
                                            <span className="text-gray-600">Provider:</span>
                                            <p className="font-mono">{run.provider || getProviderFromModel(run.model_name)}</p>
                                          </div>
                                          <div>
                                            <span className="text-gray-600">API:</span>
                                            <p className="font-mono">{run.api_used || 'Unknown'}</p>
                                          </div>
                                          <div>
                                            <span className="text-gray-600">Model:</span>
                                            <p className="font-mono">{run.model_name}</p>
                                          </div>
                                          <div>
                                            <span className="text-gray-600">Fingerprint:</span>
                                            <p className="font-mono text-xs">{run.system_fingerprint || 'None'}</p>
                                          </div>
                                          <div>
                                            <span className="text-gray-600">Temperature:</span>
                                            <p className="font-mono">{run.temperature || 0.7}</p>
                                          </div>
                                          <div>
                                            <span className="text-gray-600">Seed:</span>
                                            <p className="font-mono">{run.seed || 42}</p>
                                          </div>
                                        </div>
                                      </div>
                                    </AccordionContent>
                                  </AccordionItem>

                                  {/* Grounding Section */}
                                  <AccordionItem value="grounding">
                                    <AccordionTrigger>
                                      <div className="flex items-center gap-2">
                                        <GlobeAltIcon className="h-4 w-4" />
                                        Grounding
                                      </div>
                                    </AccordionTrigger>
                                    <AccordionContent>
                                      <div className="space-y-2 text-sm">
                                        <div className="flex justify-between">
                                          <span className="text-gray-600">Mode Requested:</span>
                                          <Badge variant="outline">{getGroundingDisplayLabel(run.grounding_mode)}</Badge>
                                        </div>
                                        <div className="flex justify-between">
                                          <span className="text-gray-600">Grounded Effective:</span>
                                          <Badge className={run.grounded_effective ? "bg-green-100 text-green-800" : "bg-gray-100 text-gray-800"}>
                                            {run.grounded_effective ? 'Yes' : 'No'}
                                          </Badge>
                                        </div>
                                        <div className="flex justify-between">
                                          <span className="text-gray-600">Tool Calls:</span>
                                          <span className="font-mono">{run.tool_call_count || 0}</span>
                                        </div>
                                      </div>
                                    </AccordionContent>
                                  </AccordionItem>

                                  {/* Citations Section */}
                                  {run.citations && run.citations.length > 0 && (
                                    <AccordionItem value="citations">
                                      <AccordionTrigger>
                                        <div className="flex items-center gap-2">
                                          <LinkIcon className="h-4 w-4" />
                                          Citations ({run.citations.length})
                                        </div>
                                      </AccordionTrigger>
                                      <AccordionContent>
                                        <div className="space-y-2">
                                          {run.citations.map((citation: any, idx: number) => (
                                            <div key={idx} className="border rounded-lg p-3">
                                              <a 
                                                href={citation.uri || citation.url} 
                                                target="_blank" 
                                                rel="noopener noreferrer"
                                                className="text-blue-600 hover:underline flex items-center gap-1 text-sm"
                                              >
                                                {citation.title || 'Untitled'}
                                                <ExternalLinkIcon className="h-3 w-3" />
                                              </a>
                                              <p className="text-xs text-gray-600 mt-1 font-mono truncate">
                                                {citation.uri || citation.url}
                                              </p>
                                            </div>
                                          ))}
                                        </div>
                                      </AccordionContent>
                                    </AccordionItem>
                                  )}

                                  {/* Timing Section */}
                                  <AccordionItem value="timing">
                                    <AccordionTrigger>
                                      <div className="flex items-center gap-2">
                                        <ClockIcon className="h-4 w-4" />
                                        Timing
                                      </div>
                                    </AccordionTrigger>
                                    <AccordionContent>
                                      <div className="space-y-2 text-sm">
                                        <div className="flex justify-between">
                                          <span className="text-gray-600">Started:</span>
                                          <span>{run.started_at ? format(new Date(run.started_at), 'PPpp') : 'N/A'}</span>
                                        </div>
                                        <div className="flex justify-between">
                                          <span className="text-gray-600">Completed:</span>
                                          <span>{run.completed_at ? format(new Date(run.completed_at), 'PPpp') : 'N/A'}</span>
                                        </div>
                                        {run.started_at && run.completed_at && (
                                          <div className="flex justify-between">
                                            <span className="text-gray-600">Duration:</span>
                                            <span className="font-mono">
                                              {Math.round((new Date(run.completed_at).getTime() - new Date(run.started_at).getTime()) / 1000)}s
                                            </span>
                                          </div>
                                        )}
                                        <div className="flex justify-between">
                                          <span className="text-gray-600">Finish Reason:</span>
                                          <Badge variant="outline">{run.finish_reason || 'Unknown'}</Badge>
                                        </div>
                                      </div>
                                    </AccordionContent>
                                  </AccordionItem>
                                </Accordion>

                                {/* Link to Template */}
                                <div className="mt-6 pt-6 border-t">
                                  <Button 
                                    variant="outline" 
                                    className="w-full"
                                    onClick={() => setActiveTab('templates')}
                                  >
                                    <DocumentTextIcon className="h-4 w-4 mr-2" />
                                    View Template
                                  </Button>
                                </div>
                              </SheetContent>
                            </Sheet>
                          </div>
                        </div>
                      </CardHeader>
                      
                      {run.status === 'completed' && run.completed_at && (
                        <CardContent>
                          <div className="text-sm text-gray-600">
                            <p>Completed {format(new Date(run.completed_at), 'PPp')}</p>
                          </div>
                        </CardContent>
                      )}
                    </Card>
                  ))
                ) : (
                  <div className="text-center py-8 text-gray-500">
                    No run results yet. Run a template to see results here.
                  </div>
                )}
              </div>
            </div>
          </TabsContent>

          <TabsContent value="analytics" className="mt-6">
            {analytics && (
              <div className="space-y-6">
                <Card>
                  <CardHeader>
                    <CardTitle>Overall Statistics</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-3 gap-4">
                      <div>
                        <p className="text-sm text-gray-600">Total Runs</p>
                        <p className="text-2xl font-bold">{analytics.statistics.total_runs}</p>
                      </div>
                      <div>
                        <p className="text-sm text-gray-600">Mention Rate</p>
                        <p className="text-2xl font-bold">{(analytics.statistics.mention_rate * 100).toFixed(1)}%</p>
                      </div>
                      <div>
                        <p className="text-sm text-gray-600">Avg Confidence</p>
                        <p className="text-2xl font-bold">{analytics.statistics.avg_confidence.toFixed(1)}%</p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </div>
            )}
          </TabsContent>

          <TabsContent value="countries" className="mt-6">
            <Countries />
          </TabsContent>

          <TabsContent value="grounding-test" className="mt-6">
            <GroundingTestGrid />
          </TabsContent>
        </Tabs>
      </div>
    </TooltipProvider>
  )
}