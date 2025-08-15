import React, { useState } from 'react';
import { Button } from './ui/button';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';
import { Loader2, Check, X, AlertCircle } from 'lucide-react';

interface TestResult {
  provider: 'openai' | 'vertex';
  model: string;
  grounded: boolean;
  status: 'pending' | 'running' | 'success' | 'failed' | 'na';
  grounded_effective?: boolean;
  tool_call_count?: number;
  json_valid?: boolean;
  json_obj?: any;
  latency_ms?: number;
  error?: string;
}

interface Country {
  code: string;
  name: string;
  flag: string;
  expected: {
    vat_percent: string;
    plug: string[];
    emergency: string[];
  };
  als_block: string;
}

const COUNTRIES: Country[] = [
  {
    code: 'SG',
    name: 'Singapore',
    flag: '🇸🇬',
    expected: {
      vat_percent: '9%',
      plug: ['G'],
      emergency: ['999', '995']
    },
    als_block: '[ALS]\nOperating from Singapore; prices in S$. Date format DD/MM/YYYY.\nPostal 018956. Tel +65 6123 4567. GST applies.\nEmergency: 999 (police), 995 (fire/ambulance).'
  },
  {
    code: 'US',
    name: 'United States',
    flag: '🇺🇸',
    expected: {
      vat_percent: '0%',
      plug: ['A', 'B'],
      emergency: ['911']
    },
    als_block: '[ALS]\nOperating from USA; prices in USD. Date format MM/DD/YYYY.\nZIP 10001. Tel +1 212 555 0100. Sales tax varies by state.\nEmergency: 911.'
  },
  {
    code: 'DE',
    name: 'Germany',
    flag: '🇩🇪',
    expected: {
      vat_percent: '19%',
      plug: ['F', 'C'],
      emergency: ['112', '110']
    },
    als_block: '[ALS]\nBetrieb aus Deutschland; Preise in EUR. Datumsformat TT.MM.JJJJ.\n10115 Berlin. Tel +49 30 12345678. MwSt. 19%.\nNotruf: 112 (Notfall), 110 (Polizei).'
  },
  {
    code: 'CH',
    name: 'Switzerland',
    flag: '🇨🇭',
    expected: {
      vat_percent: '8.1%',
      plug: ['J', 'C'],
      emergency: ['112', '117', '118', '144']
    },
    als_block: '[ALS]\nBetrieb aus der Schweiz; Preise in CHF. Datumsformat TT.MM.JJJJ.\n8001 Zürich. Tel +41 44 123 4567. MwSt. 8.1%.\nNotruf: 112 (allgemein), 117 (Polizei), 118 (Feuerwehr), 144 (Rettung).'
  }
];

export default function GroundingTestGrid() {
  const [selectedCountry, setSelectedCountry] = useState<Country>(COUNTRIES[0]);
  const [testResults, setTestResults] = useState<TestResult[]>([
    { provider: 'openai', model: 'gpt-4o', grounded: false, status: 'pending' },
    { provider: 'openai', model: 'gpt-4o', grounded: true, status: 'pending' },
    { provider: 'vertex', model: 'gemini-2.0-flash', grounded: false, status: 'pending' },
    { provider: 'vertex', model: 'gemini-2.0-flash', grounded: true, status: 'pending' },
  ]);
  const [isRunning, setIsRunning] = useState(false);

  const runTest = async (index: number) => {
    const test = testResults[index];
    
    // Update status to running
    const newResults = [...testResults];
    newResults[index] = { ...test, status: 'running' };
    setTestResults(newResults);

    try {
      const response = await fetch('/api/prompt-tracking/run-locale-test', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          provider: test.provider,
          model: test.model,
          grounded: test.grounded,
          country: selectedCountry.code,
          als_block: selectedCountry.als_block,
          expected: selectedCountry.expected
        })
      });

      const result = await response.json();
      
      newResults[index] = {
        ...test,
        status: result.success ? 'success' : 'failed',
        grounded_effective: result.grounded_effective,
        tool_call_count: result.tool_call_count,
        json_valid: result.json_valid,
        json_obj: result.json_obj,
        latency_ms: result.latency_ms,
        error: result.error
      };
    } catch (error) {
      newResults[index] = {
        ...test,
        status: 'failed',
        error: error instanceof Error ? error.message : 'Unknown error'
      };
    }

    setTestResults(newResults);
  };

  const runAllTests = async () => {
    setIsRunning(true);
    
    // Run tests sequentially to avoid rate limits
    for (let i = 0; i < testResults.length; i++) {
      if (testResults[i].status !== 'na') {
        await runTest(i);
      }
    }
    
    setIsRunning(false);
  };

  const resetTests = () => {
    setTestResults(testResults.map(t => ({ ...t, status: 'pending', grounded_effective: undefined, tool_call_count: undefined, json_valid: undefined, json_obj: undefined, latency_ms: undefined, error: undefined })));
  };

  const getStatusIcon = (result: TestResult) => {
    switch (result.status) {
      case 'pending':
        return <div className="w-12 h-12 rounded-full bg-gray-200" />;
      case 'running':
        return <Loader2 className="w-12 h-12 text-blue-500 animate-spin" />;
      case 'success':
        return <Check className="w-12 h-12 text-green-500" />;
      case 'failed':
        return <X className="w-12 h-12 text-red-500" />;
      case 'na':
        return <AlertCircle className="w-12 h-12 text-gray-400" />;
    }
  };

  const getTestDetails = (result: TestResult) => {
    if (result.status === 'pending' || result.status === 'running') return null;
    
    return (
      <div className="mt-2 text-xs space-y-1">
        {result.grounded_effective !== undefined && (
          <div>Grounded: {result.grounded_effective ? 'Yes' : 'No'}</div>
        )}
        {result.tool_call_count !== undefined && (
          <div>Tool calls: {result.tool_call_count}</div>
        )}
        {result.json_valid !== undefined && (
          <div>JSON valid: {result.json_valid ? 'Yes' : 'No'}</div>
        )}
        {result.latency_ms !== undefined && (
          <div>Latency: {result.latency_ms}ms</div>
        )}
        {result.error && (
          <div className="text-red-500">Error: {result.error}</div>
        )}
      </div>
    );
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>4-Column Grounding Test Grid</CardTitle>
        </CardHeader>
        <CardContent>
          {/* Country Selector */}
          <div className="mb-6">
            <label className="block text-sm font-medium mb-2">Select Country</label>
            <div className="flex gap-2">
              {COUNTRIES.map(country => (
                <Button
                  key={country.code}
                  variant={selectedCountry.code === country.code ? 'default' : 'outline'}
                  onClick={() => setSelectedCountry(country)}
                  disabled={isRunning}
                >
                  {country.flag} {country.name}
                </Button>
              ))}
            </div>
          </div>

          {/* Test Controls */}
          <div className="flex gap-2 mb-6">
            <Button onClick={runAllTests} disabled={isRunning}>
              {isRunning ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Running Tests...
                </>
              ) : (
                'Run All Tests'
              )}
            </Button>
            <Button variant="outline" onClick={resetTests} disabled={isRunning}>
              Reset
            </Button>
          </div>

          {/* Test Grid */}
          <div className="grid grid-cols-4 gap-4">
            {/* Headers */}
            <div className="text-center font-semibold">
              <div>GPT-4o</div>
              <Badge variant="outline" className="mt-1">Ungrounded</Badge>
            </div>
            <div className="text-center font-semibold">
              <div>GPT-4o</div>
              <Badge variant="default" className="mt-1">Grounded</Badge>
            </div>
            <div className="text-center font-semibold">
              <div>Gemini 2.0</div>
              <Badge variant="outline" className="mt-1">Ungrounded</Badge>
            </div>
            <div className="text-center font-semibold">
              <div>Gemini 2.0</div>
              <Badge variant="default" className="mt-1">Grounded</Badge>
            </div>

            {/* Test Results */}
            {testResults.map((result, index) => (
              <div key={index} className="text-center p-4 border rounded-lg">
                <div className="flex justify-center mb-2">
                  {getStatusIcon(result)}
                </div>
                {getTestDetails(result)}
              </div>
            ))}
          </div>

          {/* Expected Values */}
          <div className="mt-6 p-4 bg-gray-50 rounded-lg">
            <h3 className="font-semibold mb-2">Expected Values for {selectedCountry.flag} {selectedCountry.name}</h3>
            <div className="grid grid-cols-3 gap-4 text-sm">
              <div>
                <span className="font-medium">VAT/GST:</span> {selectedCountry.expected.vat_percent}
              </div>
              <div>
                <span className="font-medium">Plug:</span> {selectedCountry.expected.plug.join(', ')}
              </div>
              <div>
                <span className="font-medium">Emergency:</span> {selectedCountry.expected.emergency.join(', ')}
              </div>
            </div>
          </div>

          {/* ALS Block Preview */}
          <details className="mt-4">
            <summary className="cursor-pointer text-sm font-medium">View ALS Block</summary>
            <pre className="mt-2 p-3 bg-gray-100 rounded text-xs overflow-x-auto">
              {selectedCountry.als_block}
            </pre>
          </details>
        </CardContent>
      </Card>
    </div>
  );
}