from textwrap import dedent
from ..constants import GroundingMode

def compose_final_prompt(*, user_query: str, brand_name: str, website_domain: str | None, language: str = "en-US", grounding_mode: GroundingMode = GroundingMode.NONE, grounded_context: str | None = None, extra_instructions: str | None = None) -> str:
    brand_block = f"BRAND: {brand_name}"
    domain_block = f"DOMAIN: {website_domain}" if website_domain else "DOMAIN: (none)"
    sys = dedent(f"""
    SYSTEM:
    - You are an accurate, concise assistant.
    - Respond strictly in {language}.
    {brand_block}
    {domain_block}
    """).strip()
    guide = "- Be precise. If unsure, say you don't know."
    if grounding_mode == GroundingMode.WEB:
        guide = """- Use the SOURCES below to support your answer.
- Insert inline citation markers like [1], [2] that map to SOURCES.
- If SOURCES do not cover the question, say so briefly."""
    if extra_instructions:
        guide += "\n- " + extra_instructions.strip()
    user = f"USER QUESTION:\n{user_query.strip()}"
    ctx = f"\n\nSOURCES (numbered):\n{grounded_context}" if (grounded_context and grounding_mode == GroundingMode.WEB) else ""
    return "\n\n".join([sys, guide, user, ctx]).strip()
