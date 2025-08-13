"""Debug GPT-5 API issue - trace where response gets lost"""
import asyncio
from app.llm.langchain_adapter import LangChainAdapter
from app.api.prompt_tracking import run_prompt
from app.database import engine
from sqlalchemy import text
import json

async def test_direct_adapter():
    """Test 1: Direct adapter call (this works)"""
    print("\n" + "="*60)
    print("TEST 1: Direct LangChainAdapter call")
    print("="*60)
    
    adapter = LangChainAdapter()
    result = await adapter.analyze_with_gpt4(
        prompt="What do you know about AVEA?",
        model_name="gpt-5",
        temperature=0.0,
        seed=42
    )
    
    print(f"[OK] Response length: {len(result.get('content', ''))}")
    print(f"[OK] Has content: {bool(result.get('content'))}")
    print(f"[OK] First 100 chars: {result.get('content', '')[:100]}")
    return result

async def test_prompt_tracking_logic():
    """Test 2: Simulate the prompt_tracking.py logic"""
    print("\n" + "="*60)
    print("TEST 2: Simulating prompt_tracking.py logic")
    print("="*60)
    
    adapter = LangChainAdapter()
    
    # Simulate the exact flow from prompt_tracking.py
    request_model_name = "gpt-5"
    grounding_mode = "none"
    prompt_text = "What do you know about AVEA?"
    temperature = 0.0
    seed = 42
    context_message = None
    
    # Prepare prompt based on mode (from prompt_tracking.py)
    full_prompt = f"""Based only on your training data (do not search the web):

{prompt_text}"""
    
    print(f"Calling analyze_with_gpt4 with:")
    print(f"  - model_name: {request_model_name}")
    print(f"  - temperature: {temperature}")
    print(f"  - seed: {seed}")
    print(f"  - context: {context_message}")
    
    # Call exactly as prompt_tracking.py does
    response_data = await adapter.analyze_with_gpt4(
        full_prompt,
        model_name=request_model_name,
        temperature=temperature,
        seed=seed,
        context=context_message
    )
    
    print(f"\nResponse data type: {type(response_data)}")
    print(f"Response data keys: {response_data.keys() if isinstance(response_data, dict) else 'Not a dict'}")
    
    # Extract response content exactly as prompt_tracking.py does
    response = response_data.get("content", "") if isinstance(response_data, dict) else str(response_data)
    
    print(f"[OK] Extracted response length: {len(response)}")
    print(f"[OK] Response is empty: {not response or len(response.strip()) == 0}")
    print(f"[OK] First 100 chars: {response[:100] if response else 'EMPTY'}")
    
    return response

async def test_database_save():
    """Test 3: Save to database like prompt_tracking.py"""
    print("\n" + "="*60)
    print("TEST 3: Database save operation")
    print("="*60)
    
    adapter = LangChainAdapter()
    
    # Get a response
    response_data = await adapter.analyze_with_gpt4(
        "What do you know about AVEA?",
        model_name="gpt-5",
        temperature=0.0,
        seed=42
    )
    
    response = response_data.get("content", "") if isinstance(response_data, dict) else str(response_data)
    
    # Create a test run
    with engine.begin() as conn:
        run_query = text("""
            INSERT INTO prompt_runs 
            (template_id, brand_name, model_name, country_code, grounding_mode, status, started_at)
            VALUES (1, 'TEST_AVEA', 'gpt-5', 'NONE', 'none', 'running', datetime('now'))
            RETURNING id
        """)
        
        run_result = conn.execute(run_query)
        run_id = run_result.fetchone()[0]
        print(f"Created test run ID: {run_id}")
        
        # Save the result
        result_query = text("""
            INSERT INTO prompt_results 
            (run_id, prompt_text, model_response, brand_mentioned, mention_count, 
             competitors_mentioned, confidence_score)
            VALUES (:run_id, :prompt, :response, :mentioned, :count, 
                    :competitors, :confidence)
            RETURNING id
        """)
        
        conn.execute(result_query, {
            "run_id": run_id,
            "prompt": "What do you know about AVEA?",
            "response": response,
            "mentioned": True,
            "count": 1,
            "competitors": json.dumps([]),
            "confidence": 0.8
        })
        
        # Update run status
        update_query = text("""
            UPDATE prompt_runs 
            SET status = 'completed', completed_at = datetime('now')
            WHERE id = :id
        """)
        conn.execute(update_query, {"id": run_id})
        
        print(f"[OK] Saved response to database")
        print(f"[OK] Response length saved: {len(response)}")
        
        # Read it back
        check_query = text("SELECT model_response FROM prompt_results WHERE run_id = :id")
        check_result = conn.execute(check_query, {"id": run_id}).fetchone()
        saved_response = check_result[0] if check_result else None
        
        print(f"[OK] Response length retrieved: {len(saved_response) if saved_response else 0}")
        print(f"[OK] Matches original: {saved_response == response}")
    
    return run_id

async def main():
    print("GPT-5 API Debug Test")
    print("====================")
    
    # Test 1: Direct adapter (should work)
    result1 = await test_direct_adapter()
    
    # Test 2: Prompt tracking logic (where it might fail)
    result2 = await test_prompt_tracking_logic()
    
    # Test 3: Database save
    run_id = await test_database_save()
    
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Test 1 (Direct): {'PASS' if result1.get('content') else 'FAIL'}")
    print(f"Test 2 (API Logic): {'PASS' if result2 else 'FAIL'}")
    print(f"Test 3 (Database): {'PASS' if run_id else 'FAIL'}")

if __name__ == "__main__":
    asyncio.run(main())