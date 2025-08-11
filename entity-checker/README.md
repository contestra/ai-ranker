# Brand Entity Check

A sophisticated system for verifying AI model knowledge about brands and companies. This tool helps determine whether language models have genuine knowledge about a brand or are generating hallucinated information.

## 🎯 Purpose

When AI models are asked about brands or companies, they may:
- Have accurate, specific knowledge (KNOWN_STRONG)
- Have generic but plausible information (KNOWN_WEAK)  
- Admit they don't know (UNKNOWN)
- Generate false information confidently (HALLUCINATED)
- Refuse to answer (EMPTY)

This system systematically tests and classifies model knowledge across multiple brands using both OpenAI's GPT-5 and Google's Gemini models.

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- OpenAI API key
- Google Cloud service account (for Sheets access)
- Google API key (optional, for Gemini)

### Installation

```bash
# Clone the repository
git clone https://github.com/contestra/brand-entity-check.git
cd brand-entity-check

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys and credentials
```

### Basic Usage

```bash
# Process first 10 brands with V52 (recommended)
python batch_entity_probe_v52.py --limit 10

# Export results to CSV and JSON
python batch_entity_probe_v52.py --limit 10 --export both

# Update classifications only (no API calls)
python batch_entity_probe_v52.py --update-only
```

## 📚 Documentation

See [V51_V52_DOCUMENTATION.md](V51_V52_DOCUMENTATION.md) for comprehensive documentation including:
- Feature comparison between V51 and V52
- Command-line arguments
- Environment variables
- Google Sheets setup
- Cost estimates
- Troubleshooting guide

## 🔧 Available Versions

### V52 (Recommended)
Enhanced version with confidence scoring and better caching:
- **Confidence scores** (0-100) for each classification
- **Full response caching** to reduce API costs
- **Structured JSON logging** for analysis
- **Export to CSV/JSON** for further processing
- **Update-only mode** for reclassification

### V51 (Stable)
Production-ready version with robust error handling:
- OpenAI Responses API with reasoning
- Google Gemini integration
- Web search capability (optional)
- Parallel processing support
- Idempotent runs

## 📊 Google Sheets Setup

1. Create a Google Sheet with brands in column A
2. Share the sheet with your service account email
3. Set the sheet URL in your environment or command line

### Sheet Format

| Column | V51 Content | V52 Content |
|--------|-------------|-------------|
| A | Brand Name | Brand Name |
| B | OpenAI Answer | OpenAI Answer |
| C | Reserved | Reserved |
| D | Gemini Answer | Gemini Answer |
| E | Version Tag | Version Tag |
| F | OA Label | OA Label |
| G | Gemini Label | Gemini Label |
| H | HQ Gate (T/F) | **OA Confidence (0-100)** |
| I | Density Count | **Gemini Confidence (0-100)** |

## 🔑 Environment Variables

Create a `.env` file with:

```bash
# Required
OPENAI_API_KEY=sk-...
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json

# Optional
SHEET_URL=https://docs.google.com/spreadsheets/d/...
GOOGLE_API_KEY=...  # For Gemini

# Model configuration
GPT_MODEL_FAST=gpt-5
GPT_MODEL_MINI=gpt-5-mini
GEMINI_MODEL=gemini-2.5-pro

# V52 specific
V52_LOG_DIR=logs
V52_EXPORT_DIR=exports
```

## 💰 Cost Estimates

For 200 brands:
- **V52 Full run**: ~100,000 tokens ≈ $3-7
- **V52 Update only**: ~15,000 tokens ≈ $0.50-1
- **V51 Full run**: ~150,000 tokens ≈ $5-10

## 📈 Performance

- **Single worker**: ~2-3 brands/minute
- **5 workers**: ~8-10 brands/minute  
- **Update mode**: ~20-30 brands/minute

## 🛠️ Advanced Usage

### Parallel Processing
```bash
python batch_entity_probe_v52.py --workers 5 --chunk-size 100
```

### With Web Search Context
```bash
python batch_entity_probe_v52.py --with-web
```

### Force Reprocess
```bash
python batch_entity_probe_v52.py --force
```

### Export and Analysis
```bash
# Generate timestamped exports
python batch_entity_probe_v52.py --export both

# View structured logs
tail -f logs/v52_run_*.jsonl | jq '.'
```

## 📝 Classification Labels

- **KNOWN_STRONG**: Accurate, specific, verifiable facts
- **KNOWN_WEAK**: Plausible but generic information
- **UNKNOWN**: Model admits missing information
- **HALLUCINATED**: Confident but likely false claims
- **EMPTY**: Refusal or safety block

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is proprietary to Contestra. All rights reserved.

## 🙏 Acknowledgments

Built with:
- OpenAI GPT-5 API
- Google Gemini API
- Google Sheets API
- Python gspread library

## 📧 Contact

For questions or support, please open an issue on GitHub.

---

**Note**: This tool is designed for research and verification purposes. Always verify critical brand information through official sources.