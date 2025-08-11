import asyncio
from app.api.concordance_analysis import analyze_concordance, ConcordanceRequest
import json

async def test():
    try:
        request = ConcordanceRequest(
            brand_name="AVEA Life",  # Use a real brand
            vendor="openai",
            num_runs=3,
            tracked_phrases=["best longevity supplements"]
        )
        result = await analyze_concordance(request)
        print("Success!")
        
        # Convert to dict for inspection
        result_dict = result.model_dump()
        
        # Print metrics
        print(f"\nMetrics:")
        for k, v in result_dict['metrics'].items():
            print(f"  {k}: {v}")
        
        # Check for comparisons
        print(f"\nTotal comparisons: {len(result_dict['entity_comparisons'])}")
        
        # Show first few comparisons
        print("\nFirst 5 comparisons:")
        for comp in result_dict['entity_comparisons'][:5]:
            print(f"  {comp['entity']}: prompted={comp['prompted_rank']}, embedding={comp['embedding_rank']}")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

asyncio.run(test())