"""
Prompt hashing utilities for integrity checking and deduplication.
Ensures prompts haven't been modified between creation and execution.
"""

import hashlib
from typing import Optional

def calculate_prompt_hash(prompt_text: str) -> str:
    """
    Calculate SHA256 hash of prompt text for integrity checking.
    
    Args:
        prompt_text: The prompt text to hash
        
    Returns:
        64-character hex string of SHA256 hash
        
    Note:
        - Uses UTF-8 encoding consistently
        - Normalizes line endings to \n before hashing
        - Strips trailing whitespace to avoid false mismatches
    """
    if not prompt_text:
        return hashlib.sha256(b'').hexdigest()
    
    # Normalize the prompt for consistent hashing
    normalized = prompt_text.strip()
    # Replace Windows line endings with Unix
    normalized = normalized.replace('\r\n', '\n')
    # Replace Mac line endings with Unix
    normalized = normalized.replace('\r', '\n')
    
    # Calculate hash
    hash_obj = hashlib.sha256(normalized.encode('utf-8'))
    return hash_obj.hexdigest()

def verify_prompt_integrity(
    original_hash: str, 
    current_prompt: str
) -> tuple[bool, Optional[str]]:
    """
    Verify that a prompt hasn't been modified.
    
    Args:
        original_hash: The stored hash of the original prompt
        current_prompt: The current prompt text to verify
        
    Returns:
        Tuple of (is_valid, current_hash)
        - is_valid: True if prompt matches original hash
        - current_hash: The hash of the current prompt
    """
    current_hash = calculate_prompt_hash(current_prompt)
    is_valid = (original_hash == current_hash)
    return is_valid, current_hash

def detect_prompt_modification(
    template_hash: Optional[str],
    execution_hash: Optional[str]
) -> dict:
    """
    Detect if a prompt was modified between template creation and execution.
    
    Args:
        template_hash: Hash stored when template was created
        execution_hash: Hash of prompt actually sent to model
        
    Returns:
        Dictionary with detection results
    """
    if not template_hash or not execution_hash:
        return {
            "modified": None,
            "reason": "Missing hash data",
            "template_hash": template_hash,
            "execution_hash": execution_hash
        }
    
    if template_hash == execution_hash:
        return {
            "modified": False,
            "reason": "Prompt unchanged",
            "template_hash": template_hash,
            "execution_hash": execution_hash
        }
    else:
        return {
            "modified": True,
            "reason": "Prompt was modified between creation and execution",
            "template_hash": template_hash,
            "execution_hash": execution_hash,
            "warning": "Integrity check failed - prompt may have been altered"
        }

def find_duplicate_prompts(prompts: list[dict]) -> dict:
    """
    Find duplicate prompts based on hash.
    
    Args:
        prompts: List of dicts with 'id' and 'prompt_text' keys
        
    Returns:
        Dictionary mapping hash to list of duplicate prompt IDs
    """
    hash_map = {}
    
    for prompt in prompts:
        prompt_id = prompt.get('id')
        prompt_text = prompt.get('prompt_text', '')
        prompt_hash = calculate_prompt_hash(prompt_text)
        
        if prompt_hash not in hash_map:
            hash_map[prompt_hash] = []
        hash_map[prompt_hash].append(prompt_id)
    
    # Filter to only show duplicates
    duplicates = {
        hash_val: ids 
        for hash_val, ids in hash_map.items() 
        if len(ids) > 1
    }
    
    return duplicates