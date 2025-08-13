"""
Test Exa with various German queries to see what works
"""

import asyncio
import httpx
from app.config import settings

async def test_exa_german():
    """Test different queries to get good German results"""
    
    if not settings.exa_api_key:
        print("No Exa API key configured")
        return
    
    # Try different queries to get German-specific content
    test_queries = [
        ("longevity supplements", ['dm.de', 'rossmann.de', 'apotheken-umschau.de']),
        ("Nahrungsergänzungsmittel", ['.de']),  # German word for supplements
        ("Apotheke Preise", ['.de']),  # Pharmacy prices in German
        ("dm Rossmann Angebote", None),  # German retailers
        ("Deutschland Gesundheit", None),  # Germany health
    ]
    
    async with httpx.AsyncClient() as client:
        for query, domains in test_queries:
            print("\n" + "="*60)
            print(f"QUERY: {query}")
            if domains:
                print(f"DOMAINS: {domains}")
            print("="*60)
            
            request_json = {
                'query': query,
                'num_results': 5,
                'use_autoprompt': True,
                'type': 'auto',
                'contents': {
                    'text': True,
                    'highlights': True
                }
            }
            
            if domains:
                request_json['include_domains'] = domains
            
            response = await client.post(
                'https://api.exa.ai/search',
                headers={'x-api-key': settings.exa_api_key},
                json=request_json
            )
            
            if response.status_code == 200:
                data = response.json()
                
                for i, result in enumerate(data.get('results', [])[:3], 1):
                    print(f"\n--- Result {i} ---")
                    url = result.get('url', 'No URL')
                    print(f"URL: {url}")
                    
                    # Show content
                    if result.get('text'):
                        # Clean up encoding issues
                        text = result['text'][:300]
                        text = text.encode('ascii', 'ignore').decode('ascii')
                        print(f"Text: {text}...")
                    elif result.get('highlights'):
                        highlights = ' ... '.join(result['highlights'][:2])
                        highlights = highlights.encode('ascii', 'ignore').decode('ascii')
                        print(f"Highlights: {highlights}")
                    else:
                        print("No content")
                        
            else:
                print(f"Error: {response.status_code}")

if __name__ == "__main__":
    asyncio.run(test_exa_german())