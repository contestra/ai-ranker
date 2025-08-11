'use client'

import { useState } from 'react'
import jsPDF from 'jspdf'

interface CrawlabilityRequest {
  url: string
  check_content?: boolean
  check_performance?: boolean
}

interface RobotsAnalysis {
  has_llm_rules: boolean
  llm_access: Record<string, boolean>
  critical_paths_blocked: string[]
  sitemap_url: string | null
  crawl_delay: number | null
  warnings: string[]
  recommendations: string[]
  score: number
  explicit_llm_agents?: string[]
  wildcard_allowed_agents?: string[]
  policies_blocked?: boolean
}

interface CrawlabilityResponse {
  url: string
  timestamp: string
  robots_analysis: RobotsAnalysis | null
  overall_score: number
  grade: string
  critical_issues: Array<{
    type: string
    severity: string
    message: string
    solution: string
  }>
  recommendations: string[]
  advanced_checks?: any
  corrected_robots?: string
}

interface LLMCrawlabilityProps {
  brandId: number
  brandName: string
}

export default function LLMCrawlability({ brandId, brandName }: LLMCrawlabilityProps) {
  const [url, setUrl] = useState('')
  const [loading, setLoading] = useState(false)
  const [results, setResults] = useState<CrawlabilityResponse | null>(null)
  const [error, setError] = useState('')
  const [exampleRobots, setExampleRobots] = useState(false)
  const [runAdvanced, setRunAdvanced] = useState(true) // Always run advanced checks

  const generatePDFReport = () => {
    if (!results) return

    const pdf = new jsPDF()
    let yPos = 20

    // Title
    pdf.setFontSize(20)
    pdf.text('LLM Crawlability Report', 20, yPos)
    yPos += 10

    // URL and Date
    pdf.setFontSize(10)
    pdf.text(`URL: ${results.url}`, 20, yPos)
    yPos += 5
    pdf.text(`Date: ${new Date(results.timestamp).toLocaleString()}`, 20, yPos)
    yPos += 10

    // Score and Grade
    pdf.setFontSize(16)
    pdf.text(`Overall Score: ${results.overall_score}/100 (Grade: ${results.grade})`, 20, yPos)
    yPos += 10

    // Summary (from recommendations)
    const summary = results.recommendations.find(r => r.startsWith('📊'))
    if (summary) {
      pdf.setFontSize(12)
      const summaryText = summary.replace('📊 ', '')
      const lines = pdf.splitTextToSize(summaryText, 170)
      pdf.text(lines, 20, yPos)
      yPos += lines.length * 5 + 5
    }

    // Critical Issues
    if (results.critical_issues.length > 0) {
      pdf.setFontSize(14)
      pdf.text('Critical Issues:', 20, yPos)
      yPos += 7
      pdf.setFontSize(10)
      results.critical_issues.forEach(issue => {
        const issueText = `• [${issue.severity.toUpperCase()}] ${issue.message}`
        const lines = pdf.splitTextToSize(issueText, 170)
        pdf.text(lines, 25, yPos)
        yPos += lines.length * 5
        
        if (issue.solution) {
          const solutionText = `  Solution: ${issue.solution}`
          const solutionLines = pdf.splitTextToSize(solutionText, 165)
          pdf.text(solutionLines, 25, yPos)
          yPos += solutionLines.length * 5
        }
        yPos += 3
        
        // Check if we need a new page
        if (yPos > 270) {
          pdf.addPage()
          yPos = 20
        }
      })
    }

    // Robots.txt Analysis
    if (results.robots_analysis) {
      pdf.setFontSize(14)
      pdf.text('Robots.txt Analysis:', 20, yPos)
      yPos += 7
      pdf.setFontSize(10)
      
      // Explicit agents
      if (results.robots_analysis.explicit_llm_agents && results.robots_analysis.explicit_llm_agents.length > 0) {
        pdf.setFontSize(11)
        pdf.text('Explicitly Configured LLM Agents:', 25, yPos)
        yPos += 5
        pdf.setFontSize(10)
        const explicitText = results.robots_analysis.explicit_llm_agents.join(', ')
        const explicitLines = pdf.splitTextToSize(explicitText, 160)
        pdf.text(explicitLines, 30, yPos)
        yPos += explicitLines.length * 5 + 2
      }
      
      // Wildcard agents
      if (results.robots_analysis.wildcard_allowed_agents && results.robots_analysis.wildcard_allowed_agents.length > 0) {
        pdf.setFontSize(11)
        pdf.text('Allowed via Wildcard (*):', 25, yPos)
        yPos += 5
        pdf.setFontSize(10)
        const wildcardList = results.robots_analysis.wildcard_allowed_agents
        const wildcardText = wildcardList.length > 10 
          ? `${wildcardList.slice(0, 10).join(', ')} (and ${wildcardList.length - 10} more)`
          : wildcardList.join(', ')
        const wildcardLines = pdf.splitTextToSize(wildcardText, 160)
        pdf.text(wildcardLines, 30, yPos)
        yPos += wildcardLines.length * 5 + 2
      }
      
      // Key metrics
      pdf.text(`Has LLM-specific rules: ${results.robots_analysis.has_llm_rules ? 'Yes' : 'No'}`, 25, yPos)
      yPos += 5
      pdf.text(`Sitemap declared: ${results.robots_analysis.sitemap_url ? 'Yes' : 'No'}`, 25, yPos)
      yPos += 5
      
      // Policy block warning
      if (results.robots_analysis.policies_blocked) {
        pdf.setFontSize(10)
        pdf.setTextColor(255, 152, 0) // Orange for warning
        pdf.text('⚠️ /policies/ is blocked - affects returns/shipping/terms discoverability', 25, yPos)
        pdf.setTextColor(0, 0, 0) // Reset to black
        yPos += 5
      }
      yPos += 5
    }

    // Check if we need a new page for advanced checks
    if (yPos > 220) {
      pdf.addPage()
      yPos = 20
    }

    // Advanced Checks Summary
    if (results.advanced_checks && !results.advanced_checks.error) {
      pdf.setFontSize(14)
      pdf.text('Advanced Checks:', 20, yPos)
      yPos += 7
      pdf.setFontSize(10)
      
      // JavaScript content
      if (results.advanced_checks.no_js_content) {
        const jsStatus = results.advanced_checks.no_js_content.content_accessible ? '✓ Accessible' : '✗ Requires JS'
        pdf.text(`Content without JavaScript: ${jsStatus}`, 25, yPos)
        yPos += 5
        pdf.text(`Word count: ${results.advanced_checks.no_js_content.word_count || 0}`, 25, yPos)
        yPos += 5
      }
      
      // CDN/WAF
      if (results.advanced_checks.cdn_waf) {
        if (results.advanced_checks.cdn_waf.cdn_provider) {
          pdf.text(`CDN Provider: ${results.advanced_checks.cdn_waf.cdn_provider}`, 25, yPos)
          yPos += 5
        }
      }
      
      // Meta headers
      if (results.advanced_checks.meta_headers) {
        if (results.advanced_checks.meta_headers.has_noindex) {
          pdf.text('✗ Has noindex directive', 25, yPos)
          yPos += 5
        }
      }
      yPos += 5
    }

    // Recommendations
    if (results.recommendations.length > 0) {
      // Check if we need a new page
      if (yPos > 200) {
        pdf.addPage()
        yPos = 20
      }
      
      pdf.setFontSize(14)
      pdf.text('Recommendations:', 20, yPos)
      yPos += 7
      pdf.setFontSize(10)
      
      results.recommendations.forEach(rec => {
        if (!rec.startsWith('📊')) {  // Skip summary we already showed
          const lines = pdf.splitTextToSize(`• ${rec}`, 170)
          
          // Check if we need a new page
          if (yPos + lines.length * 5 > 270) {
            pdf.addPage()
            yPos = 20
          }
          
          pdf.text(lines, 25, yPos)
          yPos += lines.length * 5 + 2
        }
      })
    }

    // Save the PDF
    const hostname = new URL(results.url).hostname.replace('www.', '')
    pdf.save(`${hostname}-llm-crawlability-report.pdf`)
  }

  const checkCrawlability = async () => {
    if (!url) {
      setError('Please enter a URL')
      return
    }

    // Ensure URL has protocol
    let checkUrl = url
    if (!url.startsWith('http://') && !url.startsWith('https://')) {
      checkUrl = 'https://' + url
    }

    setLoading(true)
    setError('')
    setResults(null)

    try {
      const response = await fetch('http://localhost:8000/api/llm-crawlability', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          url: checkUrl,
          check_content: false,
          check_performance: false,
          run_advanced: runAdvanced
        })
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }

      const data = await response.json()
      setResults(data)
    } catch (err: any) {
      setError(`Failed to analyze URL: ${err.message}`)
    } finally {
      setLoading(false)
    }
  }

  const getGradeColor = (grade: string) => {
    if (grade === 'A+' || grade === 'A') return 'text-green-600 bg-green-100'
    if (grade === 'B') return 'text-blue-600 bg-blue-100'
    if (grade === 'C') return 'text-yellow-600 bg-yellow-100'
    if (grade === 'D') return 'text-orange-600 bg-orange-100'
    return 'text-red-600 bg-red-100'
  }

  const getScoreColor = (score: number) => {
    if (score >= 90) return 'bg-green-500'
    if (score >= 80) return 'bg-blue-500'
    if (score >= 70) return 'bg-yellow-500'
    if (score >= 60) return 'bg-orange-500'
    return 'bg-red-500'
  }

  const getSeverityColor = (severity: string) => {
    if (severity === 'critical') return 'text-red-700 bg-red-50 border-red-200'
    if (severity === 'high') return 'text-orange-700 bg-orange-50 border-orange-200'
    if (severity === 'medium') return 'text-yellow-700 bg-yellow-50 border-yellow-200'
    return 'text-blue-700 bg-blue-50 border-blue-200'
  }

  const getLLMProviderName = (key: string) => {
    const [provider, agent] = key.split('_')
    const providerNames: Record<string, string> = {
      openai: 'OpenAI',
      google: 'Google',
      anthropic: 'Anthropic',
      apple: 'Apple',
      amazon: 'Amazon',
      meta: 'Meta',
      microsoft: 'Microsoft',
      perplexity: 'Perplexity',
      you: 'You.com',
      common: 'Common Crawl'
    }
    
    // Special descriptions for specific agents
    const agentDescriptions: Record<string, string> = {
      'GPTBot': 'Training',
      'ChatGPT-User': 'Browsing',
      'OAI-SearchBot': 'Search Index',
      'ClaudeBot': 'Training/Index',
      'Claude-User': 'On-demand',
      'Claude-SearchBot': 'Search',
      'Google-Extended': 'Gemini Usage',
      'Applebot-Extended': 'AI Usage',
      'Amazonbot': 'Crawler',
      'CCBot': 'Common Crawl',
      'bingbot': 'Bing',
      'PerplexityBot': 'Search',
      'YouBot': 'Search',
      'FacebookBot': 'Crawler'
    }
    
    const desc = agentDescriptions[agent] || agent
    return `${providerNames[provider] || provider} - ${agent} (${desc})`
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-gray-900 mb-2">LLM Crawlability Checker</h2>
        <p className="text-gray-600">
          Analyze how accessible your website is to AI language models and get recommendations for optimization.
        </p>
      </div>

      {/* URL Input */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Website URL
            </label>
            <div className="flex space-x-3">
              <input
                type="text"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="example.com or https://example.com"
                className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
              />
              {brandName && (
                <button
                  onClick={() => setUrl(brandName.toLowerCase().replace(/\s+/g, '') + '.com')}
                  className="px-4 py-2 text-sm bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200"
                >
                  Use {brandName}
                </button>
              )}
              <button
                onClick={checkCrawlability}
                disabled={loading}
                className="px-6 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 disabled:bg-gray-400"
              >
                {loading ? 'Analyzing...' : 'Analyze'}
              </button>
            </div>
          </div>

          <div className="mt-3 flex items-center">
            <input
              type="checkbox"
              id="runAdvanced"
              checked={runAdvanced}
              onChange={(e) => setRunAdvanced(e.target.checked)}
              className="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded"
            />
            <label htmlFor="runAdvanced" className="ml-2 text-sm text-gray-700">
              Run advanced checks (CDN/WAF, JavaScript content, meta tags, llms.txt)
            </label>
          </div>

          {error && (
            <div className="text-red-600 text-sm mt-3">{error}</div>
          )}
        </div>
      </div>

      {/* Results */}
      {results && (
        <div className="space-y-6">
          {/* Score Card */}
          <div className="bg-white rounded-lg shadow p-6">
            <div className="grid grid-cols-3 gap-6">
              {/* Overall Score */}
              <div className="text-center">
                <div className="text-sm text-gray-500 mb-2">Overall Score</div>
                <div className="relative">
                  <div className="w-32 h-32 mx-auto">
                    <svg className="w-32 h-32 transform -rotate-90">
                      <circle
                        cx="64"
                        cy="64"
                        r="56"
                        stroke="#e5e7eb"
                        strokeWidth="12"
                        fill="none"
                      />
                      <circle
                        cx="64"
                        cy="64"
                        r="56"
                        stroke="currentColor"
                        strokeWidth="12"
                        fill="none"
                        strokeDasharray={`${(results.overall_score / 100) * 352} 352`}
                        className={getScoreColor(results.overall_score)}
                      />
                    </svg>
                    <div className="absolute inset-0 flex items-center justify-center">
                      <div className="text-3xl font-bold">{results.overall_score}</div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Grade */}
              <div className="text-center">
                <div className="text-sm text-gray-500 mb-2">Grade</div>
                <div className={`text-6xl font-bold mt-8 inline-block px-6 py-3 rounded-lg ${getGradeColor(results.grade)}`}>
                  {results.grade}
                </div>
              </div>

              {/* URL Info */}
              <div>
                <div className="text-sm text-gray-500 mb-2">Analyzed URL</div>
                <div className="font-medium text-gray-900 break-all">{results.url}</div>
                <div className="text-xs text-gray-500 mt-2">
                  {new Date(results.timestamp).toLocaleString()}
                </div>
                <div className="mt-4 space-y-2">
                  <button
                    onClick={generatePDFReport}
                    className="w-full inline-flex items-center justify-center px-3 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
                  >
                    <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                    Download PDF Report
                  </button>
                  {results.corrected_robots && (
                    <button
                      onClick={() => {
                        const blob = new Blob([results.corrected_robots || ''], { type: 'text/plain' })
                        const url = window.URL.createObjectURL(blob)
                        const a = document.createElement('a')
                        a.href = url
                        a.download = 'robots.txt'
                        document.body.appendChild(a)
                        a.click()
                        document.body.removeChild(a)
                        window.URL.revokeObjectURL(url)
                      }}
                      className="w-full inline-flex items-center justify-center px-3 py-2 border border-indigo-300 rounded-md text-sm font-medium text-indigo-700 bg-indigo-50 hover:bg-indigo-100"
                    >
                      <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                      </svg>
                      Download Corrected Robots.txt
                    </button>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* Critical Issues */}
          {results.critical_issues.length > 0 && (
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-lg font-semibold mb-4">Critical Issues</h3>
              <div className="space-y-3">
                {results.critical_issues.map((issue, index) => (
                  <div key={index} className={`border rounded-lg p-4 ${getSeverityColor(issue.severity)}`}>
                    <div className="flex items-start">
                      <div className="flex-shrink-0">
                        {issue.severity === 'critical' && (
                          <svg className="w-5 h-5 text-red-600" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                          </svg>
                        )}
                        {issue.severity === 'high' && (
                          <svg className="w-5 h-5 text-orange-600" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                          </svg>
                        )}
                        {issue.severity === 'medium' && (
                          <svg className="w-5 h-5 text-yellow-600" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                          </svg>
                        )}
                      </div>
                      <div className="ml-3 flex-1">
                        <div className="font-medium">{issue.message}</div>
                        <div className="text-sm mt-1">
                          <strong>Solution:</strong> {issue.solution}
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Robots.txt Analysis */}
          {results.robots_analysis && (
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-lg font-semibold mb-4">Robots.txt Analysis</h3>
              
              {/* LLM Access Status - Split into Explicit vs Wildcard */}
              <div className="mb-6">
                {/* Explicit LLM Rules */}
                {results.robots_analysis.explicit_llm_agents && results.robots_analysis.explicit_llm_agents.length > 0 && (
                  <div className="mb-4">
                    <h4 className="text-sm font-medium text-gray-700 mb-2">Explicitly Configured LLM Agents</h4>
                    <div className="flex flex-wrap gap-2">
                      {results.robots_analysis.explicit_llm_agents.map((agent) => (
                        <span key={agent} className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
                          ✓ {agent}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
                
                {/* Wildcard Allowed Agents */}
                {results.robots_analysis.wildcard_allowed_agents && results.robots_analysis.wildcard_allowed_agents.length > 0 && (
                  <div className="mb-4">
                    <h4 className="text-sm font-medium text-gray-700 mb-2">Allowed via Wildcard (*)</h4>
                    <div className="flex flex-wrap gap-2">
                      {results.robots_analysis.wildcard_allowed_agents.map((agent) => (
                        <span key={agent} className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                          ✓ {agent}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
                
                {/* Legacy grid view for blocked agents */}
                <h4 className="text-sm font-medium text-gray-700 mb-3">Overall Access Status</h4>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                  {Object.entries(results.robots_analysis.llm_access).map(([agent, allowed]) => (
                    <div key={agent} className="flex items-center space-x-2">
                      {allowed ? (
                        <svg className="w-5 h-5 text-green-500" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                        </svg>
                      ) : (
                        <svg className="w-5 h-5 text-red-500" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                        </svg>
                      )}
                      <span className="text-sm text-gray-700">{getLLMProviderName(agent)}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Additional Info */}
              <div className="grid grid-cols-2 gap-6">
                <div>
                  <h4 className="text-sm font-medium text-gray-700 mb-2">Configuration</h4>
                  <dl className="space-y-1">
                    <div className="flex justify-between text-sm">
                      <dt className="text-gray-500">LLM-specific rules:</dt>
                      <dd className="font-medium">{results.robots_analysis.has_llm_rules ? 'Yes' : 'No'}</dd>
                    </div>
                    <div className="flex justify-between text-sm">
                      <dt className="text-gray-500">Sitemap declared:</dt>
                      <dd className="font-medium">{results.robots_analysis.sitemap_url ? 'Yes' : 'No'}</dd>
                    </div>
                    <div className="flex justify-between text-sm">
                      <dt className="text-gray-500">Crawl delay:</dt>
                      <dd className="font-medium">{results.robots_analysis.crawl_delay || 'None'}</dd>
                    </div>
                  </dl>
                </div>

                <div>
                  <h4 className="text-sm font-medium text-gray-700 mb-2">Blocked Paths</h4>
                  {results.robots_analysis.critical_paths_blocked.length > 0 ? (
                    <ul className="text-sm text-red-600 space-y-1">
                      {results.robots_analysis.critical_paths_blocked.map((path, i) => (
                        <li key={i}>{path}</li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-sm text-green-600">All critical paths accessible</p>
                  )}
                </div>
              </div>

              {/* Warnings */}
              {results.robots_analysis.warnings.length > 0 && (
                <div className="mt-4 p-3 bg-yellow-50 rounded-lg">
                  <h4 className="text-sm font-medium text-yellow-800 mb-2">Warnings</h4>
                  <ul className="text-sm text-yellow-700 space-y-1">
                    {results.robots_analysis.warnings.map((warning, i) => (
                      <li key={i}>• {warning}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}

          {/* Advanced Checks Results */}
          {results.advanced_checks && !results.advanced_checks.error && (
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-lg font-semibold mb-4">Advanced Checks</h3>
              
              <div className="grid grid-cols-2 gap-6">
                {/* CDN/WAF Detection */}
                {results.advanced_checks.cdn_waf && (
                  <div>
                    <h4 className="text-sm font-medium text-gray-700 mb-2">CDN/WAF Detection</h4>
                    <dl className="space-y-1">
                      <div className="flex justify-between text-sm">
                        <dt className="text-gray-500">CDN Provider:</dt>
                        <dd className="font-medium">{results.advanced_checks.cdn_waf.cdn_provider || 'None detected'}</dd>
                      </div>
                      <div className="flex justify-between text-sm">
                        <dt className="text-gray-500">WAF Detected:</dt>
                        <dd className="font-medium">{results.advanced_checks.cdn_waf.waf_detected ? 'Yes' : 'No'}</dd>
                      </div>
                    </dl>
                  </div>
                )}
                
                {/* No-JS Content */}
                {results.advanced_checks.no_js_content && (
                  <div>
                    <h4 className="text-sm font-medium text-gray-700 mb-2">JavaScript-Free Content</h4>
                    <dl className="space-y-1">
                      <div className="flex justify-between text-sm">
                        <dt className="text-gray-500">Content Accessible:</dt>
                        <dd className="font-medium">{results.advanced_checks.no_js_content.content_accessible ? 'Yes' : 'No'}</dd>
                      </div>
                      <div className="flex justify-between text-sm">
                        <dt className="text-gray-500">Word Count:</dt>
                        <dd className="font-medium">{results.advanced_checks.no_js_content.word_count || 0}</dd>
                      </div>
                      <div className="flex justify-between text-sm">
                        <dt className="text-gray-500">Structured Data:</dt>
                        <dd className="font-medium">{results.advanced_checks.no_js_content.has_structured_data ? 'Yes' : 'No'}</dd>
                      </div>
                    </dl>
                  </div>
                )}
                
                {/* Meta/Headers */}
                {results.advanced_checks.meta_headers && (
                  <div>
                    <h4 className="text-sm font-medium text-gray-700 mb-2">Meta Tags & Headers</h4>
                    <dl className="space-y-1">
                      {results.advanced_checks.meta_headers.has_noindex && (
                        <div className="text-sm text-red-600">⚠️ Has noindex directive</div>
                      )}
                      {results.advanced_checks.meta_headers.has_nofollow && (
                        <div className="text-sm text-orange-600">⚠️ Has nofollow directive</div>
                      )}
                      {results.advanced_checks.meta_headers.has_noai && (
                        <div className="text-sm text-yellow-600">⚠️ Has noai meta tag</div>
                      )}
                      {!results.advanced_checks.meta_headers.has_noindex && 
                       !results.advanced_checks.meta_headers.has_nofollow && (
                        <div className="text-sm text-green-600">✓ No blocking directives</div>
                      )}
                    </dl>
                  </div>
                )}
                
                {/* llms.txt */}
                {results.advanced_checks.llms_txt && (
                  <div>
                    <h4 className="text-sm font-medium text-gray-700 mb-2">llms.txt File</h4>
                    <dl className="space-y-1">
                      <div className="flex justify-between text-sm">
                        <dt className="text-gray-500">Exists:</dt>
                        <dd className="font-medium">{results.advanced_checks.llms_txt.exists ? 'Yes' : 'No'}</dd>
                      </div>
                      {results.advanced_checks.llms_txt.exists && (
                        <>
                          <div className="flex justify-between text-sm">
                            <dt className="text-gray-500">Size:</dt>
                            <dd className="font-medium">{results.advanced_checks.llms_txt.size} bytes</dd>
                          </div>
                          <div className="flex justify-between text-sm">
                            <dt className="text-gray-500">Links Found:</dt>
                            <dd className="font-medium">{results.advanced_checks.llms_txt.links?.length || 0}</dd>
                          </div>
                        </>
                      )}
                    </dl>
                  </div>
                )}
              </div>
              
              {/* User Agent Tests */}
              {results.advanced_checks.user_agent_tests && (
                <div className="mt-4">
                  <h4 className="text-sm font-medium text-gray-700 mb-2">User Agent Access Tests</h4>
                  <div className="grid grid-cols-4 gap-2">
                    {Object.entries(results.advanced_checks.user_agent_tests).map(([agent, data]: [string, any]) => (
                      <div key={agent} className="flex items-center space-x-1 text-sm">
                        {data.accessible ? (
                          <svg className="w-4 h-4 text-green-500" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                          </svg>
                        ) : data.blocked ? (
                          <svg className="w-4 h-4 text-red-500" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                          </svg>
                        ) : (
                          <svg className="w-4 h-4 text-yellow-500" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                          </svg>
                        )}
                        <span className={data.accessible ? 'text-green-700' : data.blocked ? 'text-red-700' : 'text-yellow-700'}>
                          {agent} ({data.status_code})
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Recommendations */}
          {results.recommendations.length > 0 && (
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-lg font-semibold mb-4">Recommendations</h3>
              <ul className="space-y-2">
                {results.recommendations.map((rec, index) => (
                  <li key={index} className="flex items-start">
                    <svg className="w-5 h-5 text-indigo-500 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-8.293l-3-3a1 1 0 00-1.414 1.414L10.586 9.5H7a1 1 0 100 2h3.586l-1.293 1.293a1 1 0 101.414 1.414l3-3a1 1 0 000-1.414z" clipRule="evenodd" />
                    </svg>
                    <span className="ml-2 text-gray-700">{rec}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Corrected Robots.txt */}
          {results.corrected_robots && (
            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold">
                  Corrected LLM-Optimized Robots.txt
                  <span className="ml-2 text-sm font-normal text-gray-500">(Based on your actual robots.txt)</span>
                </h3>
                <div className="flex space-x-3">
                  <button
                    onClick={() => {
                      // Download robots.txt
                      const blob = new Blob([results.corrected_robots || ''], { type: 'text/plain' })
                      const url = window.URL.createObjectURL(blob)
                      const a = document.createElement('a')
                      a.href = url
                      a.download = 'robots.txt'
                      document.body.appendChild(a)
                      a.click()
                      document.body.removeChild(a)
                      window.URL.revokeObjectURL(url)
                    }}
                    className="inline-flex items-center px-3 py-1 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
                  >
                    <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                    </svg>
                    Download
                  </button>
                  <button
                    onClick={() => setExampleRobots(!exampleRobots)}
                    className="text-sm text-indigo-600 hover:text-indigo-800"
                  >
                    {exampleRobots ? 'Hide' : 'Show'} Corrected Version
                  </button>
                </div>
              </div>
              
              {exampleRobots && (
                <div>
                  <div className="mb-3 p-3 bg-green-50 border border-green-200 rounded-lg">
                    <p className="text-sm text-green-800">
                      ✅ This corrected version includes all modern LLM crawlers while preserving your existing SEO rules.
                      Copy and replace your current robots.txt with this optimized version.
                    </p>
                  </div>
                  <pre className="bg-gray-50 p-4 rounded-lg overflow-x-auto text-sm">
{results.corrected_robots || `# OpenAI Crawlers
User-agent: GPTBot
Allow: /              # Model training

User-agent: ChatGPT-User
Allow: /              # User browsing

User-agent: OAI-SearchBot
Allow: /              # ChatGPT Search indexing

# Anthropic Crawlers  
User-agent: ClaudeBot
Allow: /              # Training/indexing

User-agent: Claude-User
Allow: /              # On-demand requests

User-agent: Claude-SearchBot
Allow: /              # Claude search

# Usage Controls (not crawlers)
User-agent: Google-Extended
Allow: /              # Gemini usage

User-agent: Applebot-Extended
Allow: /              # Apple AI usage

# Other AI Crawlers
User-agent: Amazonbot
Allow: /

User-agent: CCBot
Allow: /              # Common Crawl

User-agent: PerplexityBot
Allow: /

# Traditional crawlers - SEO rules
User-agent: *
Disallow: /api/
Disallow: /admin/
Disallow: /cart
Disallow: /checkout
Disallow: /search
Allow: /policies/
Allow: /terms/

# Sitemap
Sitemap: https://example.com/sitemap.xml`}
                  </pre>
                </div>
              )}
            </div>
          )}

          {/* Advanced Checks Results */}
          {results.advanced_checks && (
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-lg font-semibold mb-4">Advanced Crawlability Checks</h3>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* JavaScript Content Check */}
                {results.advanced_checks.no_js_content && (
                  <div className="border rounded-lg p-4">
                    <h4 className="font-medium text-gray-900 mb-3 flex items-center">
                      <svg className="w-5 h-5 mr-2 text-yellow-500" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M12.316 3.051a1 1 0 01.633 1.265l-4 12a1 1 0 11-1.898-.632l4-12a1 1 0 011.265-.633zM5.707 6.293a1 1 0 010 1.414L3.414 10l2.293 2.293a1 1 0 11-1.414 1.414l-3-3a1 1 0 010-1.414l3-3a1 1 0 011.414 0zm8.586 0a1 1 0 011.414 0l3 3a1 1 0 010 1.414l-3 3a1 1 0 11-1.414-1.414L16.586 10l-2.293-2.293a1 1 0 010-1.414z" clipRule="evenodd" />
                      </svg>
                      JavaScript Content Accessibility
                    </h4>
                    <div className="space-y-2 text-sm">
                      <div className="flex justify-between">
                        <span className="text-gray-500">Content without JS:</span>
                        <span className={`font-medium ${results.advanced_checks.no_js_content.content_accessible ? 'text-green-600' : 'text-red-600'}`}>
                          {results.advanced_checks.no_js_content.content_accessible ? '✅ Accessible' : '❌ Requires JS'}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-500">Word count:</span>
                        <span className="font-medium">{results.advanced_checks.no_js_content.word_count || 0} words</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-500">H1 heading:</span>
                        <span className={`font-medium ${results.advanced_checks.no_js_content.has_main_heading ? 'text-green-600' : 'text-orange-600'}`}>
                          {results.advanced_checks.no_js_content.has_main_heading ? '✅ Present' : '⚠️ Missing'}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-500">Structured data:</span>
                        <span className={`font-medium ${results.advanced_checks.no_js_content.has_structured_data ? 'text-green-600' : 'text-gray-400'}`}>
                          {results.advanced_checks.no_js_content.has_structured_data ? '✅ JSON-LD found' : '- Not found'}
                        </span>
                      </div>
                      {results.advanced_checks.no_js_content.spa_detected && (
                        <div className="mt-2 p-2 bg-yellow-50 rounded text-xs text-yellow-800">
                          ⚠️ Single Page App detected - Consider SSR/SSG for better crawlability
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* CDN/WAF Detection */}
                {results.advanced_checks.cdn_waf && (
                  <div className="border rounded-lg p-4">
                    <h4 className="font-medium text-gray-900 mb-3 flex items-center">
                      <svg className="w-5 h-5 mr-2 text-blue-500" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M2.166 4.999A11.954 11.954 0 0010 1.944 11.954 11.954 0 0017.834 5c.11.65.166 1.32.166 2.001 0 5.225-3.34 9.67-8 11.317C5.34 16.67 2 12.225 2 7c0-.682.057-1.35.166-2.001zm11.541 3.708a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                      </svg>
                      CDN/WAF Protection
                    </h4>
                    <div className="space-y-2 text-sm">
                      <div className="flex justify-between">
                        <span className="text-gray-500">CDN Provider:</span>
                        <span className="font-medium">{results.advanced_checks.cdn_waf.cdn_provider || 'None detected'}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-500">WAF Detected:</span>
                        <span className={`font-medium ${results.advanced_checks.cdn_waf.waf_detected ? 'text-blue-600' : 'text-green-600'}`}>
                          {results.advanced_checks.cdn_waf.waf_detected ? 'ℹ️ Yes' : '✅ No'}
                        </span>
                      </div>
                      {results.advanced_checks.cdn_waf.platform && (
                        <div className="flex justify-between">
                          <span className="text-gray-500">Platform:</span>
                          <span className="font-medium">{results.advanced_checks.cdn_waf.platform}</span>
                        </div>
                      )}
                      {results.advanced_checks.cdn_waf.cloudflare && (
                        <div className="mt-2 p-2 bg-blue-50 rounded text-xs text-blue-800">
                          {results.advanced_checks.cdn_waf.platform === 'Shopify' 
                            ? '✅ Shopify manages Cloudflare - typically works well with LLMs'
                            : 'ℹ️ Cloudflare detected - Check if LLMs are actually blocked below'}
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* Meta Tags & Headers */}
                {results.advanced_checks.meta_headers && (
                  <div className="border rounded-lg p-4">
                    <h4 className="font-medium text-gray-900 mb-3 flex items-center">
                      <svg className="w-5 h-5 mr-2 text-purple-500" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M7 2a1 1 0 00-.707 1.707L7 4.414v3.758a1 1 0 01-.293.707l-4 4C.817 14.769 2.156 18 4.828 18h10.343c2.673 0 4.012-3.231 2.122-5.121l-4-4A1 1 0 0113 8.172V4.414l.707-.707A1 1 0 0013 2H7zm2 6.172V4h2v4.172a3 3 0 00.879 2.12l1.027 1.028a4 4 0 00-2.171.102l-.47.156a4 4 0 01-2.53 0l-.563-.187a1.993 1.993 0 00-.114-.035l1.063-1.063A3 3 0 009 8.172z" clipRule="evenodd" />
                      </svg>
                      Meta Tags & Headers
                    </h4>
                    <div className="space-y-2 text-sm">
                      <div className="flex justify-between">
                        <span className="text-gray-500">noindex:</span>
                        <span className={`font-medium ${results.advanced_checks.meta_headers.has_noindex ? 'text-red-600' : 'text-green-600'}`}>
                          {results.advanced_checks.meta_headers.has_noindex ? '❌ Blocking crawlers' : '✅ Not set'}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-500">nofollow:</span>
                        <span className={`font-medium ${results.advanced_checks.meta_headers.has_nofollow ? 'text-orange-600' : 'text-green-600'}`}>
                          {results.advanced_checks.meta_headers.has_nofollow ? '⚠️ Links not followed' : '✅ Not set'}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-500">noai tag:</span>
                        <span className={`font-medium ${results.advanced_checks.meta_headers.has_noai ? 'text-red-600' : 'text-green-600'}`}>
                          {results.advanced_checks.meta_headers.has_noai ? '❌ AI blocked' : '✅ Not set'}
                        </span>
                      </div>
                      {results.advanced_checks.meta_headers.robots_meta_content && (
                        <div className="mt-2 p-2 bg-gray-50 rounded text-xs">
                          Meta robots: {results.advanced_checks.meta_headers.robots_meta_content}
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* llms.txt Check */}
                {results.advanced_checks.llms_txt && (
                  <div className="border rounded-lg p-4">
                    <h4 className="font-medium text-gray-900 mb-3 flex items-center">
                      <svg className="w-5 h-5 mr-2 text-indigo-500" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clipRule="evenodd" />
                      </svg>
                      llms.txt File
                    </h4>
                    <div className="space-y-2 text-sm">
                      <div className="flex justify-between">
                        <span className="text-gray-500">File exists:</span>
                        <span className={`font-medium ${results.advanced_checks.llms_txt.exists ? 'text-green-600' : 'text-gray-400'}`}>
                          {results.advanced_checks.llms_txt.exists ? '✅ Yes' : '- No'}
                        </span>
                      </div>
                      {results.advanced_checks.llms_txt.exists && (
                        <>
                          <div className="flex justify-between">
                            <span className="text-gray-500">File size:</span>
                            <span className="font-medium">{results.advanced_checks.llms_txt.size} bytes</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-gray-500">Links found:</span>
                            <span className="font-medium">{results.advanced_checks.llms_txt.links?.length || 0}</span>
                          </div>
                        </>
                      )}
                      {!results.advanced_checks.llms_txt.exists && (
                        <div className="mt-2 p-2 bg-blue-50 rounded text-xs text-blue-800">
                          💡 Consider adding /llms.txt for LLM-specific instructions
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>

              {/* User Agent Tests */}
              {results.advanced_checks.user_agent_tests && Object.keys(results.advanced_checks.user_agent_tests).length > 0 && (
                <div className="mt-6">
                  <h4 className="font-medium text-gray-900 mb-3">User Agent Access Tests</h4>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                    {Object.entries(results.advanced_checks.user_agent_tests).map(([agent, test]: [string, any]) => (
                      <div key={agent} className="flex items-center space-x-2 text-sm">
                        {test.accessible ? (
                          <svg className="w-4 h-4 text-green-500" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                          </svg>
                        ) : test.blocked ? (
                          <svg className="w-4 h-4 text-red-500" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                          </svg>
                        ) : (
                          <svg className="w-4 h-4 text-yellow-500" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                          </svg>
                        )}
                        <span className="text-gray-700">{agent} ({test.status_code || 'N/A'})</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}