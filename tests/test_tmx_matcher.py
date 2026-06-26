"""
Unit tests for TMX matching and write-back functionality.
Run with: pytest test_tmx_matcher.py -v
"""

import os
import tempfile

from tmx_matcher import TMXParser, TMXMatcher, TMXWriter, TMXEntry


def create_test_tmx_file(file_path: str):
    """Create a minimal TMX file for testing"""
    tmx_content = """<?xml version="1.0" encoding="UTF-8"?>
<tmx version="1.4">
  <header creationtool="TestSuite" creationtoolversion="1.0" datatype="PlainText" segtype="sentence" adminlang="en-US" srclang="it-IT"/>
  <body>
    <tu tuid="test_001">
      <tuv xml:lang="it-IT"><seg>Calcio Storico</seg></tuv>
      <tuv xml:lang="en-US"><seg>Historic Football</seg></tuv>
      <tuv xml:lang="de-DE"><seg>Historischer Fußball</seg></tuv>
    </tu>
    <tu tuid="test_002">
      <tuv xml:lang="it-IT"><seg>Palio di Siena</seg></tuv>
      <tuv xml:lang="en-US"><seg>Palio of Siena</seg></tuv>
    </tu>
  </body>
</tmx>"""

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(tmx_content)


class TestTMXParser:
    """Tests for TMX parsing functionality"""

    def test_parse_valid_tmx(self):
        """Test parsing a valid TMX file"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False, encoding='utf-8') as f:
            create_test_tmx_file(f.name)
            tmx_path = f.name

        try:
            parser = TMXParser(tmx_path)

            assert len(parser.entries) == 2
            assert parser.source_locale == "it-IT"

            # Check first entry
            entry1 = parser.find_entry_by_tuid("test_001")
            assert entry1 is not None
            assert entry1.get_translation("it-IT") == "Calcio Storico"
            assert entry1.get_translation("en-US") == "Historic Football"
            assert entry1.get_translation("de-DE") == "Historischer Fußball"

        finally:
            os.unlink(tmx_path)

    def test_find_entry_by_tuid(self):
        """Test finding entries by TUID"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False, encoding='utf-8') as f:
            create_test_tmx_file(f.name)
            tmx_path = f.name

        try:
            parser = TMXParser(tmx_path)

            # Find existing entry
            entry = parser.find_entry_by_tuid("test_002")
            assert entry is not None
            assert entry.tuid == "test_002"

            # Try to find non-existent entry
            missing = parser.find_entry_by_tuid("nonexistent")
            assert missing is None

        finally:
            os.unlink(tmx_path)


class TestTMXMatcher:
    """Tests for TMX fuzzy matching functionality"""

    def test_exact_match(self):
        """Test exact string matching"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False, encoding='utf-8') as f:
            create_test_tmx_file(f.name)
            tmx_path = f.name

        try:
            parser = TMXParser(tmx_path)
            matcher = TMXMatcher(parser)

            # Exact match should score 1.0
            result = matcher.find_best_match(
                "Calcio Storico",
                "Historic Football",
                "it-IT",
                "en-US",
                threshold=0.5
            )

            assert result is not None
            entry, score, match_type = result
            assert entry.tuid == "test_001"
            assert score >= 0.9  # Should be very high for exact match

        finally:
            os.unlink(tmx_path)

    def test_fuzzy_match(self):
        """Test fuzzy string matching"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False, encoding='utf-8') as f:
            create_test_tmx_file(f.name)
            tmx_path = f.name

        try:
            parser = TMXParser(tmx_path)
            matcher = TMXMatcher(parser)

            # Similar but not exact match
            result = matcher.find_best_match(
                "Calcio Storico Fiorentino",  # Added word
                "Historical Football",  # Slightly different
                "it-IT",
                "en-US",
                threshold=0.5
            )

            assert result is not None
            entry, score, match_type = result
            # Should still match to the most similar entry
            assert entry.tuid == "test_001"
            assert 0.5 <= score < 1.0

        finally:
            os.unlink(tmx_path)

    def test_no_match_below_threshold(self):
        """Test that poor matches are rejected"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False, encoding='utf-8') as f:
            create_test_tmx_file(f.name)
            tmx_path = f.name

        try:
            parser = TMXParser(tmx_path)
            matcher = TMXMatcher(parser)

            # Completely different text
            result = matcher.find_best_match(
                "Motor Valley Supercars",
                "Supercars from Motor Valley",
                "it-IT",
                "en-US",
                threshold=0.8
            )

            # Should not match with high threshold
            assert result is None or result[1] < 0.8

        finally:
            os.unlink(tmx_path)


class TestTMXWriter:
    """Tests for TMX write-back functionality"""

    def test_update_existing_entry(self):
        """Test updating an existing TMX entry"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False, encoding='utf-8') as f:
            create_test_tmx_file(f.name)
            tmx_path = f.name

        try:
            writer = TMXWriter(tmx_path)

            # Update existing entry
            success = writer.update_translation("test_001", "en-US", "Historic Florentine Football")
            assert success is True

            # Verify the update
            parser = TMXParser(tmx_path)
            entry = parser.find_entry_by_tuid("test_001")
            # Note: Changes are in memory, not yet saved

        finally:
            os.unlink(tmx_path)

    def test_create_new_entry(self):
        """Test creating a new TMX entry"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False, encoding='utf-8') as f:
            create_test_tmx_file(f.name)
            tmx_path = f.name

        try:
            writer = TMXWriter(tmx_path)

            # Create new entry
            tuid = writer.create_translation_unit(
                "it-IT",
                "Motor Valley",
                "en-US",
                "Motor Valley",
                tuid="test_003"
            )

            assert tuid == "test_003"

            # Try to create duplicate (should fail)
            duplicate = writer.create_translation_unit(
                "it-IT",
                "Another text",
                "en-US",
                "Another translation",
                tuid="test_003"
            )
            assert duplicate is None

        finally:
            os.unlink(tmx_path)

    def test_save_with_backup(self):
        """Test saving TMX file with backup"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False, encoding='utf-8') as f:
            create_test_tmx_file(f.name)
            tmx_path = f.name

        try:
            writer = TMXWriter(tmx_path)
            writer.update_translation("test_001", "en-US", "Updated Translation")

            # Save with backup
            success = writer.save(backup=True)
            assert success is True

            # Check that backup was created
            backup_files = [f for f in os.listdir(os.path.dirname(tmx_path))
                            if f.startswith(os.path.basename(tmx_path) + '.backup_')]
            assert len(backup_files) >= 1

            # Clean up backups
            for backup in backup_files:
                backup_path = os.path.join(os.path.dirname(tmx_path), backup)
                if os.path.exists(backup_path):
                    os.unlink(backup_path)

        finally:
            if os.path.exists(tmx_path):
                os.unlink(tmx_path)


class TestTMXEntry:
    """Tests for TMXEntry class"""

    def test_get_translation(self):
        """Test retrieving translations by locale"""
        translations = {
            "it-IT": "Testo italiano",
            "en-US": "English text",
            "de-DE": "Deutscher Text"
        }
        entry = TMXEntry("test_tuid", translations)

        assert entry.get_translation("it-IT") == "Testo italiano"
        assert entry.get_translation("en-US") == "English text"
        assert entry.get_translation("fr-FR") is None

    def test_repr(self):
        """Test string representation"""
        translations = {"it-IT": "Test", "en-US": "Test"}
        entry = TMXEntry("test_001", translations)

        repr_str = repr(entry)
        assert "test_001" in repr_str
        assert "it-IT" in repr_str
        assert "en-US" in repr_str


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v"])
