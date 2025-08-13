#!/usr/bin/env python
"""Test script to debug model_name issue"""

from sqlalchemy import text
from app.database import engine

def test_direct_query():
    """Test direct SQL query to see what's returned"""
    with engine.connect() as conn:
        query = text("""
            SELECT id, brand_name, template_name, model_name 
            FROM prompt_templates 
            WHERE id = 33
        """)
        result = conn.execute(query)
        
        for row in result:
            print(f"Row type: {type(row)}")
            print(f"Row attributes: {dir(row)}")
            print(f"Has model_name attr: {hasattr(row, 'model_name')}")
            
            # Try different access methods
            print("\nAccess methods:")
            try:
                print(f"  row.model_name: {row.model_name}")
            except AttributeError as e:
                print(f"  row.model_name failed: {e}")
            
            try:
                print(f"  row['model_name']: {row['model_name']}")
            except (KeyError, TypeError) as e:
                print(f"  row['model_name'] failed: {e}")
            
            try:
                print(f"  row[3] (by index): {row[3]}")
            except IndexError as e:
                print(f"  row[3] failed: {e}")
            
            # Check mapping
            if hasattr(row, '_mapping'):
                print(f"\nRow mapping: {dict(row._mapping)}")
            
            # Try as tuple
            print(f"\nAs tuple: {tuple(row)}")

if __name__ == "__main__":
    test_direct_query()