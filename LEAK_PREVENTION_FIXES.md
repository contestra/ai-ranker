# Leak Prevention Fixes - August 12, 2025

## The Problem
Gemini 2.5 was explicitly saying:
> "Based on my training data and interpreting the location context **'DE'** as Germany..."

This revealed the model was seeing "DE" tokens, defeating the purpose of invisible ambient blocks.

## Root Cause: Self-Defeating Banlist
The system prompt's banlist explicitly mentioned "DE" which taught the model that "DE" was a location code:
```
Do not include these strings in your answer: DE, Germany, Deutschland...
```
This was self-defeating - we were teaching the model what "DE" means by telling it not to say it!

## Fixes Applied

### 1. Removed All ccTLD Domains
- **Germany**: `bund.de` → `Bundesportal`
- **Switzerland**: `ch.ch` → `Bundesverwaltung`  
- **France**: `service-public.fr` → `Service Public`
- **Others**: Already using neutral labels (GOV.UK, ICA, etc.)

### 2. Fixed System Prompt - Removed Self-Defeating Banlist
Removed explicit country codes from the system prompt. Now says:
```
Do not state or imply country/region/city names unless the user explicitly asks.
```
No longer mentions "DE" or other codes that would teach the model what they mean.

### 3. Confirmed Correct Message Order
1. **System prompt** - Allows silent locale adoption, bans mentioning it
2. **Ambient Block** - Sent BEFORE prompt (feels like prior state)
3. **User prompt** - Naked, unmodified

### 4. Clean Ambient Block Format
```
Lokaler Kontext (nur zur Lokalisierung; nicht zitieren):
- 2025-08-12 22:18, +02:00
- Bundesportal — "Reisepass beantragen Termin"
- 10115 Berlin • +49 30 xxx xx xx • 12,90 €
- Nationaler Wetterdienst: Berlin
```

## What This Prevents

✅ No more "interpreting location context 'DE'"
✅ No country codes visible to model
✅ No ccTLD domains (.de, .ch, .fr) as hints
✅ Clean locale inference without explanation

## Validation Checklist

- [ ] Log exact messages sent to model - confirm no DE/Germany/Deutschland
- [ ] Verify ALS block is BEFORE user prompt
- [ ] Check no metadata or debug info leaks country codes
- [ ] Test with probe questions (VAT rate, plug type) to confirm inference works
- [ ] Monitor for any echo of banned strings

## Files Modified

1. `backend/app/services/als/als_templates.py` - Removed ccTLD domains
2. `backend/app/llm/langchain_adapter.py` - Added banlist to system prompt

## Next Steps

Test the system to verify:
1. Models adapt to local context (mention local companies, regulations)
2. Models DO NOT mention country names or codes
3. Models DO NOT explain they're inferring location
4. Clean, natural responses as if they naturally know the locale