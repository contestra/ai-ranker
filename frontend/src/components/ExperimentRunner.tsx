'use client'

import { useState } from 'react'
import { experimentsApi, promptsApi } from '@/lib/api'

interface ExperimentRunnerProps {
  brandId: number
  brandName?: string
}

const modelOptions: Record<string, { name: string; model: string }[]> = {
  openai: [
    { name: 'GPT-5', model: 'gpt-5' },
    { name: 'GPT-4 Turbo', model: 'gpt-4-turbo' }
  ],
  google: [
    { name: 'Gemini 1.5 Flash', model: 'gemini-1.5-flash' },
    { name: 'Gemini 1.5 Pro', model: 'gemini-1.5-pro' }
  ],
  anthropic: [
    { name: 'Claude 3.5 Sonnet', model: 'claude-3-5-sonnet-20241022' },
    { name: 'Claude 3 Opus', model: 'claude-3-opus' }
  ]
}

export default function ExperimentRunner({ brandId, brandName }: ExperimentRunnerProps) {
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [modelVendor, setModelVendor] = useState('openai')
  const [modelName, setModelName] = useState('gpt-5')
  const [categories, setCategories] = useState('')
  const [repetitions, setRepetitions] = useState(3)
  const [grounded, setGrounded] = useState(false)
  const [running, setRunning] = useState(false)
  const [status, setStatus] = useState<string | null>(null)

  const handleRun = async () => {
    setRunning(true)
    setStatus('Creating experiment...')
    
    try {
      const experiment = await experimentsApi.create({ title, description })
      
      setStatus('Generating prompts...')
      const categoryList = categories.split(',').map(c => c.trim()).filter(c => c)
      const { prompts } = await promptsApi.generate(brandName || `Brand${brandId}`, categoryList)
      
      setStatus('Running experiment...')
      const result = await experimentsApi.run({
        experiment_id: experiment.id,
        model_vendor: modelVendor,
        model_name: modelName,
        prompts,
        repetitions,
        temperature: 0.1,
        grounded,
        seed: Date.now()
      })
      
      setStatus(`Experiment completed! Run ID: ${result.run_id}`)
    } catch (error) {
      console.error('Experiment failed:', error)
      setStatus('Experiment failed. Please check console for details.')
    } finally {
      setRunning(false)
    }
  }

  return (
    <div className="bg-white p-6 rounded-lg shadow">
      <h2 className="text-xl font-semibold mb-4">Run New Experiment</h2>
      
      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700">Title</label>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
            placeholder="Experiment title"
          />
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-700">Description</label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
            rows={3}
            placeholder="Optional description"
          />
        </div>
        
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700">Model Vendor</label>
            <select
              value={modelVendor}
              onChange={(e) => {
                setModelVendor(e.target.value)
                setModelName(modelOptions[e.target.value][0].model)
              }}
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
            >
              <option value="openai">OpenAI</option>
              <option value="google">Google</option>
              <option value="anthropic">Anthropic</option>
            </select>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700">Model Name</label>
            <select
              value={modelName}
              onChange={(e) => setModelName(e.target.value)}
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
            >
              {modelOptions[modelVendor].map(option => (
                <option key={option.model} value={option.model}>
                  {option.name}
                </option>
              ))}
            </select>
          </div>
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-700">Categories (comma-separated)</label>
          <input
            type="text"
            value={categories}
            onChange={(e) => setCategories(e.target.value)}
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
            placeholder="e.g., insurance, health tech, financial services"
          />
        </div>
        
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700">Repetitions</label>
            <input
              type="number"
              value={repetitions}
              onChange={(e) => setRepetitions(parseInt(e.target.value))}
              min="1"
              max="10"
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
            />
          </div>
          
          <div className="flex items-center mt-6">
            <input
              type="checkbox"
              checked={grounded}
              onChange={(e) => setGrounded(e.target.checked)}
              className="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded"
            />
            <label className="ml-2 block text-sm text-gray-900">
              Grounded Mode
            </label>
          </div>
        </div>
        
        <div className="pt-4">
          <button
            onClick={handleRun}
            disabled={running || !title}
            className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50"
          >
            {running ? 'Running...' : 'Run Experiment'}
          </button>
        </div>
        
        {status && (
          <div className="mt-4 p-4 bg-gray-50 rounded-md">
            <p className="text-sm text-gray-700">{status}</p>
          </div>
        )}
      </div>
    </div>
  )
}