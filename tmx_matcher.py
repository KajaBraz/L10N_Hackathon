"""
TMX (Translation Memory Exchange) Sync & Alignment Module

This module provides functionality to:
1. Parse TMX files (XML format for translation memories)
2. Match detected LQA issues against TMX entries using fuzzy matching
3. Expose TMX match IDs to enable translation memory synchronization
4. Write approved fixes back to TMX file (bidirectional sync)
"""

import json
import logging
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from difflib import SequenceMatcher
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


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


class TMXWriter:
    """
    Writer class for updating TMX files with approved translations.
    Enables bidirectional TMX synchronization.
    """

    def __init__(self, tmx_file_path: str):
        self.tmx_file_path = tmx_file_path
        self.tree = None
        self.root = None
        self._load()

    def _load(self):
        """Load the TMX file for editing"""
        try:
            self.tree = ET.parse(self.tmx_file_path)
            self.root = self.tree.getroot()
            logger.info(f"Loaded TMX file for writing: {self.tmx_file_path}")
        except Exception as e:
            logger.error(f"Failed to load TMX file for writing: {e}")
            raise

    def _find_tu_by_tuid(self, tuid: str) -> Optional[ET.Element]:
        """Find a translation unit element by TUID"""
        for tu in self.root.findall('.//tu'):
            if tu.get('tuid') == tuid:
                return tu
        return None

    def _find_or_create_tuv(self, tu: ET.Element, locale: str) -> ET.Element:
        """Find or create a translation unit variant for a specific locale"""
        # Try to find existing tuv for this locale
        for tuv in tu.findall('tuv'):
            if tuv.get('{http://www.w3.org/XML/1998/namespace}lang') == locale:
                return tuv

        # Create new tuv if not found
        tuv = ET.SubElement(tu, 'tuv')
        tuv.set('{http://www.w3.org/XML/1998/namespace}lang', locale)
        seg = ET.SubElement(tuv, 'seg')
        return tuv

    def _generate_tuid(self, source_text: str, prefix: str = "approved") -> str:
        """
        Generate a unique TUID for new translation units.
        Format: prefix_hash_timestamp
        """
        # Create a simple hash from the source text
        text_hash = abs(hash(source_text)) % (10 ** 8)
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        return f"{prefix}_{text_hash}_{timestamp}"

    def update_translation(
            self,
            tuid: str,
            locale: str,
            translation: str
    ) -> bool:
        """
        Update an existing TMX entry with a new translation.

        Args:
            tuid: Translation unit ID to update
            locale: Target locale code
            translation: New translation text

        Returns:
            True if update successful, False otherwise
        """
        try:
            tu = self._find_tu_by_tuid(tuid)
            if not tu:
                logger.warning(f"TUID '{tuid}' not found in TMX file")
                return False

            # Find or create the tuv for this locale
            tuv = self._find_or_create_tuv(tu, locale)
            seg = tuv.find('seg')

            if seg is None:
                seg = ET.SubElement(tuv, 'seg')

            seg.text = translation
            logger.info(f"Updated TMX entry {tuid} for locale {locale}")
            return True

        except Exception as e:
            logger.error(f"Failed to update TMX entry {tuid}: {e}")
            return False

    def create_translation_unit(
            self,
            source_locale: str,
            source_text: str,
            target_locale: str,
            target_text: str,
            tuid: Optional[str] = None
    ) -> Optional[str]:
        """
        Create a new translation unit in the TMX file.

        Args:
            source_locale: Source locale code (e.g., 'it-IT')
            source_text: Source language text
            target_locale: Target locale code (e.g., 'en-US')
            target_text: Target language translation
            tuid: Optional custom TUID (auto-generated if not provided)

        Returns:
            The TUID of the created entry, or None if failed
        """
        try:
            # Generate TUID if not provided
            if not tuid:
                tuid = self._generate_tuid(source_text)

            # Check if TUID already exists
            if self._find_tu_by_tuid(tuid):
                logger.warning(f"TUID '{tuid}' already exists, use update_translation instead")
                return None

            # Find the body element
            body = self.root.find('.//body')
            if body is None:
                logger.error("TMX file has no body element")
                return None

            # Create new translation unit
            tu = ET.SubElement(body, 'tu')
            tu.set('tuid', tuid)

            # Add source locale variant
            tuv_source = ET.SubElement(tu, 'tuv')
            tuv_source.set('{http://www.w3.org/XML/1998/namespace}lang', source_locale)
            seg_source = ET.SubElement(tuv_source, 'seg')
            seg_source.text = source_text

            # Add target locale variant
            tuv_target = ET.SubElement(tu, 'tuv')
            tuv_target.set('{http://www.w3.org/XML/1998/namespace}lang', target_locale)
            seg_target = ET.SubElement(tuv_target, 'seg')
            seg_target.text = target_text

            logger.info(f"Created new TMX entry {tuid} ({source_locale} → {target_locale})")
            return tuid

        except Exception as e:
            logger.error(f"Failed to create TMX entry: {e}")
            return None

    def save(self, backup: bool = True) -> bool:
        """
        Save the modified TMX file to disk.

        Args:
            backup: If True, creates a backup of the original file

        Returns:
            True if save successful, False otherwise
        """
        try:
            if backup:
                backup_path = f"{self.tmx_file_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                import shutil
                shutil.copy2(self.tmx_file_path, backup_path)
                logger.info(f"Created TMX backup: {backup_path}")

            # Write the modified tree
            self.tree.write(
                self.tmx_file_path,
                encoding='utf-8',
                xml_declaration=True
            )
            logger.info(f"Saved TMX file: {self.tmx_file_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to save TMX file: {e}")
            return False


def write_approved_fixes_to_tmx(
        approved_fixes: List[Dict],
        tmx_file_path: str,
        source_locale: str = "it-IT",
        create_new_entries: bool = True,
        similarity_threshold: float = 0.8
) -> Dict[str, int]:
    """
    Write approved translation fixes back to the TMX file.

    This function enables bidirectional TMX synchronization by:
    1. Matching approved fixes to existing TMX entries
    2. Updating existing entries with corrected translations
    3. Optionally creating new TMX entries for unmatched fixes

    Args:
        approved_fixes: List of approved fix dictionaries (from approved_fixes_{locale}.json)
        tmx_file_path: Path to TMX file
        source_locale: Source locale code
        create_new_entries: If True, create new TMX entries for unmatched fixes
        similarity_threshold: Minimum similarity to consider a TMX entry a match

    Returns:
        Statistics dictionary: {
            'total_processed': int,
            'entries_updated': int,
            'entries_created': int,
            'errors': int
        }
    """
    stats = {
        'total_processed': 0,
        'entries_updated': 0,
        'entries_created': 0,
        'errors': 0
    }

    try:
        # Load TMX for matching
        parser = TMXParser(tmx_file_path)
        matcher = TMXMatcher(parser)

        # Load TMX for writing
        writer = TMXWriter(tmx_file_path)

        logger.info(f"Processing {len(approved_fixes)} approved fixes for TMX write-back")

        for fix in approved_fixes:
            stats['total_processed'] += 1

            locale = fix.get('locale')
            source_text = fix.get('source_text', '')
            approved_translation = fix.get('approved_translation', '')
            target_text_original = fix.get('target_text_snippet', '')

            if not locale or not source_text or not approved_translation:
                logger.warning(f"Skipping incomplete fix: {fix.get('error_id')}")
                stats['errors'] += 1
                continue

            # Try to find matching TMX entry
            match_result = matcher.find_best_match(
                source_text,
                target_text_original,
                source_locale,
                locale,
                similarity_threshold
            )

            if match_result:
                # Update existing TMX entry
                tmx_entry, similarity, match_type = match_result
                tuid = tmx_entry.tuid

                logger.info(f"Matched fix to existing TMX entry: {tuid} (similarity: {similarity:.2f})")

                if writer.update_translation(tuid, locale, approved_translation):
                    stats['entries_updated'] += 1
                else:
                    stats['errors'] += 1

            elif create_new_entries:
                # Create new TMX entry
                tuid = writer.create_translation_unit(
                    source_locale,
                    source_text,
                    locale,
                    approved_translation
                )

                if tuid:
                    stats['entries_created'] += 1
                    logger.info(f"Created new TMX entry: {tuid}")
                else:
                    stats['errors'] += 1

            else:
                logger.info(f"No TMX match found for fix (source: '{source_text[:50]}...'), skipping")

        # Save the modified TMX file
        if writer.save(backup=True):
            logger.info(f"TMX write-back complete: {stats}")
        else:
            logger.error("Failed to save TMX file")
            stats['errors'] += 1

        return stats

    except Exception as e:
        logger.error(f"TMX write-back failed: {e}")
        stats['errors'] += 1
        return stats


if __name__ == "__main__":
    # Configure logging for demo
    logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')

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

    logger.info(f"Enriched report saved to: {output_path}")

    # Demo TMX write-back
    import os

    approved_fixes_path = "outputs/approved_fixes_en-US.json"
    if os.path.exists(approved_fixes_path):
        with open(approved_fixes_path, 'r', encoding='utf-8') as f:
            approved_fixes = json.load(f)

        logger.info("\n=== Testing TMX Write-Back ===")
        stats = write_approved_fixes_to_tmx(
            approved_fixes,
            tmx_path,
            create_new_entries=True,
            similarity_threshold=0.7
        )
        logger.info(f"Write-back statistics: {stats}")
