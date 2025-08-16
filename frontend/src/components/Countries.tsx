'use client';

import React, { useState, useEffect } from 'react';
import { AlertCircle, CheckCircle, XCircle, Loader2, Info, Plus, Play, Globe } from 'lucide-react';

interface Country {
  id: number;
  code: string;
  name: string;
  flag_emoji?: string;
  timezone?: string;
  civic_keyword?: string;
  has_als_support: boolean;
  gpt5_test_status?: string;
  gpt5_test_date?: string;
  gpt5_test_results?: any;
  gpt5_grounded_test_status?: string;
  gpt5_grounded_test_date?: string;
  gpt5_grounded_test_results?: any;
  gemini_test_status?: string;
  gemini_test_date?: string;
  gemini_test_results?: any;
  gemini_grounded_test_status?: string;
  gemini_grounded_test_date?: string;
  gemini_grounded_test_results?: any;
}

interface TestResult {
  country_code: string;
  country_name: string;
  model: string;
  test_date: string;
  overall_status: string;
  probes: {
    [key: string]: {
      question: string;
      response: string;
      passed: boolean;
      expected: string;
      found: string;
    };
  };
}

export default function Countries() {
  const [countries, setCountries] = useState<Country[]>([]);
  const [loading, setLoading] = useState(true);
  const [testing, setTesting] = useState<{ [key: string]: boolean }>({});
  const [testProgress, setTestProgress] = useState<{ [key: string]: { current: number; total: number; probe: string } }>({});
  const [selectedCountry, setSelectedCountry] = useState<Country | null>(null);
  const [selectedModel, setSelectedModel] = useState<'gpt5' | 'gemini' | null>(null);
  const [selectedGrounded, setSelectedGrounded] = useState<boolean>(false);
  const [showDetails, setShowDetails] = useState(false);
  const [showAddForm, setShowAddForm] = useState(false);
  const [newCountry, setNewCountry] = useState({
    code: '',
    name: '',
    flag_emoji: '',
    timezone: '',
    civic_keyword: '',
    has_als_support: false
  });

  // Helper functions for expected values per country
  const getExpectedVAT = (code: string): string => {
    const vatRates: { [key: string]: string } = {
      'SG': '9%',
      'US': '0%',
      'GB': '20%',
      'DE': '19%',
      'FR': '20%',
      'IT': '22%',
      'CH': '8.1%',
      'AE': '5%'
    };
    return vatRates[code] || '0%';
  };

  const getExpectedPlugs = (code: string): string[] => {
    const plugTypes: { [key: string]: string[] } = {
      'SG': ['G'],
      'US': ['A', 'B'],
      'GB': ['G'],
      'DE': ['F', 'C'],
      'FR': ['E', 'F', 'C'],
      'IT': ['L', 'F', 'C'],
      'CH': ['J', 'C'],
      'AE': ['G', 'C', 'D']
    };
    return plugTypes[code] || ['A'];
  };

  const getExpectedEmergency = (code: string): string[] => {
    const emergency: { [key: string]: string[] } = {
      'SG': ['999', '995'],
      'US': ['911'],
      'GB': ['999', '112'],
      'DE': ['112', '110'],
      'FR': ['112', '15', '17', '18'],
      'IT': ['112', '113'],
      'CH': ['112', '117', '118'],
      'AE': ['999', '998']
    };
    return emergency[code] || ['911'];
  };

  useEffect(() => {
    fetchCountries();
  }, []);

  const fetchCountries = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/countries');
      const data = await response.json();
      setCountries(data);
    } catch (error) {
      console.error('Failed to fetch countries:', error);
    } finally {
      setLoading(false);
    }
  };

  const runAllTests = async () => {
    // Test all countries with all 4 combinations
    for (const country of countries) {
      // Run 4 tests per country
      await testCountry(country.code, 'gpt5', false);  // GPT-5 Ungrounded
      await testCountry(country.code, 'gpt5', true);   // GPT-5 Grounded
      await testCountry(country.code, 'gemini', false); // Gemini Ungrounded
      await testCountry(country.code, 'gemini', true);  // Gemini Grounded
    }
  };

  const testCountry = async (countryCode: string, model: 'gpt5' | 'gemini', grounded: boolean = false) => {
    const testKey = `${countryCode}-${model}${grounded ? '-grounded' : ''}`;
    
    // Prevent duplicate tests
    if (testing[testKey]) {
      console.log(`Test already running for ${countryCode} with ${model} (grounded: ${grounded})`);
      return;
    }
    
    setTesting(prev => ({ ...prev, [testKey]: true }));
    setTestProgress(prev => ({ 
      ...prev, 
      [testKey]: { current: 0, total: 1, probe: grounded ? 'Grounded Check' : 'Locale Check' }
    }));

    try {
      // Find the country to get its ALS block
      const country = countries.find(c => c.code === countryCode);
      if (!country) {
        throw new Error('Country not found');
      }

      // Use the grounding test endpoint for both grounded and ungrounded tests
      const response = await fetch('http://localhost:8000/api/grounding-test/run-locale-test', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          provider: model === 'gpt5' ? 'openai' : 'vertex',
          model: model === 'gpt5' ? 'gpt-5' : 'gemini-2.5-pro',
          grounded: grounded,
          country: countryCode,
          als_block: `[ALS]\nOperating from ${country.name}. Local context and regulations apply.`,
          expected: {
            vat_percent: getExpectedVAT(countryCode),
            plug: getExpectedPlugs(countryCode),
            emergency: getExpectedEmergency(countryCode)
          }
        })
      });

      if (response.ok) {
        const result = await response.json();
        
        // Update the country's test results
        setCountries(prev => prev.map(c => {
          if (c.code === countryCode) {
            if (grounded) {
              // Update grounded test results
              if (model === 'gpt5') {
                return {
                  ...c,
                  gpt5_grounded_test_status: result.success ? 
                    (result.passed_vat && result.passed_plug && result.passed_emergency ? 'passed' : 'partial') : 
                    'failed',
                  gpt5_grounded_test_date: new Date().toISOString(),
                  gpt5_grounded_test_results: result
                };
              } else {
                return {
                  ...c,
                  gemini_grounded_test_status: result.success ? 
                    (result.passed_vat && result.passed_plug && result.passed_emergency ? 'passed' : 'partial') : 
                    'failed',
                  gemini_grounded_test_date: new Date().toISOString(),
                  gemini_grounded_test_results: result
                };
              }
            } else {
              // Update ungrounded test results
              if (model === 'gpt5') {
                return {
                  ...c,
                  gpt5_test_status: result.success ? 
                    (result.passed_vat && result.passed_plug && result.passed_emergency ? 'passed' : 'partial') : 
                    'failed',
                  gpt5_test_date: new Date().toISOString(),
                  gpt5_test_results: result
                };
              } else {
                return {
                  ...c,
                  gemini_test_status: result.success ? 
                    (result.passed_vat && result.passed_plug && result.passed_emergency ? 'passed' : 'partial') : 
                    'failed',
                  gemini_test_date: new Date().toISOString(),
                  gemini_test_results: result
                };
              }
            }
          }
          return c;
        }));
        
        // Clean up the testing state after successful completion
        setTesting(prev => ({ ...prev, [testKey]: false }));
        setTestProgress(prev => {
          const { [testKey]: _, ...rest } = prev;
          return rest;
        });
      } else if (!response.ok) {
        // Fallback to regular test endpoint if progress endpoint not found
        if (response.status === 404) {
          const fallbackResponse = await fetch('http://localhost:8000/api/countries/test', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              country_code: countryCode,
              model: model
            })
          });
          
          if (fallbackResponse.ok) {
            const result = await fallbackResponse.json();
            if (result.error === 'empty_response') {
              alert(`${model === 'gpt5' ? 'GPT-5' : 'Gemini'} returned empty responses. Please try again.`);
            }
            await fetchCountries();
            // Clean up the testing state after fallback completion
            setTesting(prev => ({ ...prev, [testKey]: false }));
            setTestProgress(prev => {
              const { [testKey]: _, ...rest } = prev;
              return rest;
            });
            return;
          } else {
            const errorText = await fallbackResponse.text();
            console.error('Test failed:', errorText);
            alert(`Test failed: ${errorText}`);
            // Clean up the testing state on error
            setTesting(prev => ({ ...prev, [testKey]: false }));
            setTestProgress(prev => {
              const { [testKey]: _, ...rest } = prev;
              return rest;
            });
            return;
          }
        }
        
        const errorText = await response.text();
        console.error('Test failed:', errorText);
        alert(`Test failed: ${errorText}`);
        // Clean up the testing state on error
        setTesting(prev => ({ ...prev, [testKey]: false }));
        setTestProgress(prev => {
          const { [testKey]: _, ...rest } = prev;
          return rest;
        });
        return;
      }

      // Read streaming response
      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      if (reader) {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          
          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() || '';
          
          for (const line of lines) {
            if (line.trim()) {
              try {
                const data = JSON.parse(line);
                if (data.type === 'progress') {
                  setTestProgress(prev => ({
                    ...prev,
                    [testKey]: {
                      current: data.current,
                      total: data.total,
                      probe: data.probe
                    }
                  }));
                } else if (data.type === 'complete') {
                  if (data.error === 'empty_response') {
                    alert(`${model === 'gpt5' ? 'GPT-5' : 'Gemini'} returned empty responses. Please try again.`);
                  }
                  await fetchCountries(); // Refresh to show updated test results
                  // Clean up the testing state after completion
                  setTesting(prev => ({ ...prev, [testKey]: false }));
                  setTestProgress(prev => {
                    const { [testKey]: _, ...rest } = prev;
                    return rest;
                  });
                }
              } catch (e) {
                console.error('Failed to parse streaming data:', e);
              }
            }
          }
        }
      }
    } catch (error) {
      console.error('Test error:', error);
      alert(`Test error: ${error}`);
      setTesting(prev => ({ ...prev, [testKey]: false }));
      setTestProgress(prev => {
        const { [testKey]: _, ...rest } = prev;
        return rest;
      });
    }
  };

  const addCountry = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/countries', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newCountry)
      });

      if (response.ok) {
        await fetchCountries();
        setShowAddForm(false);
        setNewCountry({
          code: '',
          name: '',
          flag_emoji: '',
          timezone: '',
          civic_keyword: '',
          has_als_support: false
        });
      } else {
        const error = await response.text();
        alert(`Failed to add country: ${error}`);
      }
    } catch (error) {
      console.error('Add country error:', error);
    }
  };

  const getStatusIcon = (status?: string) => {
    switch (status) {
      case 'passed':
        return <CheckCircle className="h-5 w-5 text-green-600" />;
      case 'partial':
        return <AlertCircle className="h-5 w-5 text-yellow-600" />;
      case 'failed':
        return <XCircle className="h-5 w-5 text-red-600" />;
      default:
        return <AlertCircle className="h-5 w-5 text-gray-400" />;
    }
  };

  const formatTestDate = (dateStr?: string) => {
    if (!dateStr) return 'Never tested';
    const date = new Date(dateStr);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
  };

  const showCountryDetails = (country: Country, model: 'gpt5' | 'gemini', grounded: boolean = false) => {
    setSelectedCountry(country);
    setSelectedModel(model);
    setSelectedGrounded(grounded);
    setShowDetails(true);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-contestra-green" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold text-gray-900">Countries</h2>
        <div className="flex gap-2">
          <button
            onClick={runAllTests}
            disabled={Object.keys(testing).length > 0}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {Object.keys(testing).length > 0 ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Testing...
              </>
            ) : (
              <>
                <Play className="h-4 w-4" />
                Run All Tests
              </>
            )}
          </button>
          <button
            onClick={() => setShowAddForm(true)}
            className="flex items-center gap-2 px-4 py-2 bg-contestra-green text-white rounded-lg hover:bg-green-700 transition-colors"
          >
            <Plus className="h-4 w-4" />
            Add Country
          </button>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="min-w-full">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Country
              </th>
              <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider" colSpan={2}>
                GPT-5 Locale Test
              </th>
              <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider" colSpan={2}>
                Gemini 2.5 Pro Locale Test
              </th>
            </tr>
            <tr>
              <th className="px-6 py-2 text-left text-xs font-medium text-gray-400"></th>
              <th className="px-3 py-2 text-center text-xs font-medium text-gray-400">Ungrounded</th>
              <th className="px-3 py-2 text-center text-xs font-medium text-gray-400">Grounded</th>
              <th className="px-3 py-2 text-center text-xs font-medium text-gray-400">Ungrounded</th>
              <th className="px-3 py-2 text-center text-xs font-medium text-gray-400">Grounded</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {countries.map((country) => (
              <tr key={country.id}>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="flex items-center">
                    <span className="text-2xl mr-3">{country.flag_emoji || <Globe className="h-6 w-6 text-gray-400" />}</span>
                    <div className="text-sm font-medium text-gray-900">{country.name}</div>
                  </div>
                </td>
                {/* GPT-5 Ungrounded */}
                <td className="px-3 py-4 whitespace-nowrap text-center">
                  <div className="flex flex-col items-center gap-1">
                    {country.gpt5_test_status && country.gpt5_test_status !== 'untested' ? (
                      <>
                        {getStatusIcon(country.gpt5_test_status)}
                        <div className="flex items-center gap-1">
                          {country.gpt5_test_results && (
                            <button
                              onClick={() => showCountryDetails(country, 'gpt5', false)}
                              className="p-1 text-gray-600 hover:text-contestra-blue hover:bg-gray-100 rounded transition-colors"
                              title="View test details"
                            >
                              <Info className="h-4 w-4" />
                            </button>
                          )}
                          <button
                            onClick={() => testCountry(country.code, 'gpt5', false)}
                            disabled={testing[`${country.code}-gpt5`]}
                            className="p-1 text-gray-600 hover:text-contestra-green hover:bg-gray-100 rounded transition-colors"
                            title="Retest with GPT-5"
                          >
                            {testing[`${country.code}-gpt5`] ? (
                              <Loader2 className="h-4 w-4 animate-spin" />
                            ) : (
                              <Play className="h-4 w-4" />
                            )}
                          </button>
                        </div>
                      </>
                    ) : (
                      <button
                        onClick={() => testCountry(country.code, 'gpt5', false)}
                        disabled={testing[`${country.code}-gpt5`]}
                        className="px-3 py-1 text-sm bg-contestra-green text-white rounded hover:bg-green-700 disabled:opacity-50"
                      >
                        {testing[`${country.code}-gpt5`] ? (
                          <div className="flex items-center gap-1">
                            <Loader2 className="h-4 w-4 animate-spin" />
                            {testProgress[`${country.code}-gpt5`] && (
                              <span className="text-xs">
                                {testProgress[`${country.code}-gpt5`].current}/{testProgress[`${country.code}-gpt5`].total}
                              </span>
                            )}
                          </div>
                        ) : (
                          'Locale Check'
                        )}
                      </button>
                    )}
                  </div>
                </td>
                
                {/* GPT-5 Grounded */}
                <td className="px-3 py-4 whitespace-nowrap text-center">
                  <div className="flex flex-col items-center gap-1">
                    {country.gpt5_grounded_test_status && country.gpt5_grounded_test_status !== 'untested' ? (
                      <>
                        {getStatusIcon(country.gpt5_grounded_test_status)}
                        <div className="flex items-center gap-1">
                          {country.gpt5_grounded_test_results && (
                            <button
                              onClick={() => showCountryDetails(country, 'gpt5', true)}
                              className="p-1 text-gray-600 hover:text-contestra-blue hover:bg-gray-100 rounded transition-colors"
                              title="View test details"
                            >
                              <Info className="h-4 w-4" />
                            </button>
                          )}
                          <button
                            onClick={() => testCountry(country.code, 'gpt5', true)}
                            disabled={testing[`${country.code}-gpt5-grounded`]}
                            className="p-1 text-gray-600 hover:text-contestra-green hover:bg-gray-100 rounded transition-colors"
                            title="Retest with GPT-5 (Grounded)"
                          >
                            {testing[`${country.code}-gpt5-grounded`] ? (
                              <Loader2 className="h-4 w-4 animate-spin" />
                            ) : (
                              <Play className="h-4 w-4" />
                            )}
                          </button>
                        </div>
                      </>
                    ) : (
                      <button
                        onClick={() => testCountry(country.code, 'gpt5', true)}
                        disabled={testing[`${country.code}-gpt5-grounded`]}
                        className="px-3 py-1 text-sm bg-contestra-green text-white rounded hover:bg-green-700 disabled:opacity-50"
                      >
                        {testing[`${country.code}-gpt5-grounded`] ? (
                          <div className="flex items-center gap-1">
                            <Loader2 className="h-4 w-4 animate-spin" />
                            {testProgress[`${country.code}-gpt5-grounded`] && (
                              <span className="text-xs">
                                {testProgress[`${country.code}-gpt5-grounded`].current}/{testProgress[`${country.code}-gpt5-grounded`].total}
                              </span>
                            )}
                          </div>
                        ) : (
                          'Grounded Check'
                        )}
                      </button>
                    )}
                  </div>
                </td>
                
                {/* Gemini Ungrounded */}
                <td className="px-3 py-4 whitespace-nowrap text-center">
                  <div className="flex flex-col items-center gap-1">
                    {country.gemini_test_status && country.gemini_test_status !== 'untested' ? (
                      <>
                        {getStatusIcon(country.gemini_test_status)}
                        <div className="flex items-center gap-1">
                          {country.gemini_test_results && (
                            <button
                              onClick={() => showCountryDetails(country, 'gemini', false)}
                              className="p-1 text-gray-600 hover:text-contestra-blue hover:bg-gray-100 rounded transition-colors"
                              title="View test details"
                            >
                              <Info className="h-4 w-4" />
                            </button>
                          )}
                          <button
                            onClick={() => testCountry(country.code, 'gemini', false)}
                            disabled={testing[`${country.code}-gemini`]}
                            className="p-1 text-gray-600 hover:text-contestra-green hover:bg-gray-100 rounded transition-colors"
                            title="Retest with Gemini"
                          >
                            {testing[`${country.code}-gemini`] ? (
                              <Loader2 className="h-4 w-4 animate-spin" />
                            ) : (
                              <Play className="h-4 w-4" />
                            )}
                          </button>
                        </div>
                      </>
                    ) : (
                      <button
                        onClick={() => testCountry(country.code, 'gemini', false)}
                        disabled={testing[`${country.code}-gemini`]}
                        className="px-3 py-1 text-sm bg-contestra-green text-white rounded hover:bg-green-700 disabled:opacity-50"
                      >
                        {testing[`${country.code}-gemini`] ? (
                          <div className="flex items-center gap-1">
                            <Loader2 className="h-4 w-4 animate-spin" />
                            {testProgress[`${country.code}-gemini`] && (
                              <span className="text-xs">
                                {testProgress[`${country.code}-gemini`].current}/{testProgress[`${country.code}-gemini`].total}
                              </span>
                            )}
                          </div>
                        ) : (
                          'Locale Check'
                        )}
                      </button>
                    )}
                  </div>
                </td>
                
                {/* Gemini Grounded */}
                <td className="px-3 py-4 whitespace-nowrap text-center">
                  <div className="flex flex-col items-center gap-1">
                    {country.gemini_grounded_test_status && country.gemini_grounded_test_status !== 'untested' ? (
                      <>
                        {getStatusIcon(country.gemini_grounded_test_status)}
                        <div className="flex items-center gap-1">
                          {country.gemini_grounded_test_results && (
                            <button
                              onClick={() => showCountryDetails(country, 'gemini', true)}
                              className="p-1 text-gray-600 hover:text-contestra-blue hover:bg-gray-100 rounded transition-colors"
                              title="View test details"
                            >
                              <Info className="h-4 w-4" />
                            </button>
                          )}
                          <button
                            onClick={() => testCountry(country.code, 'gemini', true)}
                            disabled={testing[`${country.code}-gemini-grounded`]}
                            className="p-1 text-gray-600 hover:text-contestra-green hover:bg-gray-100 rounded transition-colors"
                            title="Retest with Gemini (Grounded)"
                          >
                            {testing[`${country.code}-gemini-grounded`] ? (
                              <Loader2 className="h-4 w-4 animate-spin" />
                            ) : (
                              <Play className="h-4 w-4" />
                            )}
                          </button>
                        </div>
                      </>
                    ) : (
                      <button
                        onClick={() => testCountry(country.code, 'gemini', true)}
                        disabled={testing[`${country.code}-gemini-grounded`]}
                        className="px-3 py-1 text-sm bg-contestra-green text-white rounded hover:bg-green-700 disabled:opacity-50"
                      >
                        {testing[`${country.code}-gemini-grounded`] ? (
                          <div className="flex items-center gap-1">
                            <Loader2 className="h-4 w-4 animate-spin" />
                            {testProgress[`${country.code}-gemini-grounded`] && (
                              <span className="text-xs">
                                {testProgress[`${country.code}-gemini-grounded`].current}/{testProgress[`${country.code}-gemini-grounded`].total}
                              </span>
                            )}
                          </div>
                        ) : (
                          'Grounded Check'
                        )}
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Details Modal */}
      {showDetails && selectedCountry && selectedModel && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg max-w-2xl w-full max-h-[80vh] overflow-y-auto p-6">
            <div className="flex justify-between items-start mb-4">
              <h3 className="text-xl font-bold">
                {selectedCountry.flag_emoji} {selectedCountry.name} - {selectedModel === 'gpt5' ? 'GPT-5' : 'Gemini 2.5 Pro'} {selectedGrounded ? 'Grounded' : 'Ungrounded'}
              </h3>
              <button
                onClick={() => setShowDetails(false)}
                className="text-gray-400 hover:text-gray-600"
              >
                ✕
              </button>
            </div>

            {/* Show only the specific test results based on what was clicked */}
            <div className="space-y-4">
              {selectedModel === 'gpt5' && !selectedGrounded && selectedCountry.gpt5_test_results && (
                <div className="border rounded-lg p-4">
                  <h4 className="font-semibold mb-3 flex items-center gap-2">
                    GPT-5 Ungrounded Results
                    {getStatusIcon(selectedCountry.gpt5_test_status)}
                  </h4>
                  <div className="space-y-3">
                    <div className="text-sm text-gray-700">
                      <strong>VAT:</strong> {selectedCountry.gpt5_test_results.json_obj?.vat_percent || 'N/A'} 
                      <span className="text-xs text-gray-500 ml-2">(Expected: {getExpectedVAT(selectedCountry.code)})</span>
                    </div>
                    <div className="text-sm text-gray-700">
                      <strong>Plug:</strong> {selectedCountry.gpt5_test_results.json_obj?.plug?.join(', ') || 'N/A'}
                      <span className="text-xs text-gray-500 ml-2">(Expected: {getExpectedPlugs(selectedCountry.code).join(', ')})</span>
                    </div>
                    <div className="text-sm text-gray-700">
                      <strong>Emergency:</strong> {selectedCountry.gpt5_test_results.json_obj?.emergency?.join(', ') || 'N/A'}
                      <span className="text-xs text-gray-500 ml-2">(Expected: {getExpectedEmergency(selectedCountry.code).join(', ')})</span>
                    </div>
                    <div className="text-xs text-gray-500 mt-2 pt-2 border-t">
                      Grounding: {selectedCountry.gpt5_test_results.grounded_effective ? 'Yes' : 'No'}
                    </div>
                  </div>
                </div>
              )}
              
              {selectedModel === 'gpt5' && selectedGrounded && selectedCountry.gpt5_grounded_test_results && (
                <div className="border rounded-lg p-4">
                  <h4 className="font-semibold mb-3 flex items-center gap-2">
                    GPT-5 Grounded Results
                    {getStatusIcon(selectedCountry.gpt5_grounded_test_status)}
                  </h4>
                  <div className="space-y-3">
                    <div className="text-sm text-gray-700">
                      <strong>VAT:</strong> {selectedCountry.gpt5_grounded_test_results.json_obj?.vat_percent || 'N/A'}
                      <span className="text-xs text-gray-500 ml-2">(Expected: {getExpectedVAT(selectedCountry.code)})</span>
                    </div>
                    <div className="text-sm text-gray-700">
                      <strong>Plug:</strong> {selectedCountry.gpt5_grounded_test_results.json_obj?.plug?.join(', ') || 'N/A'}
                      <span className="text-xs text-gray-500 ml-2">(Expected: {getExpectedPlugs(selectedCountry.code).join(', ')})</span>
                    </div>
                    <div className="text-sm text-gray-700">
                      <strong>Emergency:</strong> {selectedCountry.gpt5_grounded_test_results.json_obj?.emergency?.join(', ') || 'N/A'}
                      <span className="text-xs text-gray-500 ml-2">(Expected: {getExpectedEmergency(selectedCountry.code).join(', ')})</span>
                    </div>
                    <div className="text-sm text-blue-600 mt-3 pt-2 border-t">
                      🔍 Web searches performed: {selectedCountry.gpt5_grounded_test_results.tool_call_count || 0}
                    </div>
                  </div>
                </div>
              )}

              {selectedModel === 'gemini' && !selectedGrounded && selectedCountry.gemini_test_results && (
                <div className="border rounded-lg p-4">
                  <h4 className="font-semibold mb-3 flex items-center gap-2">
                    Gemini Ungrounded Results
                    {getStatusIcon(selectedCountry.gemini_test_status)}
                  </h4>
                  <div className="space-y-3">
                    <div className="text-sm text-gray-700">
                      <strong>VAT:</strong> {selectedCountry.gemini_test_results.json_obj?.vat_percent || 'N/A'}
                      <span className="text-xs text-gray-500 ml-2">(Expected: {getExpectedVAT(selectedCountry.code)})</span>
                    </div>
                    <div className="text-sm text-gray-700">
                      <strong>Plug:</strong> {selectedCountry.gemini_test_results.json_obj?.plug?.join(', ') || 'N/A'}
                      <span className="text-xs text-gray-500 ml-2">(Expected: {getExpectedPlugs(selectedCountry.code).join(', ')})</span>
                    </div>
                    <div className="text-sm text-gray-700">
                      <strong>Emergency:</strong> {selectedCountry.gemini_test_results.json_obj?.emergency?.join(', ') || 'N/A'}
                      <span className="text-xs text-gray-500 ml-2">(Expected: {getExpectedEmergency(selectedCountry.code).join(', ')})</span>
                    </div>
                    <div className="text-xs text-gray-500 mt-2 pt-2 border-t">
                      Grounding: {selectedCountry.gemini_test_results.grounded_effective ? 'Yes' : 'No'}
                    </div>
                  </div>
                </div>
              )}
              
              {selectedModel === 'gemini' && selectedGrounded && selectedCountry.gemini_grounded_test_results && (
                <div className="border rounded-lg p-4">
                  <h4 className="font-semibold mb-3 flex items-center gap-2">
                    Gemini Grounded Results
                    {getStatusIcon(selectedCountry.gemini_grounded_test_status)}
                  </h4>
                  <div className="space-y-3">
                    <div className="text-sm text-gray-700">
                      <strong>VAT:</strong> {selectedCountry.gemini_grounded_test_results.json_obj?.vat_percent || 'N/A'}
                      <span className="text-xs text-gray-500 ml-2">(Expected: {getExpectedVAT(selectedCountry.code)})</span>
                    </div>
                    <div className="text-sm text-gray-700">
                      <strong>Plug:</strong> {selectedCountry.gemini_grounded_test_results.json_obj?.plug?.join(', ') || 'N/A'}
                      <span className="text-xs text-gray-500 ml-2">(Expected: {getExpectedPlugs(selectedCountry.code).join(', ')})</span>
                    </div>
                    <div className="text-sm text-gray-700">
                      <strong>Emergency:</strong> {selectedCountry.gemini_grounded_test_results.json_obj?.emergency?.join(', ') || 'N/A'}
                      <span className="text-xs text-gray-500 ml-2">(Expected: {getExpectedEmergency(selectedCountry.code).join(', ')})</span>
                    </div>
                    <div className="text-sm text-blue-600 mt-3 pt-2 border-t">
                      🔍 Web searches performed: {selectedCountry.gemini_grounded_test_results.tool_call_count || 0}
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Add Country Form */}
      {showAddForm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg max-w-md w-full p-6">
            <h3 className="text-xl font-bold mb-4">Add New Country</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Country Code (ISO 2-letter)
                </label>
                <input
                  type="text"
                  value={newCountry.code}
                  onChange={(e) => setNewCountry({ ...newCountry, code: e.target.value.toUpperCase() })}
                  maxLength={2}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                  placeholder="US"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Country Name
                </label>
                <input
                  type="text"
                  value={newCountry.name}
                  onChange={(e) => setNewCountry({ ...newCountry, name: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                  placeholder="United States"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Flag Emoji (optional)
                </label>
                <input
                  type="text"
                  value={newCountry.flag_emoji}
                  onChange={(e) => setNewCountry({ ...newCountry, flag_emoji: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                  placeholder="🇺🇸"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Timezone (optional)
                </label>
                <input
                  type="text"
                  value={newCountry.timezone}
                  onChange={(e) => setNewCountry({ ...newCountry, timezone: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                  placeholder="America/New_York"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Civic Keyword (optional)
                </label>
                <input
                  type="text"
                  value={newCountry.civic_keyword}
                  onChange={(e) => setNewCountry({ ...newCountry, civic_keyword: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                  placeholder="DMV"
                />
              </div>
              <div className="flex items-center">
                <input
                  type="checkbox"
                  id="als-support"
                  checked={newCountry.has_als_support}
                  onChange={(e) => setNewCountry({ ...newCountry, has_als_support: e.target.checked })}
                  className="mr-2"
                />
                <label htmlFor="als-support" className="text-sm font-medium text-gray-700">
                  Has ALS Support
                </label>
              </div>
            </div>
            <div className="flex justify-end gap-3 mt-6">
              <button
                onClick={() => setShowAddForm(false)}
                className="px-4 py-2 border border-gray-300 rounded-md hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={addCountry}
                className="px-4 py-2 bg-contestra-green text-white rounded-md hover:bg-green-700"
              >
                Add Country
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}