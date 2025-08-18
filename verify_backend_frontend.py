"""
Verify backend data matches frontend display
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8000"

def verify_data():
    print("=" * 80)
    print("BACKEND-FRONTEND DATA VERIFICATION")
    print("=" * 80)
    
    brand_name = "AVEA"
    
    # 1. Get all templates from backend
    print("\n1. BACKEND TEMPLATES CHECK")
    print("-" * 40)
    response = requests.get(f"{BASE_URL}/api/prompt-tracking/templates?brand_name={brand_name}")
    if response.status_code == 200:
        data = response.json()
        # Handle both dict and list response
        if isinstance(data, dict):
            templates = data.get('templates', [])
            print(f"Response type: dict with 'templates' key")
        else:
            templates = data
            print(f"Response type: list")
        
        print(f"Total templates for {brand_name}: {len(templates)}")
        
        # Group by model and grounding mode
        gpt5_templates = []
        gemini_templates = []
        
        for t in templates:
            template_info = {
                'id': t.get('id'),
                'name': t.get('template_name', 'Unknown'),
                'model': t.get('model_name', 'Unknown'),
                'modes': t.get('grounding_modes', []),
                'countries': t.get('countries', []),
                'created': t.get('created_at', 'Unknown')
            }
            
            if 'gpt' in template_info['model'].lower():
                gpt5_templates.append(template_info)
            elif 'gemini' in template_info['model'].lower():
                gemini_templates.append(template_info)
        
        print(f"\nGPT-5 Templates: {len(gpt5_templates)}")
        for t in gpt5_templates:
            print(f"  • ID {t['id']}: {t['name']}")
            print(f"    Model: {t['model']}, Modes: {t['modes']}, Countries: {t['countries']}")
        
        print(f"\nGemini Templates: {len(gemini_templates)}")
        for t in gemini_templates:
            print(f"  • ID {t['id']}: {t['name']}")
            print(f"    Model: {t['model']}, Modes: {t['modes']}, Countries: {t['countries']}")
    else:
        print(f"Error getting templates: {response.status_code}")
        print(response.text[:200])
    
    # 2. Get recent runs from backend
    print("\n2. BACKEND RUNS CHECK")
    print("-" * 40)
    response = requests.get(f"{BASE_URL}/api/prompt-tracking/runs?brand_name={brand_name}&limit=10")
    if response.status_code == 200:
        data = response.json()
        # Handle both dict and list response
        if isinstance(data, dict):
            runs = data.get('runs', [])
            print(f"Response type: dict with 'runs' key")
        else:
            runs = data
            print(f"Response type: list")
        
        print(f"Total recent runs: {len(runs)}")
        
        # Group by status
        completed = []
        running = []
        failed = []
        
        for r in runs:
            run_info = {
                'id': r.get('id'),
                'status': r.get('status', 'unknown'),
                'model': r.get('model_name', 'Unknown'),
                'grounding': r.get('grounding_mode', 'Unknown'),
                'country': r.get('country', 'Unknown'),
                'created': r.get('created_at', 'Unknown'),
                'template_id': r.get('template_id')
            }
            
            if run_info['status'] == 'completed':
                completed.append(run_info)
            elif run_info['status'] == 'running':
                running.append(run_info)
            else:
                failed.append(run_info)
        
        print(f"\nRun Status Distribution:")
        print(f"  ✅ Completed: {len(completed)}")
        print(f"  🔄 Running: {len(running)}")
        print(f"  ❌ Failed: {len(failed)}")
        
        if completed:
            print(f"\nRecent Completed Runs:")
            for r in completed[:5]:
                print(f"  • Run {r['id']}: {r['model']} - {r['grounding']} - {r['country']}")
    else:
        print(f"Error getting runs: {response.status_code}")
    
    # 3. Get a sample result with full details
    print("\n3. SAMPLE RESULT DETAILS")
    print("-" * 40)
    if runs and len(runs) > 0:
        # Get the first completed run
        completed_runs = [r for r in runs if r.get('status') == 'completed']
        if completed_runs:
            sample_run = completed_runs[0]
            run_id = sample_run.get('id')
            
            print(f"Fetching details for Run {run_id}...")
            response = requests.get(f"{BASE_URL}/api/prompt-tracking/results/{run_id}")
            if response.status_code == 200:
                result = response.json()
                
                print(f"\nRun {run_id} Details:")
                print(f"  Template ID: {result.get('template_id')}")
                print(f"  Model: {result.get('model_name')}")
                print(f"  Grounding Mode: {result.get('grounding_mode')}")
                print(f"  Country: {result.get('country')}")
                print(f"  Status: {result.get('status')}")
                print(f"  Created: {result.get('created_at')}")
                
                # Check for brand mention
                print(f"\n  Brand Analysis:")
                print(f"    Mentioned: {result.get('brand_mentioned', False)}")
                print(f"    Confidence: {result.get('confidence_score', 0)}%")
                
                # Check for grounding signals
                if result.get('grounding_signals'):
                    print(f"\n  Grounding Signals: Present")
                    signals = result['grounding_signals']
                    if isinstance(signals, dict):
                        for key, value in list(signals.items())[:3]:
                            print(f"    • {key}: {str(value)[:100]}...")
                
                # Check for response
                response_text = result.get('response', '')
                if response_text:
                    print(f"\n  Response Length: {len(response_text)} characters")
                    print(f"  Response Preview: {response_text[:200]}...")
                else:
                    print(f"\n  ⚠️ No response text found")
                
                # Check for metadata
                if result.get('inference_params'):
                    print(f"\n  Inference Parameters:")
                    params = result['inference_params']
                    if isinstance(params, dict):
                        for key, value in params.items():
                            print(f"    • {key}: {value}")
            else:
                print(f"Error getting result details: {response.status_code}")
    
    # 4. Verify analytics
    print("\n4. ANALYTICS VERIFICATION")
    print("-" * 40)
    response = requests.get(f"{BASE_URL}/api/prompt-tracking/analytics/{brand_name}")
    if response.status_code == 200:
        analytics = response.json()
        
        print(f"Analytics for {brand_name}:")
        print(f"  Total Runs: {analytics.get('total_runs', 0)}")
        print(f"  Overall Mention Rate: {analytics.get('overall_mention_rate', 0):.1f}%")
        print(f"  Average Confidence: {analytics.get('average_confidence', 0):.1f}%")
        
        # By grounding mode
        if analytics.get('by_grounding_mode'):
            print(f"\n  By Grounding Mode:")
            for mode, stats in analytics['by_grounding_mode'].items():
                print(f"    • {mode}: {stats.get('mention_rate', 0):.1f}% mention rate")
        
        # By country
        if analytics.get('by_country'):
            print(f"\n  By Country:")
            for country, stats in analytics['by_country'].items():
                print(f"    • {country}: {stats.get('mention_rate', 0):.1f}% mention rate")
    else:
        print(f"Error getting analytics: {response.status_code}")
    
    # 5. Check system health
    print("\n5. SYSTEM HEALTH CHECK")
    print("-" * 40)
    response = requests.get(f"{BASE_URL}/api/health")
    if response.status_code == 200:
        health = response.json()
        print(f"System Status: {health.get('status', 'unknown')}")
        print(f"Database: {health.get('database', 'unknown')}")
        print(f"Cache: {health.get('cache', 'unknown')}")
        
        if health.get('models'):
            print(f"\nModel Status:")
            for model, status in health['models'].items():
                if isinstance(status, dict):
                    print(f"  • {model}: {status.get('status', 'unknown')}")
                    if status.get('latency_ms'):
                        print(f"    Latency: {status['latency_ms']}ms")
    else:
        print(f"Error getting health: {response.status_code}")

if __name__ == "__main__":
    verify_data()