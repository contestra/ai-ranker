"""
Direct test of Exa API to debug search quality
"""

import asyncio
import httpx
from app.config import settings

async def test_exa_directly():
    """Test Exa API directly to see raw results"""
    
    if not settings.exa_api_key:
        print("No Exa API key configured")
        return
    
    queries = [
        # Try different query formulations
        "longevity supplement brands Germany",
        "NMN NAD resveratrol supplements Deutschland",
        "anti aging supplements German market",
        "Nahrungsergänzungsmittel Langlebigkeit Deutschland"
    ]
    
    for query in queries:
        print("\n" + "="*60)
        print(f"QUERY: {query}")
        print("="*60)
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                'https://api.exa.ai/search',
                headers={'x-api-key': settings.exa_api_key},
                json={
                    'query': query,
                    'num_results': 5,
                    'use_autoprompt': True,
                    'type': 'auto',
                    'contents': {
                        'text': True,
                        'highlights': True
                    }
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                
                print(f"\nFound {len(data.get('results', []))} results")
                
                for i, result in enumerate(data.get('results', [])[:3], 1):
                    print(f"\n--- Result {i} ---")
                    # Sanitize for Windows console
                    title = result.get('title', 'No title').encode('ascii', 'ignore').decode('ascii')
                    url = result.get('url', 'No URL')
                    print(f"Title: {title}")
                    print(f"URL: {url}")
                    
                    # Show highlights or text snippet
                    if result.get('highlights'):
                        highlights = ' ... '.join(result['highlights'][:2])
                        highlights = highlights.encode('ascii', 'ignore').decode('ascii')
                        print(f"Highlights: {highlights}")
                    elif result.get('text'):
                        text = result['text'][:200].encode('ascii', 'ignore').decode('ascii')
                        print(f"Text: {text}...")
                    else:
                        print("No content available")
                        
            else:
                print(f"Error: {response.status_code}")
                print(f"Response: {response.text}")

if __name__ == "__main__":
    asyncio.run(test_exa_directly())