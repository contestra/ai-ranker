"""
Logical test to determine the exact filtering pattern for GPT-5
Tests various combinations to isolate the trigger
"""

import asyncio
from openai import AsyncOpenAI

async def test_trusted_pattern():
    client = AsyncOpenAI()
    
    # Logical test matrix:
    # 1. Test "most trusted" across categories
    # 2. Test "best" across categories  
    # 3. Test other superlatives
    # 4. Test direct listings
    
    test_cases = [
        # GROUP 1: "most trusted" + different categories
        ('What are the most trusted longevity supplement brands?', 'trusted+supplement'),
        ('What are the most trusted vitamin brands?', 'trusted+vitamin'),
        ('What are the most trusted ecommerce companies?', 'trusted+ecommerce'),
        ('What are the most trusted car brands?', 'trusted+car'),
        ('What are the most trusted tech companies?', 'trusted+tech'),
        ('What are the most trusted fashion brands?', 'trusted+fashion'),
        
        # GROUP 2: "best" + same categories
        ('What are the best longevity supplement brands?', 'best+supplement'),
        ('What are the best vitamin brands?', 'best+vitamin'),
        ('What are the best ecommerce companies?', 'best+ecommerce'),
        ('What are the best car brands?', 'best+car'),
        
        # GROUP 3: Other recommendation language
        ('What are recommended longevity supplements?', 'recommended+supplement'),
        ('What are popular longevity supplement brands?', 'popular+supplement'),
        ('What are leading longevity supplement brands?', 'leading+supplement'),
        
        # GROUP 4: Direct factual listings (control)
        ('List longevity supplement brands', 'list+supplement'),
        ('List ecommerce companies', 'list+ecommerce'),
        
        # GROUP 5: Test "trusted" alone
        ('Name trusted brands', 'trusted+generic'),
        ('What are trusted companies?', 'trusted+generic'),
    ]
    
    print('GPT-5 Filtering Pattern Analysis')
    print('=' * 80)
    print(f"{'Test Type':<25} {'Status':<10} {'Length':<8} {'Prompt':<40}")
    print('-' * 80)
    
    results = []
    
    for prompt, test_type in test_cases:
        try:
            response = await client.chat.completions.create(
                model='gpt-5',
                messages=[{'role': 'user', 'content': prompt}],
                temperature=1.0,
                max_completion_tokens=2000
            )
            
            choice = response.choices[0]
            content = choice.message.content or ''
            
            # Analyze result
            status = 'OK' if content else 'FILTERED'
            length = len(content)
            
            results.append({
                'type': test_type,
                'prompt': prompt[:40],
                'status': status,
                'length': length,
                'finish_reason': choice.finish_reason
            })
            
            print(f"{test_type:<25} {status:<10} {length:<8} {prompt[:40]}")
            
        except Exception as e:
            print(f"{test_type:<25} ERROR      0        {prompt[:40]}")
            results.append({
                'type': test_type,
                'prompt': prompt[:40],
                'status': 'ERROR',
                'error': str(e)
            })
    
    # Analyze patterns
    print('\n' + '=' * 80)
    print('PATTERN ANALYSIS:')
    print('-' * 80)
    
    # Group results by status
    filtered = [r for r in results if r['status'] == 'FILTERED']
    working = [r for r in results if r['status'] == 'OK']
    
    print(f'\nFILTERED ({len(filtered)} prompts):')
    filtered_types = set(r['type'].split('+')[0] for r in filtered)
    filtered_categories = set(r['type'].split('+')[1] for r in filtered if '+' in r['type'])
    print(f'  Keywords that trigger filter: {", ".join(filtered_types)}')
    print(f'  Categories affected: {", ".join(filtered_categories)}')
    
    print(f'\nWORKING ({len(working)} prompts):')
    working_types = set(r['type'].split('+')[0] for r in working)
    working_categories = set(r['type'].split('+')[1] for r in working if '+' in r['type'])
    print(f'  Keywords that work: {", ".join(working_types)}')
    print(f'  Categories that work: {", ".join(working_categories)}')
    
    # Find the pattern
    print('\n' + '=' * 80)
    print('CONCLUSION:')
    
    # Check if filtering is category-specific or keyword-specific
    trusted_health = [r for r in results if 'trusted' in r['type'] and ('supplement' in r['type'] or 'vitamin' in r['type'])]
    trusted_other = [r for r in results if 'trusted' in r['type'] and 'supplement' not in r['type'] and 'vitamin' not in r['type']]
    
    trusted_health_filtered = sum(1 for r in trusted_health if r['status'] == 'FILTERED')
    trusted_other_filtered = sum(1 for r in trusted_other if r['status'] == 'FILTERED')
    
    if trusted_health_filtered > 0 and trusted_other_filtered == 0:
        print('Filter is CATEGORY-SPECIFIC: "trusted" only filtered for health/supplement topics')
    elif trusted_health_filtered > 0 and trusted_other_filtered > 0:
        print('Filter is KEYWORD-BASED: "trusted" is filtered regardless of category')
    else:
        print('No clear pattern detected - need more tests')

if __name__ == "__main__":
    asyncio.run(test_trusted_pattern())