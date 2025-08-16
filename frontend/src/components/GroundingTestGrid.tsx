'use client';

import React, { useState } from 'react';
import { CheckCircleIcon, XCircleIcon, ExclamationCircleIcon } from '@heroicons/react/24/outline';
import { PlayIcon } from '@heroicons/react/24/solid';

type GroundingMode = 'off' | 'preferred' | 'required';

interface TestResult {
  provider: 'openai' | 'vertex';
  model: string;
  grounding_mode: GroundingMode;
  status: 'pending' | 'running' | 'success' | 'failed';
  grounded_effective?: boolean;
  tool_call_count?: number;
  enforcement_passed?: boolean;
  json_valid?: boolean;
  json_obj?: any;
  latency_ms?: number;
  error?: string;
}

export default function GroundingTestGrid() {
  const [testResults, setTestResults] = useState<TestResult[]>([
    // GPT-5 tests
    { provider: 'openai', model: 'gpt-5', grounding_mode: 'off', status: 'pending' },
    { provider: 'openai', model: 'gpt-5', grounding_mode: 'preferred', status: 'pending' },
    { provider: 'openai', model: 'gpt-5', grounding_mode: 'required', status: 'pending' },
    // Gemini tests
    { provider: 'vertex', model: 'gemini-2.5-pro', grounding_mode: 'off', status: 'pending' },
    { provider: 'vertex', model: 'gemini-2.5-pro', grounding_mode: 'preferred', status: 'pending' },
    { provider: 'vertex', model: 'gemini-2.5-pro', grounding_mode: 'required', status: 'pending' },
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
      // Use US as test country for clearer VAT testing (no federal VAT)
      const usALS = 'Ambient Context (localization only; do not cite):\n- 08/16/2025 10:07, UTC-07:00\n- state DMV — "passport application"\n- New York, NY 10001 • (212) xxx-xxxx • $12.90\n- state sales tax — general info';
      
      const response = await fetch('http://localhost:8000/api/grounding-test/run-locale-test', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          provider: test.provider,
          model: test.model,
          grounding_mode: test.grounding_mode,
          grounded: test.grounding_mode !== 'off',  // For backward compatibility
          country: 'US',
          als_block: usALS,
          prompt: 'What is the VAT rate?',
          expected: {
            vat_percent: 'no federal VAT',
            plug: ['A', 'B'],
            emergency: ['911']
          }
        }),
      });

      const data = await response.json();
      
      setTestResults(prev => {
        const updated = [...prev];
        const test = updated[index];
        
        // Determine if test truly passed based on grounding mode expectations
        let actualStatus = 'success';
        if (data.error) {
          actualStatus = 'failed';
        } else if (test.grounding_mode === 'off' && data.grounded_effective) {
          // UNGROUNDED mode shouldn't have any grounding
          actualStatus = 'failed';
        } else if (test.grounding_mode === 'required' && !data.grounded_effective) {
          // REQUIRED mode must have grounding
          actualStatus = 'failed';
        } else if (test.grounding_mode === 'required' && data.enforcement_passed === false) {
          // REQUIRED mode with enforcement failure
          actualStatus = 'failed';
        }
        // PREFERRED mode always passes as long as no error
        
        updated[index] = {
          ...updated[index],
          status: actualStatus,
          grounded_effective: data.grounded_effective,
          tool_call_count: data.tool_call_count,
          enforcement_passed: data.enforcement_passed,
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
      return <CheckCircleIcon className="h-5 w-5 text-green-500" />;
    }
    
    if (test.status === 'failed') {
      return <XCircleIcon className="h-5 w-5 text-red-500" />;
    }
    
    return <div className="h-5 w-5 rounded-full bg-gray-200"></div>;
  };

  const getStatusColor = (test: TestResult) => {
    if (test.status === 'running') return 'bg-blue-50 border-blue-200';
    if (test.status === 'success') return 'bg-green-50 border-green-200';
    if (test.status === 'failed') return 'bg-red-50 border-red-200';
    return 'bg-gray-50 border-gray-200';
  };

  const getModeLabel = (mode: GroundingMode) => {
    switch (mode) {
      case 'off': return 'Ungrounded';
      case 'preferred': return 'Grounded (Auto)';
      case 'required': return 'Grounded (Required)';
    }
  };

  const getModeDescription = (mode: GroundingMode) => {
    switch (mode) {
      case 'off': return 'Pure model recall';
      case 'preferred': return 'Model decides when to search';
      case 'required': return 'Forces web search';
    }
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
          
          {/* GPT-5 tests: indices 0, 1, 2 */}
          {[0, 1, 2].map((idx) => {
            const test = testResults[idx];
            return (
              <div key={idx} className={`border rounded-lg p-4 ${getStatusColor(test)}`}>
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <h4 className="font-medium text-gray-900">{getModeLabel(test.grounding_mode)}</h4>
                      {getStatusIcon(test)}
                    </div>
                    <p className="text-xs text-gray-500 mt-1">{getModeDescription(test.grounding_mode)}</p>
                  </div>
                </div>
                
                {test.status !== 'pending' && test.status !== 'running' && (
                  <div className="mt-3 space-y-1 text-xs">
                    <div className="flex justify-between">
                      <span className="text-gray-500">Grounded:</span>
                      <span className={
                        test.grounding_mode === 'off' 
                          ? (test.grounded_effective ? 'text-red-500' : 'text-green-500')
                          : test.grounding_mode === 'required'
                          ? (test.grounded_effective ? 'text-green-500' : 'text-red-500')
                          : (test.grounded_effective ? 'text-blue-500' : 'text-gray-500')
                      }>
                        {test.grounded_effective ? 'Yes' : 'No'}
                        {test.grounding_mode === 'off' && test.grounded_effective && ' (unexpected)'}
                        {test.grounding_mode === 'required' && !test.grounded_effective && ' (failed)'}
                      </span>
                    </div>
                    {test.grounding_mode === 'required' && (
                      <div className="flex justify-between">
                        <span className="text-gray-500">Enforcement:</span>
                        <span className={test.enforcement_passed ? 'text-green-500' : 'text-red-500'}>
                          {test.enforcement_passed ? 'Passed' : 'Failed'}
                        </span>
                      </div>
                    )}
                    <div className="flex justify-between">
                      <span className="text-gray-500">Tool calls:</span>
                      <span className={
                        test.grounding_mode !== 'off' && !test.tool_call_count ? 'text-yellow-500' : ''
                      }>
                        {test.tool_call_count || 0}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-500">JSON valid:</span>
                      <span className={test.json_valid ? 'text-green-500' : 'text-red-500'}>
                        {test.json_valid ? 'Yes' : 'No'}
                      </span>
                    </div>
                    {test.latency_ms && (
                      <div className="flex justify-between">
                        <span className="text-gray-500">Latency:</span>
                        <span>{test.latency_ms}ms</span>
                      </div>
                    )}
                  </div>
                )}
                
                {test.error && (
                  <div className="mt-2 text-xs text-red-600">
                    Error: {test.error}
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {/* Gemini Column */}
        <div className="space-y-4">
          <h3 className="text-lg font-medium text-gray-900">Gemini 2.5 Pro</h3>
          
          {/* Gemini tests: indices 3, 4, 5 */}
          {[3, 4, 5].map((idx) => {
            const test = testResults[idx];
            return (
              <div key={idx} className={`border rounded-lg p-4 ${getStatusColor(test)}`}>
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <h4 className="font-medium text-gray-900">{getModeLabel(test.grounding_mode)}</h4>
                      {getStatusIcon(test)}
                    </div>
                    <p className="text-xs text-gray-500 mt-1">{getModeDescription(test.grounding_mode)}</p>
                  </div>
                </div>
                
                {test.status !== 'pending' && test.status !== 'running' && (
                  <div className="mt-3 space-y-1 text-xs">
                    <div className="flex justify-between">
                      <span className="text-gray-500">Grounded:</span>
                      <span className={
                        test.grounding_mode === 'off' 
                          ? (test.grounded_effective ? 'text-red-500' : 'text-green-500')
                          : test.grounding_mode === 'required'
                          ? (test.grounded_effective ? 'text-green-500' : 'text-red-500')
                          : (test.grounded_effective ? 'text-blue-500' : 'text-gray-500')
                      }>
                        {test.grounded_effective ? 'Yes' : 'No'}
                        {test.grounding_mode === 'off' && test.grounded_effective && ' (unexpected)'}
                        {test.grounding_mode === 'required' && !test.grounded_effective && ' (failed)'}
                      </span>
                    </div>
                    {test.grounding_mode === 'required' && (
                      <div className="flex justify-between">
                        <span className="text-gray-500">Enforcement:</span>
                        <span className={test.enforcement_passed !== false ? 'text-green-500' : 'text-red-500'}>
                          {test.enforcement_passed !== false ? 'Passed' : 'Failed'}
                        </span>
                      </div>
                    )}
                    <div className="flex justify-between">
                      <span className="text-gray-500">Tool calls:</span>
                      <span className={
                        test.grounding_mode !== 'off' && !test.tool_call_count ? 'text-yellow-500' : ''
                      }>
                        {test.tool_call_count || 0}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-500">JSON valid:</span>
                      <span className={test.json_valid ? 'text-green-500' : 'text-red-500'}>
                        {test.json_valid ? 'Yes' : 'No'}
                      </span>
                    </div>
                    {test.latency_ms && (
                      <div className="flex justify-between">
                        <span className="text-gray-500">Latency:</span>
                        <span>{test.latency_ms}ms</span>
                      </div>
                    )}
                  </div>
                )}
                
                {test.error && (
                  <div className="mt-2 text-xs text-red-600">
                    Error: {test.error}
                  </div>
                )}
              </div>
            );
          })}
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