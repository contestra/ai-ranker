"""Isolate exactly where the leak happens in the API flow"""

import asyncio
import sys
from sqlalchemy import text
from app.database import engine
from app.llm.langchain_adapter import LangChainAdapter
from app.services.als import als_service

async def test_with_database():
    """Test if database operations cause the leak"""
    
    print("\n" + "="*80)
    print("TEST: With Database Operations (like API)")
    print("="*80)
    
    # Simulate what the API does
    template_id = 26
    brand_name = "AVEA"
    model_name = "gemini"
    country = "DE"
    grounding_mode = "none"
    
    # Create a run record (like API does)
    with engine.begin() as conn:
        run_query = text("""
            INSERT INTO prompt_runs 
            (template_id, brand_name, model_name, country_code, grounding_mode, status, started_at)
            VALUES (:template_id, :brand, :model, :country, :grounding, 'running', datetime('now'))
            RETURNING id
        """)
        
        run_result = conn.execute(run_query, {
            "template_id": template_id,
            "brand": brand_name,
            "model": model_name,
            "country": country,  # DE stored in database
            "grounding": grounding_mode
        })
        run_id = run_result.fetchone()[0]
        print(f"Created run ID: {run_id} with country_code='{country}'")
    
    # Now call Gemini (like API does)
    adapter = LangChainAdapter()
    ambient_block = als_service.build_als_block(country)
    
    result = await adapter.analyze_with_gemini(
        'List the top 3 longevity supplements',
        use_grounding=False,
        model_name='gemini-2.5-pro',
        temperature=0.0,
        seed=42,
        context=ambient_block
    )
    
    response_text = result['content']
    
    # Save to database (like API does)
    with engine.begin() as conn:
        result_query = text("""
            INSERT INTO prompt_results 
            (run_id, prompt_text, model_response, brand_mentioned, mention_count)
            VALUES (:run_id, :prompt, :response, :mentioned, :count)
        """)
        
        conn.execute(result_query, {
            "run_id": run_id,
            "prompt": 'List the top 3 longevity supplements',
            "response": response_text[:1000],  # Truncate for DB
            "mentioned": False,
            "count": 0
        })
        
        # Update run status
        update_query = text("""
            UPDATE prompt_runs 
            SET status = 'completed', completed_at = datetime('now')
            WHERE id = :id
        """)
        conn.execute(update_query, {"id": run_id})
    
    # Check for leak
    if 'DE' in response_text or 'Germany' in response_text or 'location context' in response_text:
        print("\n[LEAK] With database operations: DE/Germany found!")
        # Show the leaking part
        for line in response_text.split('\n')[:3]:
            if 'DE' in line or 'Germany' in line:
                print(f"   -> {line[:100]}")
    else:
        print("\n[OK] With database operations: No leak")
    
    print(f"\nResponse preview: {response_text[:200]}...")
    
    return response_text

async def test_without_database():
    """Test without any database operations"""
    
    print("\n" + "="*80)
    print("TEST: Without Database (direct)")
    print("="*80)
    
    country = "DE"  # Same country
    
    # Direct call without any database
    adapter = LangChainAdapter()
    ambient_block = als_service.build_als_block(country)
    
    result = await adapter.analyze_with_gemini(
        'List the top 3 longevity supplements',
        use_grounding=False,
        model_name='gemini-2.5-pro',
        temperature=0.0,
        seed=42,
        context=ambient_block
    )
    
    response_text = result['content']
    
    # Check for leak
    if 'DE' in response_text or 'Germany' in response_text or 'location context' in response_text:
        print("\n[LEAK] Without database: DE/Germany found!")
    else:
        print("\n[OK] Without database: No leak")
    
    print(f"\nResponse preview: {response_text[:200]}...")
    
    return response_text

if __name__ == "__main__":
    # Test both scenarios
    asyncio.run(test_with_database())
    print("\n" + "="*60)
    asyncio.run(test_without_database())
    
    print("\n" + "="*80)
    print("CONCLUSION")
    print("="*80)
    print("If database test leaks but direct doesn't, the issue is database-related")
    print("If both work fine, the leak is elsewhere in prompt_tracking.py")