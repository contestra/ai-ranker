import httpx
import asyncio

async def test_shopify():
    url = "https://avea-life.com"
    headers = {
        'User-Agent': 'Mozilla/5.0 (compatible; AI-Ranker-Validator/1.0)'
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers, timeout=10.0, follow_redirects=True)
        
        print(f"Status: {response.status_code}")
        print(f"\nHeaders:")
        for key, value in response.headers.items():
            if 'shopify' in key.lower() or 'shopify' in value.lower() or key.lower() in ['x-shopid', 'powered-by']:
                print(f"  {key}: {value}")
        
        html = response.text[:5000]
        print(f"\nShopify references in HTML: {html.lower().count('shopify')}")
        print(f"CDN.shopify.com references: {html.lower().count('cdn.shopify.com')}")
        
        # Check indicators
        indicators = sum([
            'myshopify.com' in html.lower(),
            'shopify.theme' in html.lower(),
            'shopify.shop' in html.lower(),
            'shopify-assets' in html.lower(),
            html.lower().count('cdn.shopify.com') > 3,
            'x-shopify-stage' in [h.lower() for h in response.headers.keys()],
            'x-shopid' in [h.lower() for h in response.headers.keys()],
            response.headers.get('powered-by', '').lower() == 'shopify'
        ])
        
        print(f"\nShopify indicators count: {indicators}")
        print(f"Is Shopify? {indicators >= 2}")

asyncio.run(test_shopify())