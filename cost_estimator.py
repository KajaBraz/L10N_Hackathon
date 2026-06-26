"""
Token estimation and cost calculation for LQA evaluations.
"""
import json
import os
from typing import Dict, List

# Token estimation (rough approximation: 1 token ≈ 4 characters for English/Latin scripts)
# For multilingual content, we use conservative estimates
TOKEN_RATIO = 4.0  # characters per token

# Model pricing (per 1M tokens) - approximate as of 2024/2025
MODEL_PRICING = {
    # OpenAI Models
    "gpt-4o": {"input": 2.50, "output": 10.00, "provider": "OpenAI"},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60, "provider": "OpenAI"},
    "gpt-3.5-turbo": {"input": 0.50, "output": 1.50, "provider": "OpenAI"},

    # Mistral Models
    "mistral-large": {"input": 2.00, "output": 6.00, "provider": "Mistral"},
    "mistral-medium": {"input": 1.00, "output": 3.00, "provider": "Mistral"},
    "mistral-small": {"input": 0.30, "output": 0.90, "provider": "Mistral"},

    # Meta Llama Models (via various providers)
    "llama-3.1-70b": {"input": 0.60, "output": 0.80, "provider": "Meta"},
    "llama-3.1-8b": {"input": 0.10, "output": 0.15, "provider": "Meta"},

    # Microsoft Phi Models
    "phi-3-medium": {"input": 0.50, "output": 1.50, "provider": "Microsoft"},
    "phi-3-mini": {"input": 0.10, "output": 0.30, "provider": "Microsoft"},

    # DeepSeek Models
    "deepseek-coder": {"input": 0.14, "output": 0.28, "provider": "DeepSeek"},
    "deepseek-chat": {"input": 0.14, "output": 0.28, "provider": "DeepSeek"},
}


def estimate_tokens(text: str) -> int:
    """
    Estimate token count for given text.
    Uses character-based approximation.
    """
    if not text:
        return 0
    return max(1, int(len(text) / TOKEN_RATIO))


def count_tokens_in_json_file(file_path: str) -> int:
    """
    Count tokens in a JSON file by serializing it.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        serialized = json.dumps(data, ensure_ascii=False)
        return estimate_tokens(serialized)
    except Exception as e:
        print(f"[COST ESTIMATOR] Error reading {file_path}: {e}")
        return 0


def estimate_system_prompt_tokens() -> int:
    """
    Estimate tokens for system prompt.
    This is a rough estimate based on the prompt structure.
    """
    # System prompt includes: locale profile + schema + instructions
    # Typically 2000-3000 tokens for our LQA prompts
    return 2500


def estimate_output_tokens() -> int:
    """
    Estimate output tokens for LQA report.
    Based on average report size with detected errors.
    """
    # Typical output: global_score, summary, 5-15 errors with details
    # Each error ~200 tokens, plus structure ~500 tokens
    return 2000  # Conservative estimate


def calculate_cost_per_locale(
        extracted_source_file: str,
        extracted_target_file: str,
        model: str
) -> Dict:
    """
    Calculate estimated cost for evaluating one locale.

    Returns:
        {
            "input_tokens": int,
            "output_tokens": int,
            "input_cost": float,
            "output_cost": float,
            "total_cost": float,
            "model": str,
            "provider": str
        }
    """
    # Get model pricing
    if model not in MODEL_PRICING:
        # Default to gpt-4o-mini if model not found
        model = "gpt-4o-mini"

    pricing = MODEL_PRICING[model]

    # Count input tokens
    system_tokens = estimate_system_prompt_tokens()
    source_tokens = count_tokens_in_json_file(extracted_source_file) if os.path.exists(extracted_source_file) else 0
    target_tokens = count_tokens_in_json_file(extracted_target_file) if os.path.exists(extracted_target_file) else 0

    input_tokens = system_tokens + source_tokens + target_tokens
    output_tokens = estimate_output_tokens()

    # Calculate costs (pricing is per 1M tokens)
    input_cost = (input_tokens / 1_000_000) * pricing["input"]
    output_cost = (output_tokens / 1_000_000) * pricing["output"]
    total_cost = input_cost + output_cost

    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "input_cost": round(input_cost, 4),
        "output_cost": round(output_cost, 4),
        "total_cost": round(total_cost, 4),
        "model": model,
        "provider": pricing["provider"]
    }


def estimate_evaluation_cost(
        locales: List[str],
        model: str,
        extracted_data_dir: str = "extracted_data"
) -> Dict:
    """
    Estimate total cost for evaluating multiple locales.

    Returns:
        {
            "locales": [...],
            "model": str,
            "provider": str,
            "per_locale_breakdown": [{locale, cost, tokens}],
            "total_input_tokens": int,
            "total_output_tokens": int,
            "total_cost": float,
            "scrapin_phase_required": bool
        }
    """
    source_file = os.path.join(extracted_data_dir, "index_it-IT.json")
    per_locale_breakdown = []

    total_input = 0
    total_output = 0
    total_cost = 0.0

    for locale in locales:
        target_file = os.path.join(extracted_data_dir, f"index_{locale}.json")
        cost_data = calculate_cost_per_locale(source_file, target_file, model)

        per_locale_breakdown.append({
            "locale": locale,
            "cost": cost_data["total_cost"],
            "input_tokens": cost_data["input_tokens"],
            "output_tokens": cost_data["output_tokens"]
        })

        total_input += cost_data["input_tokens"]
        total_output += cost_data["output_tokens"]
        total_cost += cost_data["total_cost"]

    # Check if scraping is needed (if extracted files don't exist)
    scraping_needed = not os.path.exists(source_file)

    return {
        "locales": locales,
        "model": model,
        "provider": MODEL_PRICING.get(model, MODEL_PRICING["gpt-4o-mini"])["provider"],
        "per_locale_breakdown": per_locale_breakdown,
        "total_input_tokens": total_input,
        "total_output_tokens": total_output,
        "total_tokens": total_input + total_output,
        "total_cost": round(total_cost, 4),
        "scraping_phase_required": scraping_needed
    }


def get_available_models() -> List[Dict[str, str]]:
    """
    Get list of available models with their providers.
    """
    return [
        {"id": model, "name": model, "provider": info["provider"]}
        for model, info in MODEL_PRICING.items()
    ]


if __name__ == "__main__":
    # Test the estimator
    test_locales = ["en-US", "ja-JP", "pl-PL"]
    test_model = "gpt-4o-mini"

    estimate = estimate_evaluation_cost(test_locales, test_model)

    print("\n=== COST ESTIMATION TEST ===")
    print(f"Model: {estimate['model']} ({estimate['provider']})")
    print(f"Locales: {', '.join(estimate['locales'])}")
    print(f"\nPer-Locale Breakdown:")
    for breakdown in estimate['per_locale_breakdown']:
        print(
            f"  {breakdown['locale']}: ${breakdown['cost']:.4f} ({breakdown['input_tokens']:,} input + {breakdown['output_tokens']:,} output tokens)")
    print(f"\nTotal Tokens: {estimate['total_tokens']:,}")
    print(f"Total Cost: ${estimate['total_cost']:.4f}")
    print(f"Scraping Required: {estimate['scraping_phase_required']}")
