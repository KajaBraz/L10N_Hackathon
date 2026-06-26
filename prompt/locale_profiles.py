# Configuration database for different target locales
LOCALE_PROFILES = {
    "de-DE": {
        "target_locale_name": "German (de-DE)",
        "date_convention": "Dates must match German layout formats strictly (DD.MM.YYYY).",
        "currency_convention": "Numbers must use periods for thousands and commas for decimals. The currency symbol should follow the space-separated amount (e.g., '1.200,00 €').",
        "cultural_expectations": "Ensure tone matches corporate styling conventions (e.g., consistent use of formal 'Sie' vs informal 'Du' addresses depending on domain preferences)."
    },
    "en-GB": {
        "target_locale_name": "British English (en-GB)",
        "date_convention": "Dates must match British layout formats strictly (DD/MM/YYYY).",
        "currency_convention": "Numbers must use commas for thousands and periods for decimals. Use British English spelling variants (e.g., 'colour', 'centre').",
        "cultural_expectations": "Adapt naming preferences to match UK standards where applicable (e.g., 'football match' instead of 'soccer match')."
    },
    "en-US": {
        "target_locale_name": "US English (en-US)",
        "date_convention": "Dates must match US layout formats strictly (MM/DD/YYYY).",
        "currency_convention": "Numbers must use commas for thousands and periods for decimals. The currency symbol must precede the amount (e.g., '$1,200.00' or '€1,200.00').",
        "cultural_expectations": "Idioms, local idioms, and slang must be transcreated naturally for an American audience. Avoid literal translations of regional phrases."
    },
    "ja-JP": {
        "target_locale_name": "Japanese (ja-JP)",
        "date_convention": "Dates must match Japanese layout formats strictly (YYYY/MM/DD).",
        "currency_convention": "Numbers must use commas for thousands and periods for decimals. The currency symbol typically precedes the amount without a space (e.g., '¥1,200' or '€1,200.00').",
        "cultural_expectations": "Ensure a natural, polite tone (Teineigo) suitable for a Japanese audience. Western idioms, sports terms, and cultural concepts must be transcreated smoothly rather than translated literally."
    },
    "pl-PL": {
        "target_locale_name": "Polish (pl-PL)",
        "date_convention": "Dates must match Polish layout formats strictly (DD.MM.YYYY).",
        "currency_convention": "Numbers must use spaces for thousands and commas for decimals. The currency symbol typically follows the amount, separated by a space (e.g., '1 200,00 zł' or '1 200,00 €').",
        "cultural_expectations": "Ensure a natural, engaging, and grammatically correct tone appropriate for a Polish audience. Idioms, regional concepts (like football or traditional holidays), and culinary terms must be transcreated accurately rather than translated literally to avoid absurd or robotic imagery."
    },
    "pt-BR": {
        "target_locale_name": "Brazilian Portuguese (pt-BR)",
        "date_convention": "Dates must match Brazilian layout formats strictly (DD/MM/YYYY).",
        "currency_convention": "Numbers must use periods for thousands and commas for decimals. The currency symbol should precede the amount, typically separated by a space (e.g., 'R$ 1.200,00' or '€ 1.200,00').",
        "cultural_expectations": "Ensure the tone is warm, natural, and localized for a Brazilian audience. Idiomatic expressions, culinary references, and sports terminology should be adapted contextually rather than translated literally to prevent clunky phrasing or absurd machine-like mistranslations."
    }
}
