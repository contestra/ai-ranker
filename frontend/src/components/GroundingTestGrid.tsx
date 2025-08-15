'use client';

import React, { useState } from 'react';
import { CheckCircleIcon, XCircleIcon, ExclamationCircleIcon } from '@heroicons/react/24/outline';
import { PlayIcon } from '@heroicons/react/24/solid';

interface TestResult {
  provider: 'openai' | 'vertex';
  model: string;
  grounded: boolean;
  status: 'pending' | 'running' | 'success' | 'failed';
  grounded_effective?: boolean;
  tool_call_count?: number;
  json_valid?: boolean;
  json_obj?: any;
  latency_ms?: number;
  error?: string;
}

export default function GroundingTestGrid() {
  const [testResults, setTestResults] = useState<TestResult[]>([
    { provider: 'openai', model: 'gpt-5', grounded: false, status: 'pending' },
    { provider: 'openai', model: 'gpt-5', grounded: true, status: 'pending' },
    { provider: 'vertex', model: 'gemini-2.5-pro', grounded: false, status: 'pending' },
    { provider: 'vertex', model: 'gemini-2.5-pro', grounded: true, status: 'pending' },
  ]);
  const [isRunning, setIsRunning] = useState(false);

  const runTest = async (index: number) => {
    const test = testResults[index];
    
    // Update status to running
    setTestResults(prev => {
      const updated = [...prev];
      updated[index] = { ...updated[index], status: 'running' };
      return updated;
    });

    try {
      const response = await fetch('/api/test-grounding', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          provider: test.provider,
          model: test.model,
          grounded: test.grounded,
        }),
      });

      const data = await response.json();
      
      setTestResults(prev => {
        const updated = [...prev];
        updated[index] = {
          ...updated[index],
          status: data.error ? 'failed' : 'success',
          grounded_effective: data.grounded_effective,
          tool_call_count: data.tool_call_count,
          json_valid: data.json_valid,
          json_obj: data.json_obj,
          latency_ms: data.latency_ms,
          error: data.error,
        };
        return updated;
      });
    } catch (error) {
      setTestResults(prev => {
        const updated = [...prev];
        updated[index] = {
          ...updated[index],
          status: 'failed',
          error: error instanceof Error ? error.message : 'Unknown error',
        };
        return updated;
      });
    }
  };

  const runAllTests = async () => {
    setIsRunning(true);
    
    // Reset all tests to pending
    setTestResults(prev => prev.map(test => ({ ...test, status: 'pending' })));
    
    // Run tests sequentially to avoid overwhelming the API
    for (let i = 0; i < testResults.length; i++) {
      await runTest(i);
    }
    
    setIsRunning(false);
  };

  const getStatusIcon = (test: TestResult) => {
    if (test.status === 'running') {
      return (
        <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-indigo-500"></div>
      );
    }
    
    if (test.status === 'success') {
      // For grounded tests, check if grounding actually happened
      if (test.grounded && !test.grounded_effective) {
        return <ExclamationCircleIcon className="h-5 w-5 text-yellow-500" />;
      }
      return <CheckCircleIcon className="h-5 w-5 text-green-500" />;
    }
    
    if (test.status === 'failed') {
      return <XCircleIcon className="h-5 w-5 text-red-500" />;
    }
    
    return <div className="h-5 w-5 rounded-full bg-gray-200"></div>;
  };

  const getStatusColor = (test: TestResult) => {
    if (test.status === 'running') return 'bg-blue-50 border-blue-200';
    if (test.status === 'success') {
      if (test.grounded && !test.grounded_effective) {
        return 'bg-yellow-50 border-yellow-200';
      }
      return 'bg-green-50 border-green-200';
    }
    if (test.status === 'failed') return 'bg-red-50 border-red-200';
    return 'bg-gray-50 border-gray-200';
  };

  return (
    <div className="space-y-6">
      {/* Header with Run Button */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-xl font-semibold text-gray-900">Grounding Test Grid</h2>
          <p className="text-sm text-gray-500 mt-1">
            Test web search grounding across GPT-5 and Gemini 2.5 Pro
          </p>
        </div>
        <button
          onClick={runAllTests}
          disabled={isRunning}
          className={`inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white ${
            isRunning
              ? 'bg-gray-400 cursor-not-allowed'
              : 'bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500'
          }`}
        >
          {isRunning ? (
            <>
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
              Running Tests...
            </>
          ) : (
            <>
              <PlayIcon className="h-4 w-4 mr-2" />
              Run All Tests
            </>
          )}
        </button>
      </div>

      {/* Test Grid */}
      <div className="grid grid-cols-2 gap-6">
        {/* GPT-5 Column */}
        <div className="space-y-4">
          <h3 className="text-lg font-medium text-gray-900">GPT-5</h3>
          
          {/* Ungrounded Test */}
          <div className={`border rounded-lg p-4 ${getStatusColor(testResults[0])}`}>
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <h4 className="font-medium text-gray-900">Ungrounded</h4>
                  {getStatusIcon(testResults[0])}
                </div>
                <p className="text-xs text-gray-500 mt-1">No web search</p>
              </div>
            </div>
            
            {testResults[0].status === 'success' && (
              <div className="mt-3 space-y-1 text-xs">
                <div className="flex justify-between">
                  <span className="text-gray-500">Grounded:</span>
                  <span className={testResults[0].grounded_effective ? 'text-red-500' : 'text-green-500'}>
                    {testResults[0].grounded_effective ? 'Yes (unexpected)' : 'No (expected)'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Tool calls:</span>
                  <span>{testResults[0].tool_call_count || 0}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">JSON valid:</span>
                  <span className={testResults[0].json_valid ? 'text-green-500' : 'text-red-500'}>
                    {testResults[0].json_valid ? 'Yes' : 'No'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Latency:</span>
                  <span>{testResults[0].latency_ms}ms</span>
                </div>
              </div>
            )}
            
            {testResults[0].error && (
              <div className="mt-2 text-xs text-red-600">
                Error: {testResults[0].error}
              </div>
            )}
          </div>

          {/* Grounded Test */}
          <div className={`border rounded-lg p-4 ${getStatusColor(testResults[1])}`}>
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <h4 className="font-medium text-gray-900">Grounded</h4>
                  {getStatusIcon(testResults[1])}
                </div>
                <p className="text-xs text-gray-500 mt-1">With web search</p>
              </div>
            </div>
            
            {testResults[1].status === 'success' && (
              <div className="mt-3 space-y-1 text-xs">
                <div className="flex justify-between">
                  <span className="text-gray-500">Grounded:</span>
                  <span className={testResults[1].grounded_effective ? 'text-green-500' : 'text-red-500'}>
                    {testResults[1].grounded_effective ? 'Yes (expected)' : 'No (failed)'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Web searches:</span>
                  <span className={testResults[1].tool_call_count ? 'text-green-500' : 'text-red-500'}>
                    {testResults[1].tool_call_count || 0}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">JSON valid:</span>
                  <span className={testResults[1].json_valid ? 'text-green-500' : 'text-red-500'}>
                    {testResults[1].json_valid ? 'Yes' : 'No'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Latency:</span>
                  <span>{testResults[1].latency_ms}ms</span>
                </div>
              </div>
            )}
            
            {testResults[1].error && (
              <div className="mt-2 text-xs text-red-600">
                Error: {testResults[1].error}
              </div>
            )}
          </div>
        </div>

        {/* Gemini Column */}
        <div className="space-y-4">
          <h3 className="text-lg font-medium text-gray-900">Gemini 2.5 Pro</h3>
          
          {/* Ungrounded Test */}
          <div className={`border rounded-lg p-4 ${getStatusColor(testResults[2])}`}>
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <h4 className="font-medium text-gray-900">Ungrounded</h4>
                  {getStatusIcon(testResults[2])}
                </div>
                <p className="text-xs text-gray-500 mt-1">No web search</p>
              </div>
            </div>
            
            {testResults[2].status === 'success' && (
              <div className="mt-3 space-y-1 text-xs">
                <div className="flex justify-between">
                  <span className="text-gray-500">Grounded:</span>
                  <span className={testResults[2].grounded_effective ? 'text-red-500' : 'text-green-500'}>
                    {testResults[2].grounded_effective ? 'Yes (unexpected)' : 'No (expected)'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Tool calls:</span>
                  <span>{testResults[2].tool_call_count || 0}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">JSON valid:</span>
                  <span className={testResults[2].json_valid ? 'text-green-500' : 'text-red-500'}>
                    {testResults[2].json_valid ? 'Yes' : 'No'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Latency:</span>
                  <span>{testResults[2].latency_ms}ms</span>
                </div>
              </div>
            )}
            
            {testResults[2].error && (
              <div className="mt-2 text-xs text-red-600">
                Error: {testResults[2].error}
              </div>
            )}
          </div>

          {/* Grounded Test */}
          <div className={`border rounded-lg p-4 ${getStatusColor(testResults[3])}`}>
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <h4 className="font-medium text-gray-900">Grounded</h4>
                  {getStatusIcon(testResults[3])}
                </div>
                <p className="text-xs text-gray-500 mt-1">With web search</p>
              </div>
            </div>
            
            {testResults[3].status === 'success' && (
              <div className="mt-3 space-y-1 text-xs">
                <div className="flex justify-between">
                  <span className="text-gray-500">Grounded:</span>
                  <span className={testResults[3].grounded_effective ? 'text-green-500' : 'text-red-500'}>
                    {testResults[3].grounded_effective ? 'Yes (expected)' : 'No (failed)'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Web searches:</span>
                  <span className={testResults[3].tool_call_count ? 'text-green-500' : 'text-red-500'}>
                    {testResults[3].tool_call_count || 0}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">JSON valid:</span>
                  <span className={testResults[3].json_valid ? 'text-green-500' : 'text-red-500'}>
                    {testResults[3].json_valid ? 'Yes' : 'No'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Latency:</span>
                  <span>{testResults[3].latency_ms}ms</span>
                </div>
              </div>
            )}
            
            {testResults[3].error && (
              <div className="mt-2 text-xs text-red-600">
                Error: {testResults[3].error}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Summary */}
      <div className="mt-6 p-4 bg-gray-50 rounded-lg">
        <h3 className="text-sm font-medium text-gray-900 mb-2">Test Summary</h3>
        <div className="grid grid-cols-4 gap-4 text-xs">
          <div>
            <span className="text-gray-500">Total Tests:</span>
            <span className="ml-1 font-medium">{testResults.length}</span>
          </div>
          <div>
            <span className="text-gray-500">Passed:</span>
            <span className="ml-1 font-medium text-green-600">
              {testResults.filter(t => t.status === 'success').length}
            </span>
          </div>
          <div>
            <span className="text-gray-500">Failed:</span>
            <span className="ml-1 font-medium text-red-600">
              {testResults.filter(t => t.status === 'failed').length}
            </span>
          </div>
          <div>
            <span className="text-gray-500">Pending:</span>
            <span className="ml-1 font-medium text-gray-600">
              {testResults.filter(t => t.status === 'pending').length}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}