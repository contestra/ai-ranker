# Brand Entity Probe Documentation

## Overview

The Brand Entity Probe system verifies whether AI models have real knowledge about brands/companies or are hallucinating information. It queries multiple LLMs (OpenAI GPT-5 and Google Gemini) about brand information and classifies their responses to detect the quality of knowledge.

## Version Comparison

### V51 (batch_entity_probe_v51.py)
**Focus**: Production-ready batch processing with robust error handling

### V52 (batch_entity_probe_v52.py)  
**Focus**: Enhanced with confidence scoring, better caching, and export capabilities

## Classification Labels

Both versions classify brand knowledge into these categories:

- **KNOWN_STRONG**: Accurate, specific, verifiable facts about the brand
- **KNOWN_WEAK**: Plausible but generic information
- **UNKNOWN**: Model admits missing information or asks for clarification
- **HALLUCINATED**: Confident claims that are likely untrue
- **EMPTY**: Empty response, refusal, or safety message

## V51 Features

### Core Capabilities
- OpenAI Responses API with GPT-5/GPT-5-mini models
- Dual reasoning modes:
  - `REASONING_EFFORT_MAIN` (default: "medium") for brand extraction
  - `REASONING_EFFORT_MINI` (default: "none") for classification
- Google Gemini integration for comparison
- Idempotent runs with `--force` override
- Thread-safe caching for web searches and HQ claims
- Chunked Google Sheets writes
- Preflight checks for API keys and permissions

### Key Functions
- **claims_location()**: Detects if answer claims a headquarters location
- **density_triggers()**: Counts location-related keywords
- **Label bumping**: Upgrades UNKNOWN/EMPTY to KNOWN_WEAK if substance detected

### Command Line Arguments
```bash
python batch_entity_probe_v51.py \
  --sheet-url <URL>           # Google Sheets URL (or SHEET_URL env)
  --worksheet <NAME>          # Specific worksheet (default: first)
  --start <ROW>              # Start row (default: 2)
  --limit <N>                # Max rows to process
  --only-missing             # Skip already processed rows
  --chunk-size <N>           # Batch size for writes (default: 300)
  --workers <N>              # Thread workers (default: 1)
  --no-gemini                # Disable Gemini
  --with-web                 # Enable DuckDuckGo search (OFF by default)
  --force                    # Re-run tagged rows
  --skip-preflight           # Skip API checks
  --require-gemini           # Fail if Gemini invalid
```

### Environment Variables
```bash
# Required
OPENAI_API_KEY=sk-...
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json

# Optional
SHEET_URL=https://docs.google.com/spreadsheets/d/...
GOOGLE_API_KEY=...           # For Gemini
V51_MIN_OUTPUT_TOKENS=32     # Minimum tokens
V51_WORKERS=1                # Default workers
V51_USE_WEB=0                # Enable web by default (0/1)
V51_CACHE_PATH=.v51_cache.json
REASONING_EFFORT_MAIN=medium # Main model reasoning
REASONING_EFFORT_MINI=none   # Mini model reasoning
GPT_MODEL_FAST=gpt-5
GPT_MODEL_MINI=gpt-5-mini
GEMINI_MODEL=gemini-2.5-pro
```

### Google Sheets Format (V51)
| Column | Content | Description |
|--------|---------|-------------|
| A | Brand Name | Input brand/company name |
| B | OpenAI Answer | Formatted extraction from GPT-5 |
| C | Reserved | Always "-" |
| D | Gemini Answer | Raw Gemini response |
| E | Version Tag | "v51" when processed |
| F | OpenAI Label | Classification (KNOWN_STRONG, etc.) |
| G | Gemini Label | Classification or "-" |
| H | HQ Gate | "TRUE"/"FALSE" if claims location |
| I | Density | Count of location keywords |

## V52 Enhancements

### New Features

#### 1. Confidence Scoring (0-100)
- Each classification includes confidence percentage
- Helps identify borderline cases needing review
- Low confidence on KNOWN_WEAK suggests uncertainty

#### 2. Structured Logging
- JSON Lines format in `logs/v52_run_TIMESTAMP.jsonl`
- Event types: `brand_start`, `brand_complete`, `error`, `retry`, `run_summary`
- Enables analysis of model behavior patterns

#### 3. Enhanced Caching
- Caches model responses (not just web searches)
- Includes timestamps for cache invalidation
- Separate sections: `web`, `model_responses`, `classifications`

#### 4. Incremental Update Mode
- `--update-only` flag reclassifies existing answers
- Saves tokens by not re-querying models
- Useful for testing new classification logic

#### 5. Export Capabilities
- JSON export with full structured data
- CSV export with flattened fields
- Automatic timestamped filenames

#### 6. Improved Retry Logic
- Exponential backoff with jitter
- Per-row retry (not just API level)
- Different handling for rate limits vs errors

#### 7. Simplified Pipeline
- Removed `claims_location()` complexity
- Removed density triggers
- Cleaner separation of concerns

### V52-Specific Arguments
```bash
--update-only              # Only reclassify existing answers
--export {json,csv,both}   # Export results to file
```

### V52 Environment Variables
```bash
V52_LOG_DIR=logs          # Structured log directory
V52_EXPORT_DIR=exports    # Export file directory
V52_CACHE_PATH=.v52_cache.json
V52_MIN_OUTPUT_TOKENS=32
V52_WORKERS=1
V52_USE_WEB=0
```

### Google Sheets Format (V52)
| Column | Content | Description |
|--------|---------|-------------|
| A | Brand Name | Input brand/company name |
| B | OpenAI Answer | Formatted extraction from GPT-5 |
| C | Reserved | Always "-" |
| D | Gemini Answer | Raw Gemini response |
| E | Version Tag | "v52" when processed |
| F | OpenAI Label | Classification |
| G | Gemini Label | Classification or "-" |
| H | **OA Confidence** | OpenAI confidence (0-100) |
| I | **Gemini Confidence** | Gemini confidence (0-100) |

### V52 Cache Structure
```json
{
  "web": {
    "brand_name": "search_snippet"
  },
  "model_responses": {
    "extract_brand_context": {
      "data": {...},
      "tokens": 245,
      "timestamp": "2024-01-15T10:30:00"
    }
  },
  "classifications": {
    "classify_text_hash": {
      "label": "KNOWN_STRONG",
      "confidence": 85.0,
      "timestamp": "2024-01-15T10:30:01"
    }
  }
}
```

### V52 Log Format
```jsonl
{"timestamp":"2024-01-15T10:30:00","event":"brand_start","brand":"Avea Life","row":2}
{"timestamp":"2024-01-15T10:30:05","event":"brand_complete","brand":"Avea Life","row":2,"label":"KNOWN_WEAK","confidence":65.0,"tokens":523}
{"timestamp":"2024-01-15T10:35:00","event":"run_summary","rows_processed":50,"rows_skipped":10,"total_tokens":25000}
```

## Migration Guide: V51 → V52

### Breaking Changes
1. Columns H & I now contain confidence scores (not HQ gate/density)
2. Cache format expanded (but backward compatible)
3. Version tag changed from "v51" to "v52"

### Upgrade Steps
1. Back up your Google Sheet
2. Clear or rename existing cache file
3. Update environment variables (add V52_ prefix)
4. Run with `--force` to reprocess all rows with new format

### Feature Comparison

| Feature | V51 | V52 |
|---------|-----|-----|
| Confidence Scores | ❌ | ✅ (0-100) |
| Response Caching | ❌ | ✅ |
| Structured Logging | ❌ | ✅ (JSON Lines) |
| Export to JSON/CSV | ❌ | ✅ |
| Update-Only Mode | ❌ | ✅ |
| HQ Location Gate | ✅ | ❌ (removed) |
| Density Triggers | ✅ | ❌ (removed) |
| Web Search | Optional | Optional |
| Retry Logic | Basic | Enhanced |
| Token Optimization | Standard | Optimized |

## Usage Examples

### V51: Basic Run
```bash
# Process first 100 brands
python batch_entity_probe_v51.py --limit 100

# Resume processing, skip completed
python batch_entity_probe_v51.py --only-missing

# Parallel processing with web search
python batch_entity_probe_v51.py --workers 5 --with-web
```

### V52: Advanced Usage
```bash
# Full run with confidence scoring and export
python batch_entity_probe_v52.py --limit 100 --export both

# Update classifications only (no API calls)
python batch_entity_probe_v52.py --update-only

# Production run with all features
python batch_entity_probe_v52.py \
  --workers 3 \
  --chunk-size 100 \
  --export json \
  --only-missing
```

## Performance Considerations

### Token Usage
- V51: ~600-800 tokens per brand (with reasoning)
- V52: ~400-600 tokens per brand (optimized prompts)
- Update mode (V52): ~50-100 tokens per brand

### Processing Speed
- Single worker: ~2-3 brands/minute
- 5 workers: ~8-10 brands/minute
- Update mode: ~20-30 brands/minute

### Cost Estimates (200 brands)
- V51 Full run: ~150,000 tokens ≈ $5-10
- V52 Full run: ~100,000 tokens ≈ $3-7
- V52 Update only: ~15,000 tokens ≈ $0.50-1

## Troubleshooting

### Common Issues

#### "Permission denied" for Google Sheets
- Share the sheet with your service account email
- Check `client_email` in your credentials JSON

#### Rate limits
- V52 handles automatically with exponential backoff
- V51 may need manual retry
- Reduce `--workers` if hitting limits

#### Empty/BLOCKED responses
- Check if brand name is ambiguous
- Try with `--with-web` for context
- May indicate safety filtering

#### Cache corruption
- Delete `.v51_cache.json` or `.v52_cache.json`
- Cache will rebuild automatically

### Debug Mode
```bash
# V52 structured logs provide detailed debugging
tail -f logs/v52_run_*.jsonl | jq '.'

# Check cache contents
cat .v52_cache.json | jq '.model_responses | keys'
```

## Best Practices

1. **Start small**: Test with `--limit 5` first
2. **Use workers carefully**: Start with 1, increase gradually
3. **Monitor logs**: V52's structured logs help identify issues
4. **Regular exports**: Use `--export both` for backups
5. **Cache management**: Clear cache monthly or when changing models
6. **Incremental updates**: Use V52's `--update-only` for quick re-classification
7. **Version control**: Keep your Sheet URL in `.env` file (not in code)

## Future Enhancements

### Potential V53 Features
- Confidence thresholds for auto-retry
- Multi-model ensemble voting
- Custom classification schemas
- Real-time web UI dashboard
- Automatic quality reports
- Integration with vector databases
- A/B testing framework for prompts