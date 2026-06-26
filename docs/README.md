#  AI-Powered Localization Quality Assessment (LQA) Dashboard

End-to-end translation quality management system with AI-powered evaluation, interactive review, and automated template generation.

## Features

- ** AI Quality Assessment** - Automated LQA using OpenAI/Mistral/Llama/DeepSeek models
- ** Interactive Dashboard** - Real-time translation review with error highlighting
- ** Cost Estimation** - Pre-evaluation cost calculation based on content size
- ** Translation Memory (TMX)** - Fuzzy matching against existing translations
- ** On-Demand Evaluation** - Evaluate multiple locales with progress tracking
- ** One-Click Fixes** - Approve corrections and rebuild templates instantly
- ** Locale Switcher** - Generated pages include language selection UI

---

## Quick Start

### 1. Setup Environment

```bash
# Install dependencies
pip install -r requirements.txt

# Set API key (OpenAI, Mistral, etc.)
export LLM_API_KEY="your-api-key-here"
export LLM_MODEL_NAME="gpt-4o-mini"  # Optional, defaults to gpt-4o-mini
```

### 2. Generate HTML Pages

```bash
# Generates localized HTML from JSON translations
python generate_pages.py
```

Output: `templates/index_*.html` (one per locale)

### 3. Start Dashboard

```bash
cd dashboards
python server.py
```

Open: **http://127.0.0.1:8000**

---

## How It Works

**Why Scraping & Alignment?**

1. **Scraping** (`batch_parser.py`): Extracts text content + DOM paths from HTML templates
   - **Why?** To locate errors precisely on the page (e.g., "error in #calcio section, h2 tag")
   - **Output**: JSON with text, DOM paths, and structural context

2. **Alignment** (`align_elements.py`): Matches source (it-IT) ↔ target (en-US) text pairs
   - **Why?** AI needs to compare Italian text with its English translation to find errors
   - **How?** 3-tier matching: exact DOM path → fuzzy similarity → positional fallback

3. **LQA Evaluation** (`main.py`): AI analyzes aligned pairs using OpenAI/Mistral
   - **Why?** Human-quality linguistic assessment at scale
   - **Output**: Errors with severity, category, and suggested fixes

---

## Workflow

### Adding a New Locale

1. **Create translation file**: `locales/xx-XX.json` with the strings from the source `locales\it-IT.json`.


2. **Generate HTML page**:
   Running the below command will generate HTML pages for all the locales present in the `locales/` folder.
   ```bash
   python generate_pages.py
   ```

3. **Evaluate quality**: Running `main.py` (you have to provide the locale code that you want to evaluate) or through the dashboard.

---

## Evaluating Translations

### Via Command Line

```bash
# Set target locale
export TARGET_LOCALE="xx-XX"

# Run evaluation
python main.py
```

### Via Dashboard

1. Open dashboard: `http://127.0.0.1:8000`
2. Click **"⚡ New Evaluation"**
3. Select locales to evaluate
4. Choose AI model (gpt-4o-mini, mistral-large, etc.)
5. Review estimated cost
6. Click **"⚡ Start Evaluation"**
7. Monitor real-time progress:
   - Phase 1: Extract Elements (scraping)
   - Phase 2: Evaluate Locales (LQA analysis)

Output: `outputs/lqa_audit_report_it-IT_xx-XX.json`

---

## Reviewing Errors

### Dashboard View

1. Select locale tab (e.g., **en-US**)
2. View **error cards** in right sidebar:
   - Error category (MQM: Accuracy, Fluency, etc.)
   - Severity (Critical/Major/Minor)
   - Source vs. Target text
   - Suggested fix
   - TMX matches (if available)

3. **Error highlighting**:
   - Red border = errors found
   - Yellow border = some fixed
   - Green border = all fixed

### Actions

**Approve Fix:**
- Click **"✓ Approve & Apply"**
- Text updated in preview
- Added to `outputs/approved_fixes_{locale}.json`

**Reject Issue:**
- Click **"✗ Reject"**
- Logged to `outputs/rejected_issues_{locale}.json`
- Card dismissed

**Rebuild Templates:**
- Click **"⚙️ Update Translations & Rebuild"**
- Applies approved fixes to `locales/{locale}.json`
- Regenerates `templates/index_{locale}.html`

---

## Translation Memory (TMX)

### How It Works

1. Evaluation automatically enriches errors with TMX matches
2. Fuzzy matching against `memory.xml` (threshold: 40%)
3. Shows similar translations from previous work

### TMX Match Display

```
📚 Translation Memory Match (85% similarity)
TMX Source: "Calcio Storico Fiorentino"
TMX Target: "Historic Florentine Football"
Available in: en-US, de-DE, ja-JP
```

### Adding TMX Entries

Edit `memory.xml`:
```xml
<tu tuid="calcio_001">
  <tuv xml:lang="it-IT">
    <seg>Calcio Storico</seg>
  </tuv>
  <tuv xml:lang="en-US">
    <seg>Historic Football</seg>
  </tuv>
</tu>
```

---

## Cost Estimation

**Before evaluation**, the dashboard shows:

```
💰 Estimated Cost: $0.0063
~29.8k tokens (25,772 input + 4,000 output)
⚠️ Scraping phase required (~10s)
```

**Cost factors:**
- Input: Prompt + extracted content + locale profiles
- Output: LQA report structure
- Model: Different pricing per provider

**Example costs (3 locales):**
- gpt-4o-mini: ~$0.01
- gpt-4o: ~$0.18
- deepseek-coder: ~$0.004

---

## Model Selection

Available models across providers:

| Provider | Models | Use Case |
|----------|--------|----------|
| OpenAI | gpt-4o, gpt-4o-mini, gpt-3.5-turbo | General purpose, high quality |
| Mistral | mistral-large, mistral-medium, mistral-small | European languages |
| Meta | llama-3.1-70b, llama-3.1-8b | Open source, good quality/cost |
| Microsoft | phi-3-medium, phi-3-mini | Fast, lightweight |
| DeepSeek | deepseek-coder, deepseek-chat | Cheapest option |

---

## Project Structure

```
L10N_Hackathon/
├── locales/                    # Translation JSON files
│   ├── it-IT.json             # Source (Italian)
│   ├── en-US.json             # Target locales
│   ├── ja-JP.json
│   └── pl-PL.json
│
├── templates/
│   ├── index_template.html    # Base template with {{PLACEHOLDERS}}
│   ├── index_it-IT.html       # Generated pages (with locale switcher)
│   └── index_*.html           # One per locale
│
├── outputs/                    # LQA reports and fixes
│   ├── lqa_audit_report_it-IT_en-US.json
│   ├── approved_fixes_en-US.json
│   └── rejected_issues_en-US.json
│
├── extracted_data/             # Scraped HTML content
│   └── index_*.json
│
├── dashboards/
│   ├── server.py              # FastAPI backend
│   └── index.html             # Dashboard UI
│
├── main.py                     # LQA evaluation pipeline
├── generate_pages.py           # HTML template generator
├── batch_parser.py             # HTML scraper
├── align_elements.py           # Source-target alignment
├── tmx_matcher.py              # Translation memory matching
├── cost_estimator.py           # Token counting & pricing
└── memory.xml                  # TMX translation memory
```

---

## Configuration

### Locale Profiles

Edit `prompt/locale_profiles.py` to add linguistic rules:

```python
LOCALE_PROFILES = {
    "fr-FR": {
        "name": "French (France)",
        "grammar_rules": ["articles must match gender", "formal vous vs. tu"],
        "conventions": ["dates: DD/MM/YYYY", "currency: € after number"],
        "cultural_notes": ["avoid anglicisms", "regional variations"]
    }
}
```

### Environment Variables

```bash
# Required
export LLM_API_KEY="sk-..."

# Optional
export LLM_BASE_URL="https://api.openai.com/v1"  # Or Groq, OpenRouter, etc.
export LLM_MODEL_NAME="gpt-4o-mini"
export TARGET_LOCALE="en-US"
```

---

## Advanced Features

### Source Locale Reference

Dashboard includes **it-IT (SOURCE)** tab to view original Italian text while reviewing translations.

### Dynamic Tab Addition

New locales appear automatically after evaluation—no page reload needed.

### Error Highlighting Cleared

Switching locales clears previous error highlights for clean comparison.

### Responsive Locale Switcher

Generated pages include mobile-friendly language selection UI.

---

## API Endpoints

### Dashboard Backend

```bash
# Get evaluated locales
GET /api/locales

# Get all available locales (from locales/ directory)
GET /api/locales/available

# Get LQA report + content for locale
GET /api/report/{locale}

# Get available AI models
GET /api/models

# Estimate evaluation cost
POST /api/estimate-cost
Body: {"locales": ["en-US", "ja-JP"], "model": "gpt-4o-mini"}

# Start evaluation
POST /api/evaluate
Body: {"locales": ["en-US"], "model": "gpt-4o-mini"}

# Check evaluation progress
GET /api/evaluate/status/{task_id}

# Approve fix
POST /api/approve
Body: {"locale": "en-US", "error_id": "ERR_001", "approved_translation": "..."}

# Rebuild templates with approved fixes
POST /api/rebuild/{locale}

# TMX translation memory lookup
GET /api/tmx/match?source_text=...&target_text=...&source_locale=it-IT&target_locale=en-US
```

---

## Troubleshooting

### "No API key" error
```bash
export LLM_API_KEY="your-key-here"
```

### Dashboard shows empty/old data
```bash
# Hard refresh browser (Ctrl+F5 or Cmd+Shift+R)
```

### Evaluation fails
```bash
# Check API key is valid
curl -H "Authorization: Bearer $LLM_API_KEY" https://api.openai.com/v1/models

# Check locale file exists
ls locales/en-US.json

# Check output directory writable
ls -la outputs/
```

### Generated pages missing locale switcher
```bash
# Regenerate all pages
python generate_pages.py
```

---

## Demo Workflow

**Perfect for presentations:**

1. **Show existing reports** - Dashboard with 3 evaluated locales
2. **Add new locale** - Create `locales/de-DE.json`
3. **Estimate cost** - Click New Evaluation → see $0.003 estimate
4. **Run evaluation** - Watch two-phase progress (Extract → Evaluate)
5. **Review errors** - Click de-DE tab → see error cards with TMX matches
6. **Approve fix** - "Historical Calcium Match" → "Historic Calcio"
7. **Rebuild** - Click rebuild → see updated template
8. **Check source** - Click it-IT (SOURCE) tab → see original Italian
9. **Switch in browser** - Open generated page → click locale buttons

---

## License

MIT License - See LICENSE file

---

## Credits

Built for L10N Hackathon 2026 - AI-powered translation quality assessment demonstration.

**Stack:** Python, FastAPI, OpenAI API, TMX, Pydantic, Tailwind CSS

**Development**: This project was developed with AI assistance (Google Gemini and Anthropic Claude) for code implementation, architecture design, documentation, and testing. All design decisions and requirements were directed by the human developer.
