import io
import json
import os
from typing import List, Literal, Optional

from openai import OpenAI
from pydantic import BaseModel, Field

# Import your custom modules
from align_elements import align_localization_payloads
from batch_parser import process_localization_templates
from prompt.compile_prompt import compile_generic_prompt
from prompt.locale_profiles import LOCALE_PROFILES
from tmx_matcher import enrich_lqa_report_with_tmx


# ==========================================
# 1. DEFINE STRUCTURED OUTPUT SCHEMAS
# ==========================================
class TMXMatchInfo(BaseModel):
    tuid: str = Field(description="Translation Memory Unit ID from TMX file")
    similarity_score: float = Field(description="Fuzzy match score between 0.0 and 1.0")
    match_type: str = Field(description="Type of match: 'source', 'target', 'both', or 'fuzzy'")
    tmx_source_text: str = Field(description="Source text from TMX entry")
    tmx_target_text: str = Field(description="Target text from TMX entry")
    available_locales: List[str] = Field(description="List of available locales in this TMX entry")


class ErrorDetail(BaseModel):
    error_id: str = Field(description="Unique error sequence string, e.g., ERR_001")
    html_element_id: str = Field(description="The structural HTML ID anchor from the input, e.g., 'calcio'")
    dom_path: str = Field(description="The exact query selector string copied from the input item")
    mqm_category: str = Field(
        description="Locale Convention, Terminology, Cultural Transcreation, Accuracy, or Fluency")
    severity: Literal["Minor", "Major", "Critical"]
    source_text_snippet: str = Field(description="The original source language string context")
    target_text_snippet: str = Field(description="The flawed translated target string found")
    issue_explanation: str = Field(
        description="Clear architectural evaluation of why this fails for the target locale context.")
    suggested_fix: str = Field(description="Corrected text ready for live production hotfix deployment.")
    tmx_match: Optional[TMXMatchInfo] = Field(default=None, description="TMX translation memory match information")


class LqaSummary(BaseModel):
    total_errors: int
    critical: int
    major: int
    minor: int


class LqaReportSchema(BaseModel):
    global_score: int = Field(
        description="Calculated score: Max(0, 100 - Total_Penalties). Minor=1pt, Major=5pt, Critical=10pt")
    summary: LqaSummary
    detected_errors: List[ErrorDetail]


# ==========================================
# 2. RUN EXTRACTION AND ALIGNMENT CORRIDOR
# ==========================================
def run_lqa_pipeline(target_locale_key: str = "en-US", enable_tmx_matching: bool = True, tmx_file: str = "memory.xml"):
    print(f"--- 🚀 Initializing Universal LQA Ingestion Pipeline [{target_locale_key}] ---")

    # 1. Fetch the target configuration profile
    if target_locale_key not in LOCALE_PROFILES:
        raise ValueError(f"Locale profile for '{target_locale_key}' is missing from configurations.")

    active_profile = LOCALE_PROFILES[target_locale_key]

    # 2. Run scraping routines (assuming your output maps to target file layouts)
    process_localization_templates()

    # Make sure your scraper maps correctly to the dynamic target file names
    source_json = "extracted_data/index_it-IT.json"
    target_json = f"extracted_data/index_{target_locale_key}.json"

    aligned_data = align_localization_payloads(source_json, target_json)
    serialized_payload = json.dumps(aligned_data, indent=2, ensure_ascii=False)

    # 3. Compile the Pydantic schema mapping
    pure_json_schema = json.dumps(LqaReportSchema.model_json_schema(), indent=2)

    # 4. Generate the hybrid generic system prompt
    system_prompt = compile_generic_prompt(pure_json_schema, active_profile)
    user_content = f"### Input Segments to Evaluate:\n```json\n{serialized_payload}\n```"

    # 5. Execute API payload passage
    client = OpenAI(
        base_url=os.environ.get("LLM_BASE_URL", "[https://api.openai.com/v1](https://api.openai.com/v1)"),
        api_key=os.environ.get("LLM_API_KEY")
    )
    model_name = os.environ.get("LLM_MODEL_NAME", "gpt-4o-mini")

    try:
        # 💡 THE SECRET SAUCE: Append '.with_raw_response' right before '.create'
        raw_http_response = client.chat.completions.with_raw_response.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            response_format={"type": "json_object"},
            temperature=0.1
        )

        # --------------------------------------------------
        # METRIC A: Extract Free API Rate Limits from Headers
        # --------------------------------------------------
        headers = raw_http_response.headers

        print("\n=== ⏳ API RATE LIMIT METRICS ===")
        # Defensive lookup (.get) because alternative free providers (Groq, OpenRouter, etc.)
        # name their custom rate limit header keys slightly differently.
        remaining_req = headers.get("x-ratelimit-remaining-requests") or headers.get("x-ratelimit-remaining") or "N/A"
        remaining_tok = headers.get("x-ratelimit-remaining-tokens") or "N/A"
        limit_reset = headers.get("x-ratelimit-reset-tokens") or headers.get("x-ratelimit-reset") or "N/A"

        print(f"Requests Remaining: {remaining_req}")
        print(f"Tokens Remaining:   {remaining_tok}")
        print(f"Window Reset In:    {limit_reset}")
        print("=================================\n")

        # --------------------------------------------------
        # METRIC B: Parse the Core Object & Extract Token Usage
        # --------------------------------------------------
        # Convert the raw response packet into the standard usable completion object
        completion = raw_http_response.parse()

        # Log exact usage details for this run
        if completion.usage:
            print("=== 📊 RUNTIME TOKEN USAGE ===")
            print(f"Prompt (Input) Tokens:     {completion.usage.prompt_tokens}")
            print(f"Completion (Output) Tokens: {completion.usage.completion_tokens}")
            print(f"Total Session Tokens:      {completion.usage.total_tokens}")
            print("==============================\n")

        # Extract the raw string payload safely
        raw_json_string = completion.choices[0].message.content

        # 💡 THE SECRET SAUCE: Validate the raw JSON locally using Pydantic!
        # If the LLM missed a key or broke a type, Pydantic will raise an error here immediately.
        validated_report = LqaReportSchema.model_validate_json(raw_json_string)

        # ==========================================
        # 5. TMX MATCHING AND ENRICHMENT (NEW!)
        # ==========================================
        if enable_tmx_matching and os.path.exists(tmx_file):
            print(f"\n--- 🔍 Running TMX Sync & Alignment ---")
            report_dict = validated_report.model_dump()
            enriched_report_dict = enrich_lqa_report_with_tmx(
                report_dict,
                tmx_file,
                source_locale="it-IT",
                target_locale=target_locale_key,
                threshold=0.4  # Adjust threshold as needed (0.4 = 40% similarity minimum)
            )
            # Re-validate with enriched data
            validated_report = LqaReportSchema.model_validate(enriched_report_dict)
        elif enable_tmx_matching:
            print(f"\n[TMX WARNING] TMX file not found at: {tmx_file}")

        # ==========================================
        # 6. SAVE RUNTIME ARTIFACTS
        # ==========================================
        output_dir = "outputs"
        os.makedirs(output_dir, exist_ok=True)
        report_path = os.path.join(output_dir, f"lqa_audit_report_it-IT_{target_locale_key}.json")

        with open(report_path, "w", encoding="utf-8") as f:
            # Safely dump back out as clean JSON for your frontend application
            json.dump(validated_report.model_dump(), f, indent=2, ensure_ascii=False)

        print(f"\n--- 🎉 Pipeline Complete! ---")
        print(f"[SUCCESS] Score Calculated: {validated_report.global_score}/100")
        print(f"[SUCCESS] Errors Found:     {validated_report.summary.total_errors}")
        print(f"[ARTIFACT] Unified report written to: {report_path}")

    except Exception as e:
        print(f"\n[CRITICAL ERROR] Pipeline execution interrupted: {e}")


if __name__ == "__main__":
    import sys

    # Fix encoding issues on Windows console
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

    # Get target locale from environment variable (for dashboard integration) or default
    target_locale = os.environ.get('TARGET_LOCALE', 'en-US')

    run_lqa_pipeline(target_locale, enable_tmx_matching=True, tmx_file="memory.xml")
