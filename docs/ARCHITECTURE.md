# 🏗️ LQA System Architecture Documentation

**AI-Powered Localization Quality Assessment (LQA) Dashboard**  
*L10N Hackathon 2026*

---

## 📋 Table of Contents

1. [System Overview](#system-overview)
2. [Core Assumptions](#core-assumptions)
3. [Features & Capabilities](#features--capabilities)
4. [Architecture Diagrams](#architecture-diagrams)
5. [Workflow Descriptions](#workflow-descriptions)
6. [Technical Details](#technical-details)
7. [Data Flow](#data-flow)
8. [API Reference](#api-reference)
9. [Security Considerations](#security-considerations)

---

## 🎯 System Overview

### Purpose

The LQA system is an **end-to-end translation quality management platform** that:

- Automatically reviews multilingual websites for linguistic quality
- Identifies translation errors across multiple dimensions (accuracy, fluency, cultural adaptation)
- Provides an interactive dashboard for human review and approval
- Syncs with Translation Memory (TMX) for consistency
- Regenerates localized templates with approved fixes

### Problem Statement (Hackathon)

> **"Are We Fit for This Market?"** - Build an app that reviews and scores multilingual websites for linguistic quality, terminology consistency, cultural adaptation and other criteria. Advanced: Allow for sync between parsed strings and TMX, with human review and approval process.

### Solution Approach

**Three-layer architecture:**

1. **Ingestion Layer**: HTML parsing & extraction
2. **Analysis Layer**: AI-powered quality assessment
3. **Presentation Layer**: Interactive review dashboard

---

## 🧩 Core Assumptions

### 1. Source Locale Assumptions

| Assumption | Rationale | Impact |
|------------|-----------|--------|
| **Source locale is always `it-IT` (Italian)** | Project demonstrates Italian tourism website localization | All alignment and evaluation treats Italian as reference |
| **Source content is 100% correct** | Quality baseline for comparison | No LQA report generated for it-IT |
| **One source → multiple targets** | Standard translation workflow | Single source JSON, multiple target JSONs |

### 2. Content Structure Assumptions

| Assumption | Rationale | Impact |
|------------|-----------|--------|
| **HTML structure is consistent across locales** | Templates generated from same base | DOM path alignment works reliably |
| **Locale JSON is source of truth** | Structured data over HTML | All updates modify JSON, not HTML directly |
| **Element IDs are stable** | Predictable DOM structure | Error reporting tied to IDs like `#calcio`, `#palio` |

### 3. Evaluation Assumptions

| Assumption | Rationale | Impact |
|------------|-----------|--------|
| **MQM scoring model** | Industry standard (Minor=1pt, Major=5pt, Critical=10pt) | Global score = 100 - penalties |
| **AI model is not perfect** | LLMs can hallucinate or miss issues | Human review is required step |
| **Fuzzy TMX matching threshold: 40%** | Balance recall and precision | More matches, some false positives |

### 4. User Workflow Assumptions

| Assumption | Rationale | Impact |
|------------|-----------|--------|
| **Users review errors one-by-one** | Natural approval workflow | Error cards with approve/reject buttons |
| **Batch rebuild after approvals** | Efficient template regeneration | Single "Rebuild" button applies all fixes |
| **Visual preview aids decision-making** | Context is crucial for translation judgment | Browser-like viewport in dashboard |

### 5. Technical Assumptions

| Assumption | Rationale | Impact |
|------------|-----------|--------|
| **OpenAI-compatible API** | Standard for LLM providers | Works with OpenAI, Mistral, Groq, etc. |
| **UTF-8 encoding throughout** | Multilingual support required | Handles Italian, Japanese, Polish, etc. |
| **Python 3.8+** | Modern standard library features | Uses Pydantic v2, type hints |
| **Single-user environment** | Hackathon scope | No authentication or multi-tenancy |

---

## ✨ Features & Capabilities

### Core Features (Must-Have)

#### 1. Multilingual Website Ingestion ✅
- **HTML Parsing**: BeautifulSoup4 + lxml for robust extraction
- **DOM Path Generation**: CSS selector syntax for precise element identification
- **Structural Context**: Captures parent nodes, anchor IDs, hierarchical relationships
- **Multi-Locale Support**: Handles 6+ locales simultaneously

**Files**: `batch_parser.py`

#### 2. Linguistic Quality Assessment ✅
- **AI-Powered Evaluation**: Uses OpenAI/Mistral/Llama/DeepSeek models
- **MQM Framework**: Industry-standard quality metrics
- **Five Evaluation Dimensions**:
  - **Accuracy**: Mistranslations, wrong terminology
  - **Fluency**: Grammar, naturalness, readability
  - **Locale Conventions**: Date formats, currency symbols, number formatting
  - **Cultural Adaptation**: Idioms, regional variations, transcreation
  - **Terminology**: Consistency with brand/domain terminology

**Files**: `main.py`, `prompt/compile_prompt.py`, `prompt/locale_profiles.py`

#### 3. Interactive Dashboard ✅
- **Real-Time Preview**: Browser-like viewport showing translations in context
- **Error Highlighting**: Visual indicators (red/yellow/green borders)
- **Detailed Error Cards**: Source, target, explanation, severity, suggested fix
- **Multi-Locale Tabs**: Easy switching between locales for comparison
- **Source Reference**: View original Italian alongside translations

**Files**: `dashboards/server.py`, `dashboards/index.html`

### Advanced Features

#### 4. TMX Translation Memory Sync ✅
- **Bidirectional Sync**:
  - **Read**: Match errors against TMX for consistency suggestions
  - **Write**: Update TMX with approved corrections (NEW!)
- **Fuzzy Matching**: SequenceMatcher + Levenshtein distance
- **Match Metadata**: TUID, similarity score, match type, available locales
- **Configurable Threshold**: Default 40% minimum similarity

**Files**: `tmx_matcher.py`, `memory.xml`

#### 5. Human Review & Approval Workflow ✅
- **Approve Fix**: Saves to `approved_fixes_{locale}.json`
- **Reject Issue**: Logs to `rejected_issues_{locale}.json`
- **Live Preview Update**: Changes reflected immediately
- **Rebuild Pipeline**: Updates JSON → regenerates HTML → syncs TMX
- **Visual Feedback**: Elements turn yellow (partial) or green (all fixed)

**Files**: `dashboards/server.py` (API endpoints), `dashboards/index.html` (UI)

### Bonus Features

#### 6. Cost Estimation 💰
- **Pre-Evaluation Calculation**: Estimate cost before running
- **Multi-Model Support**: OpenAI, Mistral, Llama, DeepSeek, Phi
- **Token Counting**: Input + output token estimates
- **Per-Locale Breakdown**: Cost transparency

**Files**: `cost_estimator.py`

#### 7. On-Demand Evaluation ⚡
- **Modal UI**: Select locales and model in real-time
- **Progress Tracking**: Two-phase progress (scraping → evaluating)
- **Background Execution**: Non-blocking FastAPI BackgroundTasks
- **Status Polling**: Live updates during evaluation

**Files**: `dashboards/server.py`, `dashboards/index.html`

#### 8. Structured LLM Output 🤖
- **Pydantic Schemas**: Type-safe response validation
- **JSON Mode**: Forces LLM to return valid JSON
- **Error Detection**: Catches malformed outputs immediately

**Files**: `main.py` (LqaReportSchema, ErrorDetail)

---

## 📊 Architecture Diagrams

### System Architecture (High-Level)

```
┌────────────────────────────────────────────────────────────────┐
│                         USER INTERFACE                         │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Dashboard (HTML/JS + Tailwind CSS)                      │  │
│  │  - Locale tabs                                           │  │
│  │  - Browser viewport preview                              │  │
│  │  - Error cards with approve/reject                       │  │
│  │  - Evaluation modal                                      │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────┘
                              ▲
                              │ HTTP/JSON
                              ▼
┌────────────────────────────────────────────────────────────────┐
│                     API LAYER (FastAPI)                        │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Endpoints:                                              │  │
│  │  - GET /api/report/{locale}  [Load LQA data]             │  │
│  │  - POST /api/approve         [Save fix]                  │  │
│  │  - POST /api/rebuild/{locale} [Apply & regenerate]       │  │
│  │  - POST /api/evaluate        [Run LQA pipeline]          │  │
│  │  - GET /api/tmx/match        [TMX lookup]                │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────┘
                              ▲
                              │
                              ▼
┌────────────────────────────────────────────────────────────────┐
│                    BUSINESS LOGIC LAYER                        │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐       │
│  │  HTML Parser  │  │  LQA Engine   │  │  TMX Matcher  │       │
│  │  (BeautifulSo │  │  (OpenAI API) │  │  (Fuzzy Match)│       │
│  │   up)         │  │               │  │               │       │
│  └───────────────┘  └───────────────┘  └───────────────┘       │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐       │
│  │  Alignment    │  │  Template Gen │  │  TMX Writer   │       │
│  │  Engine       │  │               │  │  (NEW!)       │       │
│  └───────────────┘  └───────────────┘  └───────────────┘       │
└────────────────────────────────────────────────────────────────┘
                              ▲
                              │
                              ▼
┌────────────────────────────────────────────────────────────────┐
│                      DATA LAYER                                │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐       │
│  │  Locale JSON  │  │  LQA Reports  │  │  TMX Memory   │       │
│  │  (locales/)   │  │  (outputs/)   │  │  (memory.xml) │       │
│  └───────────────┘  └───────────────┘  └───────────────┘       │
│  ┌───────────────┐  ┌───────────────┐                          │
│  │  HTML Pages   │  │  Approved     │                          │
│  │  (templates/) │  │  Fixes (JSON) │                          │
│  └───────────────┘  └───────────────┘                          │
└────────────────────────────────────────────────────────────────┘
```

### Data Flow Diagram

```
┌──────────────┐
│ templates/   │  Input: Pre-generated HTML templates
│ index_*.html │
└──────┬───────┘
       │
       ▼ (1) HTML Parsing
┌──────────────┐
│ batch_parser │  Extract: Text content + DOM paths + structure
└──────┬───────┘
       │
       ▼ (2) Structured Extraction
┌──────────────────┐
│ extracted_data/  │  Output: JSON with tagged elements
│ index_*.json     │
└──────┬───────────┘
       │
       ▼ (3) Alignment
┌──────────────┐
│ align_       │  Match source ↔ target elements
│ elements.py  │
└──────┬───────┘
       │
       ▼ (4) LQA Evaluation
┌──────────────┐
│ OpenAI API   │  AI analyzes source vs. target
│ (GPT-4o etc) │
└──────┬───────┘
       │
       ▼ (5) TMX Enrichment
┌──────────────┐
│ tmx_matcher  │  Add translation memory suggestions
│              │
└──────┬───────┘
       │
       ▼ (6) LQA Report
┌──────────────────┐
│ outputs/         │  Report: errors + scores + TMX matches
│ lqa_audit_*.json │
└──────┬───────────┘
       │
       ▼ (7) Human Review
┌──────────────┐
│ Dashboard UI │  User approves/rejects fixes
└──────┬───────┘
       │
       ▼ (8) Apply Fixes
┌──────────────────┐
│ approved_fixes_  │  Saved approved corrections
│ {locale}.json    │
└──────┬───────────┘
       │
       ▼ (9) Rebuild Pipeline
       │
       ├─► (9a) Update locale JSON (locales/{locale}.json)
       │
       ├─► (9b) Sync to TMX (memory.xml) ◄── NEW!
       │
       └─► (9c) Regenerate HTML (templates/index_{locale}.html)
```

### Component Interaction Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                       main.py (Orchestrator)                │
│                                                             │
│  run_lqa_pipeline(target_locale)                            │
│    ├─► process_localization_templates()                     │
│    ├─► align_localization_payloads()                        │
│    ├─► OpenAI API call (structured output)                  │
│    └─► enrich_lqa_report_with_tmx()                         │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                   batch_parser.py (Extractor)               │
│                                                             │
│  parse_html_content(html)                                   │
│    ├─► BeautifulSoup parsing                                │
│    ├─► get_dom_path(element)  [CSS selector]                │
│    └─► get_structural_context(element)  [anchors, IDs]      │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                align_elements.py (Matcher)                  │
│                                                             │
│  align_localization_payloads(source_json, target_json)      │
│    ├─► Tier 1: Exact DOM path match                         │
│    ├─► Tier 2: Fuzzy text similarity (SequenceMatcher)      │
│    └─► Tier 3: Positional fallback                          │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│               tmx_matcher.py (TMX Handler)                  │
│                                                             │
│  TMXParser: Load XML → TMXEntry objects                     │
│  TMXMatcher: Fuzzy match errors ↔ TMX                       │
│  TMXWriter: Update TMX with approved fixes ◄── NEW!         │
│    ├─► update_translation(tuid, locale, text)               │
│    ├─► create_translation_unit(...)                         │
│    └─► save(backup=True)                                    │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│             dashboards/server.py (API Server)               │
│                                                             │
│  FastAPI Endpoints:                                         │
│    ├─► /api/report/{locale}  [GET]                          │
│    ├─► /api/approve  [POST]                                 │
│    ├─► /api/rebuild/{locale}  [POST]                        │
│    │     └─► write_approved_fixes_to_tmx() ◄── NEW!         │
│    ├─► /api/evaluate  [POST → Background Task]              │
│    └─► /api/tmx/*  [TMX endpoints]                          │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔄 Workflow Descriptions

### 1. Initial Setup Workflow

```
User Action: Add new locale
   │
   ├─► 1. Create locales/xx-XX.json (copy structure from it-IT.json)
   │
   ├─► 2. Run: python generate_pages.py
   │       → Generates templates/index_xx-XX.html
   │
   └─► 3. Ready for evaluation
```

### 2. Evaluation Workflow

```
User Action: Click "⚡ New Evaluation"
   │
   ├─► Dashboard: Show modal with:
   │     - Locale checkboxes (from locales/ directory)
   │     - Model dropdown (gpt-4o-mini, mistral-large, etc.)
   │     - Cost estimate (calculated in real-time)
   │
   ├─► User: Select locales + model → Click "Start"
   │
   ├─► Backend: POST /api/evaluate
   │     └─► For each locale (background task):
   │           ├─► Phase 1: Scraping (~3s)
   │           │     process_localization_templates()
   │           │       → extracted_data/index_{locale}.json
   │           │
   │           ├─► Phase 2: Evaluation (~30-60s)
   │           │     ├─► Alignment (source ↔ target)
   │           │     ├─► OpenAI API call (structured JSON response)
   │           │     └─► TMX enrichment (match errors to memory)
   │           │
   │           └─► Output: outputs/lqa_audit_report_it-IT_{locale}.json
   │
   └─► Frontend: Poll /api/evaluate/status/{task_id}
         → Show progress bar + current locale
         → On complete: Refresh locale tabs
```

### 3. Review & Approval Workflow

```
User Action: Select locale tab (e.g., en-US)
   │
   ├─► Dashboard loads: /api/report/en-US
   │     Returns: { lqa: {...}, page_content: [...] }
   │
   ├─► Display:
   │     ├─► Left: Browser viewport with highlighted elements
   │     └─► Right: Error cards (sorted by severity)
   │
   ├─► User reviews error:
   │     Error Card shows:
   │       - Source: "Calcio Storico"
   │       - Target: "Historical Calcium Match" (wrong!)
   │       - Issue: "Mistranslation: 'Calcio' is football, not calcium"
   │       - Fix: "Historic Soccer Match"
   │       - TMX Match: "Historic Football" (85% similar)
   │
   ├─► User clicks: "✓ Approve & Apply"
   │     → POST /api/approve
   │       └─► Saves to: outputs/approved_fixes_en-US.json
   │       └─► Updates preview (element turns yellow → pending)
   │
   ├─► OR User clicks: "✗ Reject"
   │     → POST /api/reject
   │       └─► Logs to: outputs/rejected_issues_en-US.json
   │
   └─► After reviewing all errors...
```

### 4. Rebuild & Deployment Workflow

```
User Action: Click "⚙️ Update Translations & Rebuild"
   │
   ├─► Backend: POST /api/rebuild/en-US
   │
   ├─► Step 1: Load approved fixes
   │     └─► Read: outputs/approved_fixes_en-US.json
   │
   ├─► Step 2: Update locale JSON
   │     ├─► Map DOM path → JSON key path
   │     │     (e.g., #calcio → sections.calcio.title)
   │     ├─► Update: locales/en-US.json
   │     └─► Count: X fields updated
   │
   ├─► Step 3: Sync to TMX ◄── NEW!
   │     └─► write_approved_fixes_to_tmx()
   │           ├─► Match approved fixes to TMX entries (fuzzy)
   │           ├─► Update existing <tu> elements
   │           ├─► Create new <tu> for unmatched fixes
   │           ├─► Backup: memory.xml.backup_YYYYMMDD_HHMMSS
   │           └─► Save: memory.xml
   │
   ├─► Step 4: Regenerate HTML
   │     └─► Run: python generate_pages.py
   │           → Overwrites templates/index_en-US.html
   │
   └─► Response: {
         "status": "success",
         "patched_elements": 3,
         "tmx_updated": 2,
         "tmx_created": 1
       }
```

### 5. TMX Synchronization Workflow (NEW!)

```
┌─────────────────────────────────────────────────────────┐
│              TMX Bidirectional Sync                     │
└─────────────────────────────────────────────────────────┘

READ Direction (Error Detection → TMX Lookup):
  LQA Error → TMXMatcher.find_best_match()
    ├─► Fuzzy match source + target text
    ├─► Return: TMXEntry + similarity score + match type
    └─► Display in error card: "📚 TMX Suggestion"

WRITE Direction (Approved Fix → TMX Update): ◄── NEW!
  Approved Fix → write_approved_fixes_to_tmx()
    ├─► For each fix:
    │     ├─► Match to existing TMX entry (threshold: 70%)
    │     │     ├─► Found: Update <tuv> for target locale
    │     │     └─► Not found: Create new <tu> element
    │     └─► Result: {'updated': X, 'created': Y}
    │
    ├─► Backup original TMX (timestamped)
    └─► Save updated memory.xml

Benefits:
  ✅ Translation memory learns from corrections
  ✅ Future evaluations benefit from past approvals
  ✅ Consistent terminology across projects
  ✅ Reduced manual review over time
```

---

## 🔧 Technical Details

### Tech Stack

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| **Backend** | Python | 3.8+ | Core language |
| **Web Framework** | FastAPI | 0.104+ | RESTful API server |
| **ASGI Server** | Uvicorn | 0.24+ | Production server |
| **HTML Parsing** | BeautifulSoup4 | 4.12+ | DOM extraction |
| **XML Parsing** | lxml | 4.9+ | High-performance HTML/XML |
| **LLM Integration** | OpenAI SDK | 1.0+ | AI evaluation |
| **Data Validation** | Pydantic | 2.0+ | Type-safe schemas |
| **Frontend** | HTML/JS | - | Dashboard UI |
| **CSS Framework** | Tailwind CSS | 3.x | Utility-first styling |

### File Structure

```
L10N_Hackathon/
├── main.py                    # LQA pipeline orchestrator
├── batch_parser.py            # HTML → JSON extractor
├── align_elements.py          # Source ↔ Target alignment
├── tmx_matcher.py             # TMX read/write (NEW: write!)
├── cost_estimator.py          # Token counting & pricing
├── generate_pages.py          # JSON → HTML template generation
├── logging_config.py          # Centralized logging (NEW!)
│
├── prompt/
│   ├── compile_prompt.py      # System prompt builder
│   └── locale_profiles.py     # Locale-specific rules
│
├── dashboards/
│   ├── server.py              # FastAPI backend
│   └── index.html             # Interactive dashboard
│
├── locales/                   # Source of truth (JSON)
│   ├── it-IT.json            # Source (Italian)
│   ├── en-US.json            # Target locales
│   ├── ja-JP.json
│   └── ...
│
├── templates/                 # Generated HTML
│   ├── index_template.html   # Base template
│   ├── index_it-IT.html      # Generated pages
│   └── ...
│
├── extracted_data/            # Scraped content
│   ├── index_it-IT.json
│   └── ...
│
├── outputs/                   # LQA reports & fixes
│   ├── lqa_audit_report_it-IT_en-US.json
│   ├── approved_fixes_en-US.json
│   └── rejected_issues_en-US.json
│
├── memory.xml                 # TMX translation memory
├── requirements.txt           # Python dependencies (NEW!)
├── test_tmx_matcher.py        # Unit tests (NEW!)
├── test_align_elements.py     # Unit tests (NEW!)
│
├── README.md                  # User guide
└── ARCHITECTURE.md            # This file (NEW!)
```

### Key Algorithms

#### 1. DOM Path Generation

```python
def get_dom_path(element):
    """
    Generate CSS selector path for element.
    Example: html > body > article:nth-of-type(2) > h3:nth-of-type(1)
    """
    path = []
    while element and element.name != '[document]':
        siblings = element.find_previous_siblings(element.name)
        index = len(siblings) + 1
        path.append(f"{element.name}:nth-of-type({index})")
        element = element.parent
    return " > ".join(reversed(path))
```

#### 2. Fuzzy Text Matching (TMX)

```python
def _calculate_similarity(text1, text2):
    """
    Uses Python's difflib.SequenceMatcher (Ratcliff-Obershelp algorithm)
    Returns: 0.0 (no match) to 1.0 (perfect match)
    """
    norm_text1 = normalize(text1)  # lowercase + strip whitespace
    norm_text2 = normalize(text2)
    return SequenceMatcher(None, norm_text1, norm_text2).ratio()
```

#### 3. Alignment Strategy (Three-Tier)

```python
def align_localization_payloads(source_json, target_json):
    """
    Tier 1: Exact DOM path match (fastest, most reliable)
    Tier 2: Fuzzy text match within same anchor (handles drift)
    Tier 3: Positional fallback (same tag, same anchor)
    """
    for src_item in source_data:
        # Tier 1: Exact DOM path
        if dom_path in target_path_map:
            tgt_item = target_path_map[dom_path]
        
        # Tier 2: Fuzzy similarity within anchor
        elif anchor_id in target_anchor_clusters:
            tgt_item = find_best_fuzzy_match(src_item, candidates)
        
        # Tier 3: Positional fallback
        else:
            tgt_item = find_by_position(src_item, anchor_candidates)
```

#### 4. MQM Scoring

```python
def calculate_global_score(errors):
    """
    Penalties:
      Minor = 1 point
      Major = 5 points
      Critical = 10 points
    
    Formula: global_score = max(0, 100 - sum(penalties))
    """
    penalties = sum([
        1 * minor_count,
        5 * major_count,
        10 * critical_count
    ])
    return max(0, 100 - penalties)
```

---

## 🔐 Security Considerations

### Current State (Hackathon Scope)

⚠️ **Not production-ready** - Single-user environment assumptions

| Area | Current State | Production Requirement |
|------|---------------|----------------------|
| **Authentication** | None | OAuth2 / JWT tokens |
| **API Keys** | Environment variables | Secrets manager (Vault, AWS Secrets) |
| **CORS** | `allow_origins=["*"]` | Whitelist specific domains |
| **Input Validation** | Minimal | Strict sanitization, rate limiting |
| **File Upload** | Not implemented | Virus scanning, size limits |
| **TMX Backup** | Timestamped files | Versioned storage (S3, Git LFS) |

### Recommended Security Enhancements

1. **Add authentication middleware** (FastAPI dependencies)
2. **Encrypt API keys** at rest
3. **Validate all user inputs** (filename injection, XSS)
4. **Rate limit API endpoints** (prevent abuse)
5. **Audit logging** (who approved what, when)

---

## 📈 Performance Considerations

### Current Performance

| Operation | Time | Bottleneck |
|-----------|------|-----------|
| HTML Scraping (6 locales) | ~3s | Disk I/O |
| LQA Evaluation (1 locale) | ~30-60s | OpenAI API latency |
| TMX Matching (per error) | <10ms | In-memory fuzzy search |
| Dashboard Load | <500ms | JSON parsing |
| Template Rebuild | ~2s | Subprocess + file write |

### Optimization Opportunities

1. **Parallel Evaluation**: Run multiple locales concurrently (current: sequential)
2. **TMX Indexing**: Pre-compute embeddings for semantic search
3. **Caching**: Cache LQA reports (Redis), invalidate on rebuild
4. **Streaming**: Server-Sent Events for real-time progress
5. **Database**: Replace JSON files with PostgreSQL for large-scale

---

## 🧪 Testing Strategy

### Test Coverage (NEW!)

```
test_tmx_matcher.py           # TMX parsing, matching, write-back
  ├─► TestTMXParser          # XML parsing correctness
  ├─► TestTMXMatcher         # Fuzzy matching accuracy
  ├─► TestTMXWriter          # Update/create/save operations
  └─► TestTMXEntry           # Data structure integrity

test_align_elements.py        # Alignment algorithm
  ├─► Exact DOM path match
  ├─► Fuzzy anchor match
  ├─► Multiple elements
  └─► Image alt text
```

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Run all tests
pytest -v

# Run specific test file
pytest test_tmx_matcher.py -v

# Run with coverage
pytest --cov=. --cov-report=html
```

---

## 📝 Logging & Monitoring

### Logging Architecture (NEW!)

```
logging_config.py
  ├─► Console Handler (INFO level)
  ├─► File Handler (DEBUG level)
  │     └─► logs/lqa_system_YYYYMMDD.log
  └─► Error Handler (ERROR level only)
        └─► logs/lqa_errors_YYYYMMDD.log
```

### Log Levels

| Level | Usage | Example |
|-------|-------|---------|
| **DEBUG** | Detailed diagnostic info | Alignment tier choices, TMX match scores |
| **INFO** | General progress | Pipeline start/complete, API calls |
| **WARNING** | Recoverable issues | TMX file not found, missing locale |
| **ERROR** | Failures requiring attention | API timeout, invalid JSON |
| **CRITICAL** | System-level failures | Cannot connect to OpenAI, disk full |

### Example Log Output

```
2026-06-26 10:15:23 [    INFO] main - ========================================
2026-06-26 10:15:23 [    INFO] main - 🚀 Initializing LQA Pipeline [en-US]
2026-06-26 10:15:23 [    INFO] main - ========================================
2026-06-26 10:15:26 [    INFO] batch_parser - Parsed: index_en-US.html
2026-06-26 10:15:27 [    INFO] align_elements - Aligned 42 elements
2026-06-26 10:15:45 [    INFO] main - 📊 Runtime Token Usage
2026-06-26 10:15:45 [    INFO] main - Prompt Tokens: 8,543
2026-06-26 10:15:45 [    INFO] main - Completion Tokens: 2,187
2026-06-26 10:15:46 [    INFO] tmx_matcher - [TMX MATCH] ERR_001: matched to 'calcio_title' (score: 0.92)
2026-06-26 10:15:46 [    INFO] main - 🎉 Pipeline Complete!
2026-06-26 10:15:46 [    INFO] main - Score: 85/100
2026-06-26 10:15:46 [    INFO] main - Errors Found: 3
```

---

## 🚀 Deployment Guide

### Local Development

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set environment variables
export LLM_API_KEY="sk-..."
export LLM_MODEL_NAME="gpt-4o-mini"
export LOG_LEVEL="INFO"

# 3. Generate HTML templates
python generate_pages.py

# 4. Run dashboard
cd dashboards
python server.py

# 5. Open browser
# http://127.0.0.1:8000
```

### Production Deployment (Recommendations)

```yaml
# docker-compose.yml (example)
version: '3.8'
services:
  lqa-dashboard:
    build: ..
    ports:
      - "8000:8000"
    environment:
      - LLM_API_KEY=${LLM_API_KEY}
      - LOG_LEVEL=INFO
    volumes:
      - ./outputs:/app/outputs
      - ./logs:/app/logs
      - ./memory.xml:/app/memory.xml
```

---

## 📞 Support & Contribution

**Project**: L10N Hackathon 2026  
**Author**: Kaja Braz  
**Repository**: (Add GitHub link if applicable)

### Key Contacts

- **Technical Issues**: Check logs in `logs/lqa_errors_*.log`
- **TMX Questions**: See `tmx_matcher.py` docstrings
- **API Reference**: `dashboards/server.py` endpoint comments

---

## 🎓 References

- **MQM Framework**: https://themqm.org/
- **TMX Specification**: https://www.gala-global.org/tmx-14b
- **FastAPI Docs**: https://fastapi.tiangolo.com/
- **Pydantic Guide**: https://docs.pydantic.dev/

---

## ⚠️ Development Disclaimer

This project was developed with AI assistance:
- **AI Tools Used**: Google Gemini and Anthropic Claude
- **AI Role**: Code implementation, architecture design, documentation, testing, debugging
- **Human Role**: All design decisions, feature requirements, quality standards, and project direction

The AI tools served as pair programming assistants and technical writing aids throughout the development process.

---

**Document Version**: 1.0  
**Last Updated**: 2026-06-26  
**Status**: Complete & Production-Ready Documentation
