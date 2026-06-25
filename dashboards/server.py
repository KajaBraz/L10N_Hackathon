import glob
import json
import os
import subprocess

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

app = FastAPI(title="Boutique Italia - Content-Aware LQA Gateway")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

OUTPUT_DIR = "../outputs"
EXTRACTED_DIR = "../extracted_data"
TEMPLATES_DIR = "../templates"  # Directory where index_*.html lives
LOCALES_DIR = "../locales"  # Directory where locale JSON resource files live
GENERATE_SCRIPT = "../generate_pages.py"  # Template generation script


class ApprovalPayload(BaseModel):
    locale: str
    error_id: str
    dom_path: str
    source_text: str
    approved_translation: str
    html_element_id: str = ""
    target_text_snippet: str = ""


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
    report_file = os.path.join(OUTPUT_DIR, f"lqa_audit_report_it-IT_{locale}.json")
    locale_json_file = os.path.join(LOCALES_DIR, f"{locale}.json")

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
        with open(report_file, "r", encoding="utf-8") as f:
            lqa_report = json.load(f)
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


@app.post("/api/rebuild/{locale}")
def rebuild_localization_template(locale: str):
    """
    Updates the locale JSON resource file with approved fixes,
    then runs generate_pages.py to regenerate the HTML templates.
    """
    fixes_path = os.path.join(OUTPUT_DIR, f"approved_fixes_{locale}.json")
    locale_json_path = os.path.join(LOCALES_DIR, f"{locale}.json")

    if not os.path.exists(fixes_path):
        raise HTTPException(status_code=400,
                            detail=f"No approved fixes found for locale '{locale}'. Please approve at least one fix before rebuilding.")

    if not os.path.exists(locale_json_path):
        raise HTTPException(status_code=404,
                            detail=f"Locale resource file not found: {locale_json_path}\nPlease ensure the locale JSON file exists in the locales directory.")

    # 1. Load approved string adjustments
    with open(fixes_path, "r", encoding="utf-8") as f:
        approved_fixes = json.load(f)

    # 2. Load current locale JSON data
    with open(locale_json_path, "r", encoding="utf-8") as f:
        locale_data = json.load(f)

    applied_count = 0

    # 3. Apply fixes to locale JSON structure
    for fix in approved_fixes:
        html_element_id = fix.get("html_element_id", "")
        dom_path = fix.get("dom_path", "")
        target_text = fix.get("target_text_snippet", fix.get("source_text", ""))
        new_text = fix["approved_translation"]

        # Map element to JSON key path
        section_key, field_key = map_element_to_locale_key(html_element_id, dom_path, target_text, new_text,
                                                           locale_data)

        if section_key and field_key:
            if section_key == "meta":
                locale_data["meta"][field_key] = new_text
                applied_count += 1
                print(f"[LOCALE UPDATE] Updated meta.{field_key} = '{new_text}'")
            elif section_key in locale_data.get("sections", {}):
                locale_data["sections"][section_key][field_key] = new_text
                applied_count += 1
                print(f"[LOCALE UPDATE] Updated sections.{section_key}.{field_key} = '{new_text}'")
        else:
            print(
                f"[LOCALE WARNING] Could not map fix for element '{html_element_id}' with target text '{target_text[:50]}...'")

    # 4. Save updated locale JSON
    with open(locale_json_path, "w", encoding="utf-8") as f:
        json.dump(locale_data, f, indent=2, ensure_ascii=False)

    print(f"[LOCALE WRITE-BACK SUCCESS] Updated {applied_count} strings in '{locale_json_path}'")

    # 5. Run generate_pages.py to regenerate templates
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
                "locale_file_updated": locale_json_path,
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
        raise HTTPException(status_code=500, detail=f"Failed to run template generation: {str(e)}")


if __name__ == "__main__":
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=True)
