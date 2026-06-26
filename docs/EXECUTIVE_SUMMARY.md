# 🚀 LQA System - Executive Summary

**AI-Powered Localization Quality Assessment Dashboard**  
*L10N Hackathon 2026 Submission*

---

## 🎯 Problem & Solution

**Problem**: "Are We Fit for This Market?" - Need automated review of multilingual websites for linguistic quality, terminology consistency, and cultural adaptation.

**Solution**: End-to-end platform that ingests HTML, evaluates translations with AI, provides interactive review dashboard, and syncs with Translation Memory (TMX).

**Event Link**: https://custom.mt/mad-localization-hackathon/

---

## ✅ Requirements Met

### Core Features (Must-Have)
-  **Multilingual Website Ingestion** - HTML parsing with DOM tracking across 6+ locales
-  **Linguistic Quality Assessment** - AI-powered MQM evaluation (Accuracy, Fluency, Cultural Adaptation, Locale Conventions, Terminology)
-  **Report/Dashboard** - Interactive browser-like preview with error highlighting

### Advanced Features
-  **TMX Synchronization** - **Bidirectional** (reads + writes) with fuzzy matching
-  **Human Review & Approval** - One-click approve/reject → automatic template rebuild

### Bonus Features
-  **Easy locale addition** - Create JSON file, run one command → new localized page
-  Cost estimation before evaluation
-  Multi-model support (OpenAI, Mistral, Llama, DeepSeek)
-  Real-time progress tracking
-  Production logging & error handling
-  Unit tests

---

## 🏗️ Architecture

**Why Scraping & Alignment?**
- **Scraping**: Extract text + DOM paths from HTML so errors can be located precisely on the page
- **Alignment**: Match source (Italian) ↔ target text pairs so AI can evaluate translation quality

**3-Layer Design:**
```
Frontend (HTML/Tailwind) → API (FastAPI) → AI Engine (OpenAI)
                              ↓
                    TMX Memory (Bidirectional)
```

**Key Components:**
- `main.py` - LQA pipeline orchestrator
- `batch_parser.py` - HTML → structured JSON (extracts content + DOM paths for precise error location)
- `align_elements.py` - Source ↔ Target matching (pairs Italian text with translations for comparison)
- `tmx_matcher.py` - Translation memory read/write with fuzzy matching
- `dashboards/server.py` - FastAPI REST API (12 endpoints)

**Data Flow:**
```
HTML Templates → Parse → Align → LLM Evaluate → TMX Enrich → Dashboard
                                                     ↓
                                      Approve → Rebuild → Sync TMX 
```

---

## 💡 Key Assumptions

- **Source locale**: it-IT (Italian) is reference
- **HTML structure**: Consistent across locales for alignment
- **JSON as source of truth**: Updates modify JSON, not HTML directly
- **MQM scoring**: Industry standard (Minor=1pt, Major=5pt, Critical=10pt)
- **Fuzzy matching**: 40% threshold for TMX matches
- **Single-user**: No auth (acceptable for hackathon scope)

---

## 🌟 Unique Features

### 1. **Bidirectional TMX Sync** (Competitive Advantage!)
- Most solutions only READ from TMX
- **We WRITE back** approved fixes → translation memory learns over time
- Automatic timestamped backups before modification
- Creates new entries for unmatched fixes

### 2. **Cost Transparency**
- Pre-evaluation cost estimates per locale
- Compare pricing across 5+ LLM providers
- Helps users make informed decisions

### 3. **Easy Locale Addition** (Developer-Friendly!)
- Add new locale in 2 steps:
  1. Create `locales/fr-FR.json` (copy structure from it-IT)
  2. Run `python generate_pages.py` (auto-generates HTML)
- No code changes needed
- Instant template generation
- Scalable to 50+ locales

### 4. **Visual Context**
- Browser-like viewport showing translations in context
- Color-coded error highlighting (red/yellow/green)
- Side-by-side source reference

---

## 📊 Technical Specs

**Stack:**
- Python 3.8+, FastAPI, Pydantic, BeautifulSoup4, OpenAI SDK, Tailwind CSS

**Supported Locales:**
- it-IT (source), en-US, ja-JP, pl-PL, de-DE, pt-BR + extensible

**AI Models:**
- Configurable with URL and API key
- Infrastructure: OpenAI

**Evaluation Criteria:**
- MQM categories: Accuracy, Fluency, Locale Conventions, Cultural Adaptation, Terminology
- Severity levels: Critical (10pts), Major (5pts), Minor (1pt)
- Score: 100 - total_penalties

**Performance:**
- HTML scraping: ~3s for 6 locales
- LQA evaluation: ~30-60s per locale
- TMX matching: <10ms per error
- Dashboard load: <500ms

---

## Quick Reference

**Installation:**
```bash
pip install -r requirements.txt
export LLM_API_KEY="your-key"
python generate_pages.py
cd dashboards && python server.py
```

---

**Contact**: Kaja Braz | L10N Hackathon 2026  
**Repository**: https://github.com/KajaBraz/L10N_Hackathon

---

## Development Disclaimer

This project was developed with AI assistance (Google Gemini and Anthropic Claude) for code implementation, architecture design, documentation, testing, and debugging.

**All design decisions, feature requirements, and quality standards were directed by the human developer.** The AI tools served as pair programming assistants and technical writing aids.
