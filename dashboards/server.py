import glob
import json
import os
import subprocess
import sys
import threading
import uuid
from datetime import datetime
from typing import List, Dict, Optional

# Add parent directory to path to import tmx_matcher
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import uvicorn
from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from tmx_matcher import TMXParser, TMXMatcher, enrich_lqa_report_with_tmx
from cost_estimator import estimate_evaluation_cost, get_available_models

app = FastAPI(title="Boutique Italia - Content-Aware LQA Gateway")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Get absolute path to project root (parent of dashboards directory)
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

OUTPUT_DIR = os.path.join(PROJECT_ROOT, "outputs")
EXTRACTED_DIR = os.path.join(PROJECT_ROOT, "extracted_data")
TEMPLATES_DIR = os.path.join(PROJECT_ROOT, "templates")  # Directory where index_*.html lives
LOCALES_DIR = os.path.join(PROJECT_ROOT, "locales")  # Directory where locale JSON resource files live
GENERATE_SCRIPT = os.path.join(PROJECT_ROOT, "generate_pages.py")  # Template generation script
TMX_FILE = os.path.join(PROJECT_ROOT, "memory.xml")  # TMX translation memory file

# Global TMX parser instance (loaded once at startup)
_tmx_parser = None
_tmx_matcher = None

# Global evaluation tasks tracker
evaluation_tasks: Dict[str, Dict] = {}
evaluation_lock = threading.Lock()


class ApprovalPayload(BaseModel):
    locale: str
    error_id: str
    dom_path: str
    source_text: str
    approved_translation: str
    html_element_id: str = ""
    target_text_snippet: str = ""


class EvaluationRequest(BaseModel):
    locales: List[str]
    tmx_threshold: float = 0.4
    model: Optional[str] = None  # Model selection


class CostEstimationRequest(BaseModel):
    locales: List[str]
    model: str


def get_tmx_parser():
    """Get or initialize the TMX parser (singleton pattern)"""
    global _tmx_parser, _tmx_matcher
    if _tmx_parser is None and os.path.exists(TMX_FILE):
        try:
            _tmx_parser = TMXParser(TMX_FILE)
            _tmx_matcher = TMXMatcher(_tmx_parser)
            print(f"[TMX] Loaded {len(_tmx_parser.entries)} translation units")
        except Exception as e:
            print(f"[TMX ERROR] Failed to load TMX file: {e}")
    return _tmx_parser, _tmx_matcher


@app.get("/")
def read_dashboard():
    if not os.path.exists("index.html"):
        raise HTTPException(status_code=404, detail="index.html not found.")
    return FileResponse("index.html")


@app.get("/api/locales")
def get_available_locales():
    search_pattern = os.path.join(OUTPUT_DIR, "lqa_audit_report_it-IT_*.json")
    found_files = glob.glob(search_pattern)
    locales = []
    for file_path in found_files:
        filename = os.path.basename(file_path)
        parts = filename.replace("lqa_audit_report_it-IT_", "").replace(".json", "")
        if parts:
            locales.append(parts)
    if not locales:
        return ["en-US", "de-DE"]  # Fallback for demo stability
    return sorted(locales)


@app.get("/api/report/{locale}")
def get_lqa_combined_data(locale: str):
    print(f"[API] get_lqa_combined_data called for locale: {locale}")
    report_file = os.path.join(OUTPUT_DIR, f"lqa_audit_report_it-IT_{locale}.json")
    locale_json_file = os.path.join(LOCALES_DIR, f"{locale}.json")
    print(f"[API] Report file: {report_file}, exists: {os.path.exists(report_file)}")

    # 1. Load Locale JSON data (the source of truth for translations)
    locale_data = None
    if os.path.exists(locale_json_file):
        with open(locale_json_file, "r", encoding="utf-8") as f:
            locale_data = json.load(f)

    # 2. Convert locale JSON to page_content structure for dashboard rendering
    webpage_strings = []
    if locale_data:
        # Add meta fields (header)
        webpage_strings.append({
            "tag": "h1",
            "content": locale_data["meta"]["title"],
            "closest_anchor_id": None
        })
        webpage_strings.append({
            "tag": "p",
            "content": locale_data["meta"]["subtitle"],
            "closest_anchor_id": None,
            "parent_node": {"tag": "header"}
        })

        # Add promo banner fields
        webpage_strings.append({
            "tag": "span",
            "content": locale_data["meta"]["promo_label"],
            "closest_anchor_id": {"id": "global_banner"},
            "parent_node": {"tag": "div", "attributes": {"class": "promo-banner"}}
        })
        webpage_strings.append({
            "tag": "span",
            "content": locale_data["meta"]["promo_date"],
            "closest_anchor_id": {"id": "global_banner"},
            "parent_node": {"tag": "div", "attributes": {"class": "promo-banner"}}
        })

        # Add section cards
        for section_id, section_data in locale_data["sections"].items():
            webpage_strings.append({
                "tag": "h2",
                "content": section_data["title"],
                "closest_anchor_id": {"id": section_id}
            })
            webpage_strings.append({
                "tag": "p",
                "content": section_data["description"],
                "closest_anchor_id": {"id": section_id},
                "parent_node": {"tag": "div"}
            })
            webpage_strings.append({
                "tag": "img",
                "content": section_data["img_alt"],
                "attributes": {"alt": section_data["img_alt"]},
                "closest_anchor_id": {"id": section_id}
            })
            # Add price (formatted)
            currency_format = locale_data["meta"]["currency_format"]
            price_formatted = currency_format.format(price=section_data["price_value"])
            webpage_strings.append({
                "tag": "span",
                "content": price_formatted,
                "attributes": {"class": "meta-price"},
                "closest_anchor_id": {"id": section_id}
            })
    else:
        # High-fidelity fallback layout ensuring both content grid and global components adapt
        if locale == "de-DE":
            webpage_strings = [
                {"tag": "h1", "content": "Boutique Italia - Tolle Erlebnisse", "closest_anchor_id": None},
                {"tag": "p", "content": "Entdecken Sie die Seele Italiens.", "closest_anchor_id": None,
                 "parent_node": {"tag": "header"}},
                {"tag": "h2", "content": "Besonderes Frühbucherangebot gültig bis",
                 "closest_anchor_id": {"id": "global_banner"}},
                {"tag": "span", "content": "15.08.2026", "closest_anchor_id": {"id": "global_banner"}},
                {"tag": "h2", "content": "Siena Palio Erlebnisse", "closest_anchor_id": {"id": "palio"}},
                {"tag": "p", "content": "Erleben Sie das traditionelle Pferderennen.",
                 "closest_anchor_id": {"id": "palio"}, "parent_node": {"tag": "div"}},
                {"tag": "h2", "content": "Automobil-Valley-Superautos", "closest_anchor_id": {"id": "macchine"}},
                {"tag": "p", "content": "Besuchen Sie Luxus-Fertigungsräume.", "closest_anchor_id": {"id": "macchine"},
                 "parent_node": {"tag": "div"}}
            ]
        else:
            webpage_strings = [
                {"tag": "h1", "content": "Boutique Italia - Grand Experiences", "closest_anchor_id": None},
                {"tag": "p", "content": "Explore the authentic soul of the Italian peninsula.",
                 "closest_anchor_id": None, "parent_node": {"tag": "header"}},
                {"tag": "h2", "content": "Special early bird offer valid until",
                 "closest_anchor_id": {"id": "global_banner"}},
                {"tag": "span", "content": "15/08/2026", "closest_anchor_id": {"id": "global_banner"}},
                {"tag": "h2", "content": "Siena Palio Experience", "closest_anchor_id": {"id": "palio"}},
                {"tag": "p", "content": "Experience the thrilling horse race.", "closest_anchor_id": {"id": "palio"},
                 "parent_node": {"tag": "div"}},
                {"tag": "h2", "content": "Historical Calcium Match", "closest_anchor_id": {"id": "calcio"}},
                {"tag": "p", "content": "Watch the brutal elegance of early historic football.",
                 "closest_anchor_id": {"id": "calcio"}, "parent_node": {"tag": "div"}}
            ]

    # 2. Load LQA Issue Metrics
    lqa_report = {"global_score": 100, "summary": {"total_errors": 0}, "detected_errors": []}
    if os.path.exists(report_file):
        print(f"[DEBUG] Loading report from: {report_file}")
        with open(report_file, "r", encoding="utf-8") as f:
            lqa_report = json.load(f)
        print(f"[DEBUG] Loaded {len(lqa_report.get('detected_errors', []))} errors")

        # 3. Automatically enrich with TMX data if TMX is available
        print(
            f"[DEBUG] TMX_FILE exists: {os.path.exists(TMX_FILE)}, has errors: {bool(lqa_report.get('detected_errors'))}")
        if os.path.exists(TMX_FILE) and lqa_report.get("detected_errors"):
            try:
                print(f"[DEBUG] Starting TMX enrichment for {locale}...")
                lqa_report = enrich_lqa_report_with_tmx(
                    lqa_report,
                    TMX_FILE,
                    source_locale="it-IT",
                    target_locale=locale,
                    threshold=0.4
                )
                print(
                    f"[TMX] Enriched {locale} report: {lqa_report.get('tmx_metadata', {}).get('errors_matched', 0)}/{lqa_report.get('tmx_metadata', {}).get('errors_total', 0)} matches")
            except Exception as e:
                print(f"[TMX WARNING] Failed to enrich report for {locale}: {e}")
                import traceback
                traceback.print_exc()
    else:
        if locale == "de-DE":
            lqa_report = {
                "global_score": 94, "summary": {"total_errors": 1},
                "detected_errors": [{
                    "error_id": "ERR_002", "html_element_id": "macchine", "mqm_category": "Fluency",
                    "severity": "Major",
                    "dom_path": "html:nth-of-type(1) > body:nth-of-type(1) > div:nth-of-type(1) > main:nth-of-type(1) > article:nth-of-type(7) > h3:nth-of-type(1)",
                    "source_text_snippet": "Motor Valley Supercars",
                    "target_text_snippet": "Automobil-Valley-Superautos",
                    "issue_explanation": "Unnatural compound structure for high-end German branding.",
                    "suggested_fix": "Supercars aus dem Motor Valley"
                }]
            }
        elif locale == "en-US":
            lqa_report = {
                "global_score": 85, "summary": {"total_errors": 1},
                "detected_errors": [{
                    "error_id": "ERR_001", "html_element_id": "calcio", "mqm_category": "Accuracy",
                    "severity": "Critical",
                    "dom_path": "html:nth-of-type(1) > body:nth-of-type(1) > div:nth-of-type(1) > main:nth-of-type(1) > article:nth-of-type(2) > h3:nth-of-type(1)",
                    "source_text_snippet": "Calcio Storico", "target_text_snippet": "Historical Calcium Match",
                    "issue_explanation": "Catastrophic mistranslation of 'Calcio' as a chemical element instead of soccer.",
                    "suggested_fix": "Historic Soccer Match"
                }]
            }

    return {
        "lqa": lqa_report,
        "page_content": webpage_strings
    }


@app.post("/api/approve")
def approve_fix(payload: ApprovalPayload):
    fixes_path = os.path.join(OUTPUT_DIR, f"approved_fixes_{payload.locale}.json")
    fixes = []
    if os.path.exists(fixes_path):
        with open(fixes_path, "r", encoding="utf-8") as f:
            try:
                fixes = json.load(f)
            except json.JSONDecodeError:
                fixes = []

    # Avoid duplicate registrations for the same error item
    fixes = [f for f in fixes if f.get('error_id') != payload.error_id]
    fixes.append(payload.model_dump())

    with open(fixes_path, "w", encoding="utf-8") as f:
        json.dump(fixes, f, indent=2, ensure_ascii=False)
    print(f"[LIVE AUDIT] [{payload.locale}] Fix recorded for {payload.error_id}!")
    return {"status": "success"}


@app.post("/api/reject")
def reject_issue(payload: dict):
    """
    Track rejected issues for reporting/analytics purposes.
    These are NOT applied to templates - they're just logged.
    """
    locale = payload.get("locale")
    error_id = payload.get("error_id")

    rejections_path = os.path.join(OUTPUT_DIR, f"rejected_issues_{locale}.json")
    rejections = []
    if os.path.exists(rejections_path):
        with open(rejections_path, "r", encoding="utf-8") as f:
            try:
                rejections = json.load(f)
            except json.JSONDecodeError:
                rejections = []

    # Avoid duplicates
    rejections = [r for r in rejections if r.get('error_id') != error_id]
    rejections.append(payload)

    with open(rejections_path, "w", encoding="utf-8") as f:
        json.dump(rejections, f, indent=2, ensure_ascii=False)

    print(f"[LIVE AUDIT] [{locale}] Issue rejected: {error_id}")
    return {"status": "success"}


def map_element_to_locale_key(html_element_id: str, dom_path: str, target_text: str, approved_translation: str,
                              locale_data: dict):
    """
    Maps HTML element ID, DOM path, and target text to the corresponding key path in locale JSON.
    Returns tuple: (section_key, field_key) or (None, None) if not found.

    Args:
        html_element_id: The ID of the HTML element containing the error
        dom_path: CSS selector path to the element
        target_text: The current (flawed) target text that needs to be replaced
        approved_translation: The corrected translation
        locale_data: The current locale JSON data
    """
    # Handle meta fields (header, promo banner)
    if html_element_id == "global_banner":
        # Check if it's the promo label or date based on content
        if any(char.isdigit() for char in target_text) and any(char.isdigit() for char in approved_translation):
            return "meta", "promo_date"
        else:
            return "meta", "promo_label"

    # Handle header elements
    if not html_element_id or html_element_id in ["live-webpage-title", "emulated-site-title"]:
        return "meta", "title"

    if not html_element_id or html_element_id in ["live-webpage-subtitle", "emulated-site-subtitle"]:
        return "meta", "subtitle"

    # Handle section-specific elements
    section_ids = ["palio", "calcio", "natura", "film", "feste", "esperienze", "macchine", "musica"]
    if html_element_id in section_ids:
        section_data = locale_data.get("sections", {}).get(html_element_id, {})

        if not section_data:
            return None, None

        # Use DOM path to determine field type
        # h2/h3 tags are typically titles
        if "h2" in dom_path.lower() or "h3" in dom_path.lower():
            return html_element_id, "title"

        # p tags are typically descriptions
        elif "p" in dom_path.lower():
            # If the target text matches the description, it's a description
            if "description" in section_data:
                current_desc = section_data["description"]
                # Check if significant overlap with current description
                if target_text.lower() in current_desc.lower() or current_desc.lower() in target_text.lower():
                    return html_element_id, "description"
            return html_element_id, "description"

        # img tags with alt attributes
        elif "img" in dom_path.lower():
            return html_element_id, "img_alt"

        # Fallback: try to match based on target text content
        for field_key in ["title", "description", "img_alt"]:
            if field_key in section_data:
                field_value = section_data[field_key]
                # Normalize and compare
                normalized_target = " ".join(target_text.split()).lower()
                normalized_field = " ".join(field_value.split()).lower()

                # Exact match
                if normalized_target == normalized_field:
                    return html_element_id, field_key

                # Substring match (either direction)
                if normalized_target in normalized_field or normalized_field in normalized_target:
                    return html_element_id, field_key

    return None, None


@app.get("/api/tmx/info")
def get_tmx_info():
    """Get information about the loaded TMX translation memory"""
    parser, matcher = get_tmx_parser()

    if parser is None:
        return {
            "loaded": False,
            "error": "TMX file not found or failed to load"
        }

    return {
        "loaded": True,
        "total_entries": len(parser.entries),
        "source_locale": parser.source_locale,
        "sample_tuids": [entry.tuid for entry in parser.entries[:10]],
        "tmx_file": TMX_FILE
    }


@app.get("/api/tmx/entry/{tuid}")
def get_tmx_entry(tuid: str):
    """Get a specific TMX entry by its translation unit ID"""
    parser, matcher = get_tmx_parser()

    if parser is None:
        raise HTTPException(status_code=503, detail="TMX not loaded")

    entry = parser.find_entry_by_tuid(tuid)

    if entry is None:
        raise HTTPException(status_code=404, detail=f"TMX entry '{tuid}' not found")

    return {
        "tuid": entry.tuid,
        "translations": entry.translations
    }


@app.get("/api/tmx/match")
def find_tmx_match(
        source_text: str = Query(..., description="Source language text"),
        target_text: str = Query(..., description="Target language text"),
        source_locale: str = Query("it-IT", description="Source locale code"),
        target_locale: str = Query("en-US", description="Target locale code"),
        threshold: float = Query(0.5, ge=0.0, le=1.0, description="Similarity threshold")
):
    """Find the best TMX match for given source and target texts"""
    parser, matcher = get_tmx_parser()

    if matcher is None:
        raise HTTPException(status_code=503, detail="TMX matcher not initialized")

    match_result = matcher.find_best_match(
        source_text,
        target_text,
        source_locale,
        target_locale,
        threshold
    )

    if match_result is None:
        return {
            "match_found": False,
            "message": f"No match found above threshold {threshold}"
        }

    tmx_entry, similarity, match_type = match_result

    return {
        "match_found": True,
        "tuid": tmx_entry.tuid,
        "similarity_score": round(similarity, 3),
        "match_type": match_type,
        "tmx_source_text": tmx_entry.get_translation(source_locale),
        "tmx_target_text": tmx_entry.get_translation(target_locale),
        "all_translations": tmx_entry.translations
    }


@app.post("/api/tmx/enrich/{locale}")
def enrich_report_with_tmx(
        locale: str,
        threshold: float = Query(0.4, ge=0.0, le=1.0, description="Matching threshold")
):
    """
    Enrich an existing LQA report with TMX match data.
    This can be run on-demand to add/update TMX matches.
    """
    report_file = os.path.join(OUTPUT_DIR, f"lqa_audit_report_it-IT_{locale}.json")

    if not os.path.exists(report_file):
        raise HTTPException(status_code=404, detail=f"Report file not found for locale '{locale}'")

    if not os.path.exists(TMX_FILE):
        raise HTTPException(status_code=404, detail="TMX file not found")

    try:
        # Load existing report
        with open(report_file, 'r', encoding='utf-8') as f:
            report = json.load(f)

        # Enrich with TMX data
        enriched_report = enrich_lqa_report_with_tmx(
            report,
            TMX_FILE,
            source_locale="it-IT",
            target_locale=locale,
            threshold=threshold
        )

        # Save enriched report
        enriched_file = report_file.replace('.json', '_tmx_enriched.json')
        with open(enriched_file, 'w', encoding='utf-8') as f:
            json.dump(enriched_report, f, indent=2, ensure_ascii=False)

        return {
            "status": "success",
            "enriched_file": enriched_file,
            "tmx_metadata": enriched_report.get('tmx_metadata', {}),
            "message": f"Report enriched with TMX data. Matched {enriched_report['tmx_metadata']['errors_matched']} out of {enriched_report['tmx_metadata']['errors_total']} errors."
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to enrich report: {str(e)}")


@app.post("/api/rebuild/{locale}")
def rebuild_localization_template(locale: str):
    """
    Updates the locale JSON resource file with approved fixes,
    then runs generate_pages.py to regenerate the HTML templates.
    """
    try:
        fixes_path = os.path.join(OUTPUT_DIR, f"approved_fixes_{locale}.json")
        locale_json_path = os.path.join(LOCALES_DIR, f"{locale}.json")

        if not os.path.exists(fixes_path):
            raise HTTPException(status_code=400,
                                detail=f"No approved fixes found for locale '{locale}'. Please approve at least one fix before rebuilding.")

        if not os.path.exists(locale_json_path):
            raise HTTPException(status_code=404,
                                detail=f"Locale resource file not found: {locale_json_path}\nPlease ensure the locale JSON file exists in the locales directory.")

        # 1. Load approved string adjustments
        print(f"[REBUILD] Loading fixes from: {fixes_path}")
        with open(fixes_path, "r", encoding="utf-8") as f:
            approved_fixes = json.load(f)
        print(f"[REBUILD] Loaded {len(approved_fixes)} fixes")

        # 2. Load current locale JSON data
        print(f"[REBUILD] Loading locale data from: {locale_json_path}")
        with open(locale_json_path, "r", encoding="utf-8") as f:
            locale_data = json.load(f)

        applied_count = 0

        # 3. Apply fixes to locale JSON structure
        for fix in approved_fixes:
            html_element_id = fix.get("html_element_id", "")
            dom_path = fix.get("dom_path", "")
            target_text = fix.get("target_text_snippet", fix.get("source_text", ""))
            new_text = fix["approved_translation"]

            print(f"[REBUILD] Processing fix: {fix.get('error_id')} - element: {html_element_id}")

            # Map element to JSON key path
            try:
                section_key, field_key = map_element_to_locale_key(html_element_id, dom_path, target_text, new_text,
                                                                   locale_data)
            except Exception as e:
                print(f"[REBUILD ERROR] Failed to map element: {e}")
                import traceback
                traceback.print_exc()
                raise HTTPException(status_code=500,
                                    detail=f"Failed to map element for {fix.get('error_id')}: {str(e)}")

            if section_key and field_key:
                if section_key == "meta":
                    locale_data["meta"][field_key] = new_text
                    applied_count += 1
                    print(f"[LOCALE UPDATE] Updated meta.{field_key} (length: {len(new_text)} chars)")
                elif section_key in locale_data.get("sections", {}):
                    locale_data["sections"][section_key][field_key] = new_text
                    applied_count += 1
                    print(f"[LOCALE UPDATE] Updated sections.{section_key}.{field_key} (length: {len(new_text)} chars)")
            else:
                print(
                    f"[LOCALE WARNING] Could not map fix for element '{html_element_id}'")

        # 4. Save updated locale JSON
        print(f"[REBUILD] Saving updated locale data...")
        with open(locale_json_path, "w", encoding="utf-8") as f:
            json.dump(locale_data, f, indent=2, ensure_ascii=False)

        print(f"[LOCALE WRITE-BACK SUCCESS] Updated {applied_count} strings in '{locale_json_path}'")

        # 5. Run generate_pages.py to regenerate templates
        print(f"[REBUILD] Running template generation...")
        try:
            # Change to parent directory to run the script
            parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
            result = subprocess.run(
                ["python", "generate_pages.py"],
                cwd=parent_dir,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                print(f"[TEMPLATE GENERATION SUCCESS] {result.stdout}")
                return {
                    "status": "success",
                    "patched_elements": applied_count,
                    "locale": locale,
                    "template_generation_output": result.stdout.strip()
                }
            else:
                print(f"[TEMPLATE GENERATION ERROR] {result.stderr}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Template generation failed: {result.stderr}"
                )
        except subprocess.TimeoutExpired:
            raise HTTPException(status_code=500, detail="Template generation timed out.")
        except Exception as e:
            print(f"[REBUILD ERROR] Subprocess exception: {e}")
            import traceback
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=f"Failed to run template generation: {str(e)}")

    except HTTPException:
        raise
    except Exception as e:
        print(f"[REBUILD FATAL ERROR] {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Rebuild failed: {str(e)}")


def run_evaluation_for_locale(locale: str, task_id: str, model: Optional[str] = None, is_first: bool = False):
    """
    Run LQA evaluation for a single locale.

    Note: main.py internally calls process_localization_templates() which scrapes
    the HTML templates and creates extracted_data/index_{locale}.json files.
    This happens on EVERY call to main.py, but it's fast (~3s) and idempotent.

    For the first locale, we show "scraping" phase briefly, then switch to "evaluating".
    """
    try:
        print(f"[EVALUATION] Starting evaluation for {locale} (task: {task_id})")

        # Show scraping phase for first locale (main.py will do this internally)
        if is_first:
            with evaluation_lock:
                evaluation_tasks[task_id]["current_locale"] = locale
                evaluation_tasks[task_id]["current_phase"] = "scraping"
                evaluation_tasks[task_id]["phase_status"] = f"Extracting elements (during {locale} evaluation)..."
                evaluation_tasks[task_id]["status"] = "running"

        # After a brief moment, switch to evaluating phase
        with evaluation_lock:
            evaluation_tasks[task_id]["current_locale"] = locale
            evaluation_tasks[task_id]["current_phase"] = "evaluating"
            evaluation_tasks[task_id]["phase_status"] = f"Evaluating {locale}..."
            evaluation_tasks[task_id]["status"] = "running"
            if is_first:
                evaluation_tasks[task_id]["scraping_complete"] = True

        # Run main.py evaluation logic
        # This internally calls process_localization_templates() + alignment + LLM evaluation
        parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

        # Build environment with model override if provided
        env = {**os.environ, "TARGET_LOCALE": locale}
        if model:
            env["LLM_MODEL_NAME"] = model

        result = subprocess.run(
            ["python", "main.py"],
            cwd=parent_dir,
            env=env,
            capture_output=True,
            text=True,
            timeout=300  # 5 minutes timeout
        )

        if result.returncode == 0:
            print(f"[EVALUATION] Success for {locale}")
            with evaluation_lock:
                evaluation_tasks[task_id]["completed_locales"].append(locale)
                evaluation_tasks[task_id]["results"][locale] = {"status": "success", "output": result.stdout}
        else:
            print(f"[EVALUATION] Failed for {locale}: {result.stderr}")
            with evaluation_lock:
                evaluation_tasks[task_id]["completed_locales"].append(locale)
                evaluation_tasks[task_id]["results"][locale] = {"status": "error", "error": result.stderr}

    except Exception as e:
        print(f"[EVALUATION] Exception for {locale}: {e}")
        with evaluation_lock:
            evaluation_tasks[task_id]["completed_locales"].append(locale)
            evaluation_tasks[task_id]["results"][locale] = {"status": "error", "error": str(e)}


def run_evaluation_task(locales: List[str], task_id: str, model: Optional[str] = None):
    """
    Background task to evaluate multiple locales.

    Architecture note:
    - Each call to main.py internally runs process_localization_templates() (scraping)
    - This extracts HTML content into extracted_data/index_{locale}.json files
    - Scraping is fast (~3s) and idempotent (safe to run multiple times)
    - Then main.py does alignment + LLM evaluation (~30-60s per locale)

    We don't need a separate scraping phase because:
    1. It's already built into main.py (line 70: process_localization_templates())
    2. It's fast enough to not need separate tracking
    3. Running it multiple times is safe (it just overwrites the same extracted files)

    For UI purposes, we briefly show "scraping" during the first locale, then "evaluating".
    """
    try:
        with evaluation_lock:
            evaluation_tasks[task_id]["status"] = "running"
            evaluation_tasks[task_id]["started_at"] = datetime.now().isoformat()

        # Evaluate each locale
        # The first locale will show scraping phase briefly (main.py does this internally)
        for idx, locale in enumerate(locales):
            is_first = (idx == 0)
            run_evaluation_for_locale(locale, task_id, model, is_first=is_first)

        with evaluation_lock:
            evaluation_tasks[task_id]["status"] = "completed"
            evaluation_tasks[task_id]["completed_at"] = datetime.now().isoformat()

        print(f"[EVALUATION] Task {task_id} completed")

    except Exception as e:
        print(f"[EVALUATION] Task {task_id} failed: {e}")
        with evaluation_lock:
            evaluation_tasks[task_id]["status"] = "failed"
            evaluation_tasks[task_id]["error"] = str(e)


@app.get("/api/models")
def get_available_models_list():
    """
    Get list of available models for evaluation.
    """
    try:
        models = get_available_models()
        return {
            "models": models,
            "total": len(models)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get models: {str(e)}")


@app.post("/api/estimate-cost")
def estimate_cost(request: CostEstimationRequest):
    """
    Estimate the cost of evaluating selected locales with a given model.
    """
    try:
        extracted_dir = os.path.join(PROJECT_ROOT, "extracted_data")
        estimate = estimate_evaluation_cost(
            request.locales,
            request.model,
            extracted_dir
        )
        return estimate
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cost estimation failed: {str(e)}")


@app.post("/api/evaluate")
async def start_evaluation(request: EvaluationRequest, background_tasks: BackgroundTasks):
    """
    Start evaluation for selected locales.
    Runs main.py in the background for each locale.
    """
    if not request.locales:
        raise HTTPException(status_code=400, detail="No locales selected")

    # Generate unique task ID
    task_id = str(uuid.uuid4())[:8]

    # Initialize task tracking
    with evaluation_lock:
        evaluation_tasks[task_id] = {
            "task_id": task_id,
            "locales": request.locales,
            "total": len(request.locales),
            "completed_locales": [],
            "current_locale": None,
            "current_phase": "starting",
            "phase_status": "Initializing...",
            "scraping_complete": False,
            "status": "starting",
            "model": request.model or os.environ.get("LLM_MODEL_NAME", "gpt-4o-mini"),
            "created_at": datetime.now().isoformat(),
            "started_at": None,
            "completed_at": None,
            "results": {}
        }

    # Start background task
    background_tasks.add_task(run_evaluation_task, request.locales, task_id, request.model)

    print(f"[EVALUATION] Started task {task_id} for locales: {request.locales}, model: {request.model}")

    return {
        "task_id": task_id,
        "status": "started",
        "locales": request.locales,
        "model": request.model,
        "message": f"Evaluation started for {len(request.locales)} locale(s)"
    }


@app.get("/api/evaluate/status/{task_id}")
def get_evaluation_status(task_id: str):
    """Get the status of an evaluation task"""
    with evaluation_lock:
        if task_id not in evaluation_tasks:
            raise HTTPException(status_code=404, detail="Task not found")

        task = evaluation_tasks[task_id]

        # Calculate progress with two phases
        # Phase 1 (scraping): 0-10% of total progress
        # Phase 2 (evaluation): 10-100% of total progress (split equally per locale)
        if task.get("current_phase") == "scraping":
            progress = 0.05  # 5% during scraping
        elif task.get("scraping_complete"):
            # Scraping done, now evaluating locales
            locale_progress = len(task["completed_locales"]) / task["total"] if task["total"] > 0 else 0
            progress = 0.10 + (locale_progress * 0.90)  # 10% base + 90% for locales
        else:
            progress = 0.0

        return {
            "task_id": task_id,
            "status": task["status"],
            "progress": round(progress, 2),
            "current_phase": task.get("current_phase", "starting"),
            "phase_status": task.get("phase_status", "Initializing..."),
            "scraping_complete": task.get("scraping_complete", False),
            "current_locale": task["current_locale"],
            "completed": len(task["completed_locales"]),
            "total": task["total"],
            "completed_locales": task["completed_locales"],
            "model": task.get("model", "N/A"),
            "results": task["results"],
            "created_at": task["created_at"],
            "started_at": task["started_at"],
            "completed_at": task["completed_at"]
        }


@app.get("/api/evaluate/tasks")
def list_evaluation_tasks():
    """List all evaluation tasks"""
    with evaluation_lock:
        return {
            "tasks": list(evaluation_tasks.values()),
            "total": len(evaluation_tasks)
        }


if __name__ == "__main__":
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=True)
