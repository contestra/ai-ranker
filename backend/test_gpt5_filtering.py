"""
Comprehensive GPT-5 content filtering analysis
Tests various longevity/supplement prompts to understand filtering patterns
"""

import asyncio
from openai import AsyncOpenAI
import json

async def comprehensive_test():
    client = AsyncOpenAI()
    
    # Test various longevity/supplement related prompts
    test_prompts = [
        # Direct longevity supplement prompts
        'List the top 10 longevity supplement brands',
        'What are the best longevity supplements?',
        'Name leading longevity supplement companies',
        'Which companies make anti-aging supplements?',
        
        # Variations without 'supplement'
        'List the top 10 longevity companies',
        'What are the best longevity products?',
        'Name leading anti-aging brands',
        'Which companies focus on longevity?',
        
        # With 'trusted' keyword
        'What are the most trusted longevity supplement brands?',
        'List trusted supplement companies',
        'Name trusted longevity brands',
        
        # Specific brand queries
        'What is AVEA?',
        'Tell me about AVEA supplements',
        'What does AVEA Life sell?',
        
        # General health/wellness
        'List health and wellness brands',
        'What are popular wellness companies?',
        'Name vitamin manufacturers',
        
        # Control prompts (should work)
        'List the top 10 car brands',
        'What are the best tech companies?'
    ]
    
    results = []
    for prompt in test_prompts:
        print(f"Testing: {prompt[:40]}...", end=" ")
        try:
            response = await client.chat.completions.create(
                model='gpt-5',
                messages=[{'role': 'user', 'content': prompt}],
                temperature=1.0,
                max_completion_tokens=2000
            )
            
            choice = response.choices[0]
            content = choice.message.content or ''
            finish_reason = choice.finish_reason
            
            # Determine if content was filtered
            filtered = (finish_reason == 'content_filter' or 
                       (finish_reason == 'length' and len(content.strip()) == 0))
            
            results.append({
                'prompt': prompt[:50],
                'content_length': len(content),
                'finish_reason': finish_reason,
                'filtered': filtered,
                'tokens_used': response.usage.completion_tokens if response.usage else 0
            })
            
            print("✓" if not filtered else "✗")
            
        except Exception as e:
            results.append({
                'prompt': prompt[:50],
                'error': str(e)[:50]
            })
            print("ERROR")
    
    # Print results in a table format
    print('\n' + '=' * 100)
    print('GPT-5 Content Filtering Analysis Results')
    print('=' * 100)
    print(f"{'Prompt':<50} {'Length':<8} {'Finish':<12} {'Tokens':<8} {'Status':<10}")
    print('-' * 100)
    
    for r in results:
        if 'error' in r:
            print(f"{r['prompt']:<50} ERROR: {r['error']}")
        else:
            status = 'FILTERED' if r['filtered'] else 'OK'
            print(f"{r['prompt']:<50} {r['content_length']:<8} {r['finish_reason']:<12} {r['tokens_used']:<8} {status:<10}")
    
    # Analyze patterns
    print('\n' + '=' * 100)
    print('Pattern Analysis:')
    
    filtered_prompts = [r['prompt'] for r in results if r.get('filtered')]
    ok_prompts = [r['prompt'] for r in results if not r.get('filtered') and 'error' not in r]
    
    print(f'\nFiltered ({len(filtered_prompts)} prompts):')
    for p in filtered_prompts:
        print(f'  ✗ {p}')
    
    print(f'\nWorking ({len(ok_prompts)} prompts):')
    for p in ok_prompts:
        print(f'  ✓ {p}')
    
    # Identify patterns
    print('\n' + '=' * 100)
    print('Key Findings:')
    
    # Check for common words in filtered prompts
    filtered_words = set()
    for p in filtered_prompts:
        filtered_words.update(p.lower().split())
    
    ok_words = set()
    for p in ok_prompts:
        ok_words.update(p.lower().split())
    
    # Words that appear in filtered but not in OK
    problem_words = filtered_words - ok_words
    print(f'\nPotential trigger words: {", ".join(sorted(problem_words)[:10])}')
    
    return results

if __name__ == "__main__":
    asyncio.run(comprehensive_test())