"""
Backfill script to populate new columns from existing data.
Uses model registry for accurate provider detection.
"""

import sys
import os
import io

# Configure stdout for UTF-8
sys.stdout.reconfigure(encoding='utf-8')

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sqlite3
import json
from typing import Dict, Any, List, Optional

# Import from app
from app.llm.model_registry import resolve_model
from app.services.canonical import canonicalize, build_canonical_object

def get_provider(model_name: str) -> str:
    """Use model registry for accurate provider detection."""
    try:
        return resolve_model(model_name).provider
    except Exception:
        # Fallback for unknown models
        model_lower = model_name.lower()
        if 'gpt' in model_lower:
            return 'openai'
        elif 'gemini' in model_lower:
            return 'vertex'
        return 'unknown'

def normalize_grounding_mode(mode: Optional[str]) -> str:
    """Map old grounding modes to canonical values."""
    if not mode:
        return 'not_grounded'
        
    mode_map = {
        'off': 'not_grounded',
        'none': 'not_grounded',
        'ungrounded': 'not_grounded',
        'preferred': 'preferred',
        'auto': 'preferred',
        'web': 'preferred',
        'required': 'enforced',
        'enforced': 'enforced'
    }
    return mode_map.get(mode.lower(), 'not_grounded')

def parse_json_field(value: Any) -> Any:
    """Parse JSON string if needed."""
    if isinstance(value, str):
        try:
            return json.loads(value)
        except:
            return value
    return value

def backfill():
    """Run the backfill migration."""
    conn = sqlite3.connect('ai_ranker.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    print("Starting backfill migration...")
    
    # 1. Backfill templates
    print("\n1. Backfilling prompt_templates...")
    cursor.execute("SELECT * FROM prompt_templates WHERE provider IS NULL")
    templates = cursor.fetchall()
    
    updated_count = 0
    for template in templates:
        template_dict = dict(template)
        provider = get_provider(template_dict['model_name'])
        
        # Parse countries and modes
        countries = parse_json_field(template_dict.get('countries', '["NONE"]'))
        if not countries:
            countries = ["NONE"]
        countries = sorted(countries)
        
        modes = parse_json_field(template_dict.get('grounding_modes', '["not_grounded"]'))
        if not modes:
            modes = ["not_grounded"]
        # Normalize modes
        modes = sorted([normalize_grounding_mode(m) for m in modes])
        
        # Determine ALS mode from parsed countries (not string comparison)
        als_mode = 'off' if countries == ["NONE"] else 'implicit'
        
        # Build canonical object
        canonical_obj = build_canonical_object(
            provider=provider,
            model=template_dict['model_name'],
            prompt_text=template_dict.get('prompt_text', ''),
            countries=countries,
            grounding_modes=modes
        )
        
        # Generate canonical JSON and hash
        canonical_json, template_sha256 = canonicalize(canonical_obj)
        
        # Determine system params
        if 'gpt-5' in template_dict['model_name'].lower():
            max_tokens = 2000
            timeout_ms = 60000
        else:
            max_tokens = 8192
            timeout_ms = 30000
        
        # Determine grounding binding note
        if provider == 'openai':
            grounding_note = "openai:web_search auto/required"
        else:
            grounding_note = "vertex:google_search pass-1; two-step for JSON"
        
        # Update normalized modes back to template
        modes_json = json.dumps(modes)
            
        cursor.execute("""
            UPDATE prompt_templates 
            SET provider = ?,
                system_temperature = 0.0,
                system_seed = 42,
                system_top_p = 1.0,
                max_output_tokens = ?,
                request_timeout_ms = ?,
                als_mode = ?,
                als_hash = 'als_v3_2025-08',
                safety_profile = 'standard',
                max_retries = 2,
                grounding_binding_note = ?,
                canonical_json = ?,
                template_sha256 = ?,
                grounding_modes = ?
            WHERE id = ?
        """, (
            provider, max_tokens, timeout_ms,
            als_mode,  # Use the parsed value
            grounding_note, canonical_json, template_sha256,
            modes_json,  # Update with normalized modes
            template['id']
        ))
        updated_count += 1
    
    print(f"  ✓ Updated {updated_count} templates")
    
    # 2. Backfill runs
    print("\n2. Backfilling prompt_runs...")
    cursor.execute("SELECT * FROM prompt_runs WHERE provider IS NULL")
    runs = cursor.fetchall()
    
    updated_count = 0
    for run in runs:
        run_dict = dict(run)
        provider = get_provider(run_dict['model_name'])
        
        # Handle NULL grounding_mode
        grounding_mode = normalize_grounding_mode(run_dict.get('grounding_mode'))
        
        # Determine response API
        if provider == 'vertex':
            response_api = 'vertex_genai'
        elif 'gpt-5' in run_dict['model_name'].lower():
            response_api = 'responses_http'
        else:
            response_api = 'sdk_chat'
        
        # Determine tool_choice_sent
        tool_choice = None
        if provider == 'openai':
            if grounding_mode == 'enforced':
                tool_choice = 'required'
            elif grounding_mode == 'preferred':
                tool_choice = 'auto'
            else:
                tool_choice = 'off'
                
        cursor.execute("""
            UPDATE prompt_runs
            SET provider = ?,
                grounding_mode_requested = ?,
                response_api = ?,
                tool_choice_sent = ?,
                system_temperature = 0.0,
                system_seed = 42,
                system_top_p = 1.0,
                max_output_tokens = ?
            WHERE id = ?
        """, (
            provider, grounding_mode, response_api, tool_choice,
            2000 if 'gpt-5' in run_dict['model_name'].lower() else 8192,
            run_dict['id']
        ))
        updated_count += 1
    
    print(f"  ✓ Updated {updated_count} runs")
    
    # 3. Update grounding_mode in runs table to canonical
    print("\n3. Normalizing grounding_mode in prompt_runs...")
    cursor.execute("SELECT id, grounding_mode FROM prompt_runs WHERE grounding_mode IS NOT NULL")
    runs_modes = cursor.fetchall()
    
    updated_count = 0
    for run in runs_modes:
        normalized = normalize_grounding_mode(run['grounding_mode'])
        if normalized != run['grounding_mode']:
            cursor.execute("""
                UPDATE prompt_runs
                SET grounding_mode = ?
                WHERE id = ?
            """, (normalized, run['id']))
            updated_count += 1
    
    print(f"  ✓ Normalized {updated_count} run grounding modes")
    
    # 4. Count citations in results
    print("\n4. Counting citations in prompt_results...")
    cursor.execute("SELECT id, citations FROM prompt_results WHERE citations IS NOT NULL")
    results = cursor.fetchall()
    
    updated_count = 0
    for result in results:
        citations = parse_json_field(result['citations'])
        if isinstance(citations, list):
            count = len(citations)
        else:
            count = 0
            
        cursor.execute("""
            UPDATE prompt_results
            SET citations_count = ?
            WHERE id = ?
        """, (count, result['id']))
        updated_count += 1
    
    print(f"  ✓ Updated citation counts for {updated_count} results")
    
    conn.commit()
    conn.close()
    print("\n✅ Backfill migration complete!")

if __name__ == "__main__":
    backfill()