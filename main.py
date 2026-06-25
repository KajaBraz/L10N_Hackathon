import json
import os
from typing import List, Literal
from openai import OpenAI
from pydantic import BaseModel, Field

# Import your custom modules
from align_elements import align_localization_payloads
from batch_parser import process_localization_templates


# ==========================================
# 1. DEFINE STRUCTURED OUTPUT SCHEMAS
# ==========================================
class ErrorDetail(BaseModel):
    error_id: str = Field(description="Unique error sequence string, e.g., ERR_001")
    html_element_id: str = Field(description="The structural HTML ID anchor from the input, e.g., 'calcio'")
    dom_path: str = Field(description="The exact query selector string copied from the input item")
    mqm_category: str = Field(
        description="Locale Convention, Terminology, Cultural Transcreation, Accuracy, or Fluency")
    severity: Literal["Minor", "Major", "Critical"]
    source_text_snippet: str = Field(description="The original Italian string context")
    target_text_snippet: str = Field(description="The flawed translated English string found")
    issue_explanation: str = Field(description="Why this fails for a US user.")
    suggested_fix: str = Field(description="Corrected text ready for live deployment.")


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
def run_lqa_pipeline():
    print("--- 🚀 Initializing Universal LQA Ingestion Pipeline ---")

    # Run your BeautifulSoup scraper
    process_localization_templates()

    # Combine individual files into the pre-aligned payload array
    aligned_data = align_localization_payloads("extracted_data/index_it.json", "extracted_data/index_en.json")
    print(f"[INFO] Successfully aligned {len(aligned_data)} visual DOM fragments.")

    # Convert aligned python list to formatted string block
    serialized_payload = json.dumps(aligned_data, indent=2, ensure_ascii=False)

    # Export Pydantic schema as a pure JSON string to force compliance inside the prompt text
    pure_json_schema = json.dumps(LqaReportSchema.model_json_schema(), indent=2)

    # ==========================================
    # 3. COMPILE UNIVERSAL SYSTEM PROMPT
    # ==========================================
    system_prompt = (
        "You are an enterprise-grade Localization Quality Assurance (LQA) Engine.\n"
        "Your task is to evaluate an array of pre-aligned source and target UI segments, "
        "identify localization flaws, calculate an MQM score, and report findings.\n\n"

        "CRITICAL REQUIREMENT:\n"
        "You must respond with a single, well-formed JSON object. "
        f"The architecture of your JSON output MUST strictly match this JSON Schema:\n{pure_json_schema}\n\n"

        "INSPECTION CRITERIA:\n"
        "1. Global Banners: Look for segments where html_element_id is 'global_banner' and css_class contains 'promo-banner'. "
        "Ensure dates match US conventions (MM/DD/YYYY).\n"
        "2. Price Conventions: Look for segments where css_class contains 'meta-price'. Check that numbers use US layout punctuation "
        "(commas for thousands, periods for decimals).\n"
        "3. Visual/Alt Text: Evaluate elements where element_tag is 'img'. Ensure the target_text (alt text) represents natural, "
        "localized phrasing instead of literal translations.\n"
        "4. Context Accuracy: Catch critical drops (e.g. 'Calcio' -> 'Calcium')."
    )

    user_content = f"### Input Segments to Evaluate:\n```json\n{serialized_payload}\n```"

    # ==========================================
    # 4. EXECUTE COUPLING WITH ALTERNATIVE API
    # ==========================================
    print("\n--- 🤖 Initiating Third-Party LLM Analysis Sequence ---")

    client = OpenAI(
        base_url=os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1"),
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
        # 5. SAVE RUNTIME ARTIFACTS
        # ==========================================
        output_dir = "extracted_data"
        report_path = os.path.join(output_dir, "lqa_audit_report.json")

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
    run_lqa_pipeline()
