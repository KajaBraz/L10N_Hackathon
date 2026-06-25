import glob
import json
import os

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

OUTPUT_DIR = "../output"
EXTRACTED_DIR = "../extracted_data"


class ApprovalPayload(BaseModel):
    locale: str
    error_id: str
    dom_path: str
    source_text: str
    approved_translation: str


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

    content_file = os.path.join(OUTPUT_DIR, f"index_{locale}.json")
    if not os.path.exists(content_file):
        content_file = os.path.join(EXTRACTED_DIR, f"index_{locale}.json")

    # 1. Load Webpage Content Layout Structure
    webpage_strings = []
    if os.path.exists(content_file):
        with open(content_file, "r", encoding="utf-8") as f:
            webpage_strings = json.load(f)
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
                    "dom_path": "html > body > div > main > article#macchine > h3",
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
                    "dom_path": "html > body > div > main > article#calcio > h3",
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
    fixes.append(payload.model_dump())
    with open(fixes_path, "w", encoding="utf-8") as f:
        json.dump(fixes, f, indent=2, ensure_ascii=False)
    print(f"[LIVE AUDIT] [{payload.locale}] Fix recorded for {payload.error_id}!")
    return {"status": "success"}


if __name__ == "__main__":
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=True)
