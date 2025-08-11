"""
Test AVEA disambiguation with website verification
"""
import asyncio
import httpx
from bs4 import BeautifulSoup

async def test_website_fetch():
    """Test fetching and analyzing AVEA Life website"""
    
    domain = "https://www.avea-life.com"
    
    print(f"Fetching {domain}...")
    
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            response = await client.get(domain)
            
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                # Parse HTML
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Extract title
                title = soup.find('title')
                title_text = title.text.strip() if title else ""
                print(f"Title: {title_text}")
                
                # Meta description
                meta_desc = soup.find('meta', attrs={'name': 'description'})
                description = meta_desc.get('content', '') if meta_desc else ""
                print(f"Description: {description}")
                
                # Look for keywords
                text_content = soup.get_text().lower()[:3000]
                
                # Check for health/wellness keywords
                health_keywords = ["supplement", "health", "wellness", "nutrition", "vitamin", "longevity", "nmn", "nad+", "collagen"]
                health_count = sum(1 for kw in health_keywords if kw in text_content)
                
                # Check for telecom keywords
                telecom_keywords = ["telecom", "mobile", "carrier", "network", "5g", "4g", "sim", "roaming", "operator"]
                telecom_count = sum(1 for kw in telecom_keywords if kw in text_content)
                
                print(f"\nIndustry detection:")
                print(f"  Health/Wellness keywords found: {health_count}")
                print(f"  Telecommunications keywords found: {telecom_count}")
                
                if health_count >= 2:
                    print(f"  => Detected as: health/wellness")
                elif telecom_count >= 2:
                    print(f"  => Detected as: telecommunications")
                else:
                    print(f"  => Industry unclear")
                
                # Show sample content
                print(f"\nFirst 500 chars of text content:")
                print(text_content[:500])
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_website_fetch())