"""
Check database directly for templates and results
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import sqlite3
import json
from datetime import datetime

DB_PATH = "backend/prompt_tracking.db"

def check_database():
    print("=" * 80)
    print("DATABASE DIRECT CHECK")
    print("=" * 80)
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 1. Check templates
    print("\n1. TEMPLATES IN DATABASE")
    print("-" * 40)
    cursor.execute("""
        SELECT id, template_name, model_name, countries, grounding_modes, brand_name, created_at
        FROM prompt_templates
        WHERE brand_name = 'AVEA'
        ORDER BY id DESC
        LIMIT 10
    """)
    templates = cursor.fetchall()
    
    print(f"Found {len(templates)} AVEA templates (showing latest 10):")
    for t in templates:
        print(f"\n  Template ID {t['id']}: {t['template_name']}")
        print(f"    Model: {t['model_name']}")
        print(f"    Countries: {t['countries']}")
        print(f"    Grounding: {t['grounding_modes']}")
        print(f"    Created: {t['created_at']}")
    
    # 2. Check runs
    print("\n2. RUNS IN DATABASE")
    print("-" * 40)
    cursor.execute("""
        SELECT id, template_id, status, created_at, model_name, grounding_mode, country
        FROM prompt_runs
        WHERE template_id IN (SELECT id FROM prompt_templates WHERE brand_name = 'AVEA')
        ORDER BY id DESC
        LIMIT 10
    """)
    runs = cursor.fetchall()
    
    print(f"Found {len(runs)} AVEA runs (showing latest 10):")
    for r in runs:
        print(f"\n  Run ID {r['id']}: Status={r['status']}")
        print(f"    Template: {r['template_id']}")
        print(f"    Model: {r['model_name']}")
        print(f"    Grounding: {r['grounding_mode']}")
        print(f"    Country: {r['country']}")
        print(f"    Created: {r['created_at']}")
    
    # 3. Check results
    print("\n3. RESULTS IN DATABASE")
    print("-" * 40)
    cursor.execute("""
        SELECT pr.id, pr.run_id, pr.response, pr.brand_mentioned, pr.confidence_score,
               pr.grounding_signals, pr.created_at
        FROM prompt_results pr
        JOIN prompt_runs prun ON pr.run_id = prun.id
        WHERE prun.template_id IN (SELECT id FROM prompt_templates WHERE brand_name = 'AVEA')
        ORDER BY pr.id DESC
        LIMIT 5
    """)
    results = cursor.fetchall()
    
    print(f"Found {len(results)} AVEA results (showing latest 5):")
    for res in results:
        print(f"\n  Result ID {res['id']}: Run {res['run_id']}")
        print(f"    Brand Mentioned: {res['brand_mentioned']}")
        print(f"    Confidence: {res['confidence_score']}%")
        response_len = len(res['response']) if res['response'] else 0
        print(f"    Response Length: {response_len} chars")
        if res['grounding_signals']:
            print(f"    Has Grounding Signals: Yes")
        print(f"    Created: {res['created_at']}")
        
        # Show response preview
        if res['response']:
            preview = res['response'][:200] if len(res['response']) > 200 else res['response']
            print(f"    Response Preview: {preview}...")
    
    # 4. Check for orphaned data
    print("\n4. DATA INTEGRITY CHECK")
    print("-" * 40)
    
    # Check runs without results
    cursor.execute("""
        SELECT COUNT(*) as count
        FROM prompt_runs pr
        WHERE pr.status = 'completed'
        AND pr.id NOT IN (SELECT run_id FROM prompt_results)
        AND pr.template_id IN (SELECT id FROM prompt_templates WHERE brand_name = 'AVEA')
    """)
    orphaned = cursor.fetchone()
    print(f"Completed runs without results: {orphaned['count']}")
    
    # Check results without runs
    cursor.execute("""
        SELECT COUNT(*) as count
        FROM prompt_results
        WHERE run_id NOT IN (SELECT id FROM prompt_runs)
    """)
    orphaned = cursor.fetchone()
    print(f"Results without runs: {orphaned['count']}")
    
    # 5. Summary statistics
    print("\n5. SUMMARY STATISTICS")
    print("-" * 40)
    
    cursor.execute("""
        SELECT 
            COUNT(DISTINCT pt.id) as template_count,
            COUNT(DISTINCT pr.id) as run_count,
            COUNT(DISTINCT pres.id) as result_count,
            COUNT(DISTINCT CASE WHEN pr.status = 'completed' THEN pr.id END) as completed_runs,
            COUNT(DISTINCT CASE WHEN pr.status = 'failed' THEN pr.id END) as failed_runs,
            COUNT(DISTINCT CASE WHEN pres.brand_mentioned = 1 THEN pres.id END) as mentions,
            AVG(CASE WHEN pres.confidence_score IS NOT NULL THEN pres.confidence_score END) as avg_confidence
        FROM prompt_templates pt
        LEFT JOIN prompt_runs pr ON pt.id = pr.template_id
        LEFT JOIN prompt_results pres ON pr.id = pres.run_id
        WHERE pt.brand_name = 'AVEA'
    """)
    stats = cursor.fetchone()
    
    print(f"AVEA Statistics:")
    print(f"  Templates: {stats['template_count']}")
    print(f"  Total Runs: {stats['run_count']}")
    print(f"  Results: {stats['result_count']}")
    print(f"  Completed Runs: {stats['completed_runs']}")
    print(f"  Failed Runs: {stats['failed_runs']}")
    print(f"  Brand Mentions: {stats['mentions']}")
    if stats['avg_confidence']:
        print(f"  Avg Confidence: {stats['avg_confidence']:.1f}%")
    
    conn.close()

if __name__ == "__main__":
    check_database()