"""
Test Exa.ai integration for evidence pack building
"""

import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Check if Exa key is configured
exa_key = os.getenv('EXA_API_KEY')
if exa_key:
    print(f"[OK] Exa API key found: {exa_key[:10]}...")
else:
    print("[ERROR] No EXA_API_KEY found in .env file")
    print("Please add: EXA_API_KEY=your_key_here to backend/.env")
    exit(1)

from app.services.evidence_pack_builder import evidence_pack_builder

async def test_exa():
    print("\n" + "="*60)
    print("TESTING EXA.AI INTEGRATION")
    print("="*60)
    
    # Test query
    query = "What are the best longevity supplements?"
    
    # Test for different countries
    for country in ['CH', 'US', 'DE']:
        print(f"\n[{country}] Fetching evidence pack...")
        print("-" * 40)
        
        try:
            evidence = await evidence_pack_builder.build_evidence_pack(
                query,
                country,
                max_snippets=3,
                max_tokens=600
            )
            
            if evidence:
                print("[SUCCESS] Evidence pack generated successfully!")
                print("\nEvidence preview:")
                print(evidence[:500])
                if len(evidence) > 500:
                    print("... [truncated]")
                
                # Check for country-specific markers
                markers = []
                if country == 'CH':
                    if 'CHF' in evidence or 'Swiss' in evidence or 'Migros' in evidence:
                        markers.append("Swiss context detected")
                elif country == 'US':
                    if 'FDA' in evidence or '$' in evidence or 'CVS' in evidence:
                        markers.append("US context detected")
                elif country == 'DE':
                    if '€' in evidence or 'EUR' in evidence or 'Apotheke' in evidence:
                        markers.append("German context detected")
                
                if markers:
                    print(f"\n[OK] Location markers: {', '.join(markers)}")
                else:
                    print("\n[WARNING] No clear location markers found (may need to check actual search results)")
            else:
                print("[ERROR] No evidence pack generated")
                
        except Exception as e:
            print(f"[ERROR] Error: {str(e)}")
            if "401" in str(e):
                print("   → API key might be invalid")
            elif "429" in str(e):
                print("   → Rate limit exceeded")
            elif "402" in str(e):
                print("   → Payment required (check your Exa account)")
    
    print("\n" + "="*60)
    print("TEST COMPLETE")
    print("="*60)
    print("\nIf successful, your templates will now use REAL search results")
    print("instead of mock data when you run them!")

if __name__ == "__main__":
    asyncio.run(test_exa())