#!/usr/bin/env python3
"""
Quick test to verify Vertex AI is working with new ADC credentials
"""
import asyncio
import sys
import os
sys.stdout.reconfigure(encoding='utf-8')

async def test_vertex_adc():
    print("🧪 Testing Vertex AI with ADC credentials...")
    print(f"📍 ADC File Location: {os.path.expanduser('~')}\\AppData\\Roaming\\gcloud\\application_default_credentials.json")
    
    # Set environment variables manually for this test
    os.environ['GOOGLE_CLOUD_PROJECT'] = 'contestra-ai'
    os.environ['GOOGLE_CLOUD_REGION'] = 'europe-west4'
    os.environ['GOOGLE_IMPERSONATE_SERVICE_ACCOUNT'] = 'vertex-runner@contestra-ai.iam.gserviceaccount.com'
    
    # Check if ADC file exists
    adc_path = os.path.expanduser('~') + "\\AppData\\Roaming\\gcloud\\application_default_credentials.json"
    if os.path.exists(adc_path):
        print("✅ ADC file exists")
        # Show file modification time
        import datetime
        mtime = os.path.getmtime(adc_path)
        mod_time = datetime.datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
        print(f"📅 ADC file modified: {mod_time}")
    else:
        print("❌ ADC file not found!")
        return
    
    # Test environment variables
    print(f"\n🔧 Environment Variables:")
    print(f"   GOOGLE_CLOUD_PROJECT: {os.getenv('GOOGLE_CLOUD_PROJECT')}")
    print(f"   GOOGLE_CLOUD_REGION: {os.getenv('GOOGLE_CLOUD_REGION')}")
    print(f"   GOOGLE_IMPERSONATE_SERVICE_ACCOUNT: {os.getenv('GOOGLE_IMPERSONATE_SERVICE_ACCOUNT')}")
    print(f"   GOOGLE_APPLICATION_CREDENTIALS: {os.getenv('GOOGLE_APPLICATION_CREDENTIALS')}")
    
    try:
        # Try importing and testing the Vertex adapter
        from app.llm.adapters.vertex_genai_adapter import VertexGenAIAdapter
        
        print(f"\n🚀 Testing Vertex GenAI Adapter...")
        
        # Create adapter with explicit parameters
        adapter = VertexGenAIAdapter(
            project="contestra-ai", 
            location="europe-west4"
        )
        
        print("   📡 Adapter created successfully")
        
        # Test simple query without grounding
        print("   🎯 Testing simple query (no grounding)...")
        response = await adapter.analyze_with_gemini(
            prompt="What is 2+2?",
            use_grounding=False,
            model_name="gemini-2.5-pro"
        )
        
        if response and response.get('content'):
            print(f"   ✅ Simple query SUCCESS: {response['content'][:50]}...")
            
            # Test with grounding
            print("   🌐 Testing with grounding...")
            grounded_response = await adapter.analyze_with_gemini(
                prompt="What are the most popular longevity supplements?",
                use_grounding=True,
                model_name="gemini-2.5-pro"
            )
            
            if grounded_response and grounded_response.get('content'):
                print(f"   ✅ Grounding query SUCCESS: {grounded_response['content'][:50]}...")
                
                # Check for citations
                citations = grounded_response.get('citations', [])
                print(f"   📚 Citations found: {len(citations)}")
                
                if citations:
                    print("   🎉 VERTEX AI FULLY OPERATIONAL with ADC!")
                    return True
                else:
                    print("   ⚠️ No citations - grounding might not be working")
                    return False
            else:
                print("   ❌ Grounding query failed")
                return False
        else:
            print("   ❌ Simple query failed")
            return False
            
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        return False

if __name__ == "__main__":
    result = asyncio.run(test_vertex_adc())
    if result:
        print(f"\n🎊 SUCCESS: Vertex AI is working with ADC!")
    else:
        print(f"\n💥 FAILURE: Vertex AI still has issues")