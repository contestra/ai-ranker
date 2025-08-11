import asyncio
from app.api.concordance_analysis import analyze_concordance, ConcordanceRequest

async def test():
    try:
        request = ConcordanceRequest(
            brand_name="TestBrand",
            vendor="openai",
            num_runs=3,
            tracked_phrases=[]
        )
        result = await analyze_concordance(request)
        print("Success!")
        print(f"Metrics: {result.metrics}")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

asyncio.run(test())