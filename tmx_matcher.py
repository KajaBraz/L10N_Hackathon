"""
TMX (Translation Memory Exchange) Sync & Alignment Module

This module provides functionality to:
1. Parse TMX files (XML format for translation memories)
2. Match detected LQA issues against TMX entries using fuzzy matching
3. Expose TMX match IDs to enable translation memory synchronization
"""

import json
import re
import xml.etree.ElementTree as ET
from difflib import SequenceMatcher
from typing import Dict, List, Optional, Tuple


class TMXEntry:
    """Represents a single translation unit from TMX file"""

    def __init__(self, tuid: str, translations: Dict[str, str]):
        self.tuid = tuid
        self.translations = translations

    def get_translation(self, locale: str) -> Optional[str]:
        """Get translation for a specific locale"""
        return self.translations.get(locale)

    def __repr__(self):
        return f"TMXEntry(tuid={self.tuid}, locales={list(self.translations.keys())})"


class TMXParser:
    """Parser for TMX (Translation Memory Exchange) files"""

    def __init__(self, tmx_file_path: str):
        self.tmx_file_path = tmx_file_path
        self.entries: List[TMXEntry] = []
        self.source_locale: str = ""
        self._parse()

    def _parse(self):
        """Parse the TMX file and extract translation units"""
        try:
            tree = ET.parse(self.tmx_file_path)
            root = tree.getroot()

            # Extract source locale from header
            header = root.find('.//header')
            if header is not None:
                self.source_locale = header.get('srclang', 'it-IT')

            # Parse each translation unit (tu)
            for tu in root.findall('.//tu'):
                tuid = tu.get('tuid', '')
                translations = {}

                # Extract translations for all locales
                for tuv in tu.findall('tuv'):
                    locale = tuv.get('{http://www.w3.org/XML/1998/namespace}lang')
                    seg = tuv.find('seg')
                    if locale and seg is not None and seg.text:
                        translations[locale] = seg.text.strip()

                if tuid and translations:
                    self.entries.append(TMXEntry(tuid, translations))

            print(f"[TMX PARSER] Loaded {len(self.entries)} translation units from {self.tmx_file_path}")

        except Exception as e:
            print(f"[TMX PARSER ERROR] Failed to parse TMX file: {e}")
            raise

    def get_all_entries(self) -> List[TMXEntry]:
        """Return all TMX entries"""
        return self.entries

    def find_entry_by_tuid(self, tuid: str) -> Optional[TMXEntry]:
        """Find a specific entry by its translation unit ID"""
        for entry in self.entries:
            if entry.tuid == tuid:
                return entry
        return None


class TMXMatcher:
    """
    Fuzzy matcher that finds closest TMX entries for given text strings
    using Levenshtein distance and semantic similarity
    """

    def __init__(self, tmx_parser: TMXParser):
        self.parser = tmx_parser
        self.entries = tmx_parser.get_all_entries()
        self.source_locale = tmx_parser.source_locale

    def _normalize_text(self, text: str) -> str:
        """Normalize text for better matching"""
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text.strip())
        # Convert to lowercase for case-insensitive matching
        return text.lower()

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate similarity score between two texts using SequenceMatcher
        Returns a value between 0.0 (no match) and 1.0 (perfect match)
        """
        norm_text1 = self._normalize_text(text1)
        norm_text2 = self._normalize_text(text2)

        return SequenceMatcher(None, norm_text1, norm_text2).ratio()

    def _calculate_levenshtein_distance(self, s1: str, s2: str) -> int:
        """
        Calculate Levenshtein distance (edit distance) between two strings
        Lower distance = more similar
        """
        if len(s1) < len(s2):
            return self._calculate_levenshtein_distance(s2, s1)

        if len(s2) == 0:
            return len(s1)

        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                # Cost of insertions, deletions, or substitutions
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row

        return previous_row[-1]

    def find_best_match(
            self,
            source_text: str,
            target_text: str,
            source_locale: str = "it-IT",
            target_locale: str = "en-US",
            threshold: float = 0.5
    ) -> Optional[Tuple[TMXEntry, float, str]]:
        """
        Find the best matching TMX entry for given source and target texts

        Args:
            source_text: The source language text (e.g., Italian)
            target_text: The target language text (e.g., English)
            source_locale: Source locale code
            target_locale: Target locale code
            threshold: Minimum similarity score to consider a match (0.0-1.0)

        Returns:
            Tuple of (TMXEntry, similarity_score, match_type) or None if no good match found
            match_type can be: "source", "target", or "both"
        """
        best_match = None
        best_score = 0.0
        match_type = ""

        for entry in self.entries:
            source_tmx = entry.get_translation(source_locale)
            target_tmx = entry.get_translation(target_locale)

            if not source_tmx or not target_tmx:
                continue

            # Calculate similarity for source text
            source_similarity = self._calculate_similarity(source_text, source_tmx)

            # Calculate similarity for target text
            target_similarity = self._calculate_similarity(target_text, target_tmx)

            # Use the maximum similarity as the overall score
            # Prioritize source matching as it's more reliable
            overall_score = max(source_similarity * 1.2, target_similarity)

            # Cap at 1.0
            overall_score = min(overall_score, 1.0)

            if overall_score > best_score and overall_score >= threshold:
                best_score = overall_score
                best_match = entry

                # Determine match type
                if source_similarity >= 0.8:
                    match_type = "source" if target_similarity < 0.8 else "both"
                elif target_similarity >= 0.8:
                    match_type = "target"
                else:
                    match_type = "fuzzy"

        if best_match:
            return (best_match, best_score, match_type)

        return None

    def find_matches_for_errors(
            self,
            detected_errors: List[Dict],
            source_locale: str = "it-IT",
            target_locale: str = "en-US",
            threshold: float = 0.5
    ) -> List[Dict]:
        """
        Enhance detected LQA errors with TMX match information

        Args:
            detected_errors: List of error dictionaries from LQA report
            source_locale: Source locale code
            target_locale: Target locale code
            threshold: Minimum similarity threshold

        Returns:
            Enhanced list of errors with TMX match data added
        """
        enhanced_errors = []

        for error in detected_errors:
            enhanced_error = error.copy()

            source_text = error.get('source_text_snippet', '')
            target_text = error.get('target_text_snippet', '')

            # Find best TMX match
            match_result = self.find_best_match(
                source_text,
                target_text,
                source_locale,
                target_locale,
                threshold
            )

            if match_result:
                tmx_entry, similarity, match_type = match_result

                # Add TMX match information to the error
                enhanced_error['tmx_match'] = {
                    'tuid': tmx_entry.tuid,
                    'similarity_score': round(similarity, 3),
                    'match_type': match_type,
                    'tmx_source_text': tmx_entry.get_translation(source_locale),
                    'tmx_target_text': tmx_entry.get_translation(target_locale),
                    'available_locales': list(tmx_entry.translations.keys())
                }

                print(f"[TMX MATCH] {error.get('error_id')}: matched to '{tmx_entry.tuid}' "
                      f"(score: {similarity:.2f}, type: {match_type})")
            else:
                enhanced_error['tmx_match'] = None
                print(f"[TMX MATCH] {error.get('error_id')}: no match found (threshold: {threshold})")

            enhanced_errors.append(enhanced_error)

        return enhanced_errors


def enrich_lqa_report_with_tmx(
        lqa_report: Dict,
        tmx_file_path: str,
        source_locale: str = "it-IT",
        target_locale: str = "en-US",
        threshold: float = 0.5
) -> Dict:
    """
    Utility function to enrich an entire LQA report with TMX match data

    Args:
        lqa_report: Complete LQA report dictionary
        tmx_file_path: Path to TMX file
        source_locale: Source locale code
        target_locale: Target locale code
        threshold: Similarity threshold for matching

    Returns:
        Enhanced LQA report with TMX data
    """
    try:
        # Parse TMX file
        parser = TMXParser(tmx_file_path)
        matcher = TMXMatcher(parser)

        # Enhance detected errors
        if 'detected_errors' in lqa_report:
            lqa_report['detected_errors'] = matcher.find_matches_for_errors(
                lqa_report['detected_errors'],
                source_locale,
                target_locale,
                threshold
            )

        # Add TMX metadata to report
        lqa_report['tmx_metadata'] = {
            'tmx_file': tmx_file_path,
            'total_tmx_entries': len(parser.entries),
            'source_locale': source_locale,
            'target_locale': target_locale,
            'matching_threshold': threshold
        }

        # Calculate match statistics
        matched_count = sum(1 for e in lqa_report.get('detected_errors', []) if e.get('tmx_match'))
        total_errors = len(lqa_report.get('detected_errors', []))

        lqa_report['tmx_metadata']['errors_matched'] = matched_count
        lqa_report['tmx_metadata']['errors_total'] = total_errors
        lqa_report['tmx_metadata']['match_rate'] = round(matched_count / total_errors, 3) if total_errors > 0 else 0.0

        print(f"\n[TMX ENRICHMENT] Matched {matched_count}/{total_errors} errors "
              f"({lqa_report['tmx_metadata']['match_rate'] * 100:.1f}%)")

        return lqa_report

    except Exception as e:
        print(f"[TMX ENRICHMENT ERROR] Failed to enrich report: {e}")
        return lqa_report


if __name__ == "__main__":
    # Demo/test code

    tmx_path = "memory.xml"
    report_path = "outputs/lqa_audit_report_it-IT_en-US.json"

    # Load LQA report
    with open(report_path, 'r', encoding='utf-8') as f:
        report = json.load(f)

    # Enrich with TMX data
    enriched_report = enrich_lqa_report_with_tmx(report, tmx_path, threshold=0.4)

    # Save enriched report
    output_path = report_path.replace('.json', '_tmx_enriched.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(enriched_report, f, indent=2, ensure_ascii=False)

    print(f"\n[SUCCESS] Enriched report saved to: {output_path}")
