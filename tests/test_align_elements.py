"""
Unit tests for element alignment functionality.
Run with: pytest test_align_elements.py -v
"""

import json
import tempfile

from align_elements import align_localization_payloads


def create_test_json_file(file_path: str, content: list):
    """Helper to create test JSON files"""
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(content, f, ensure_ascii=False)


class TestAlignElements:
    """Tests for localization payload alignment"""

    def test_exact_dom_path_match(self):
        """Test alignment with exact DOM path matches"""
        source_data = [
            {
                "type": "text",
                "content": "Benvenuto",
                "tag": "h1",
                "dom_path": "html > body > h1",
                "closest_anchor_id": {"id": "header"}
            }
        ]

        target_data = [
            {
                "type": "text",
                "content": "Welcome",
                "tag": "h1",
                "dom_path": "html > body > h1",
                "closest_anchor_id": {"id": "header"}
            }
        ]

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
            create_test_json_file(f.name, source_data)
            source_path = f.name

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
            create_test_json_file(f.name, target_data)
            target_path = f.name

        try:
            result = align_localization_payloads(source_path, target_path)

            assert len(result) == 1
            assert result[0]["source_text"] == "Benvenuto"
            assert result[0]["target_text"] == "Welcome"
            assert result[0]["dom_path"] == "html > body > h1"

        finally:
            import os
            os.unlink(source_path)
            os.unlink(target_path)

    def test_fuzzy_anchor_match(self):
        """Test alignment with fuzzy matching within same anchor"""
        source_data = [
            {
                "type": "text",
                "content": "Calcio Storico Fiorentino",
                "tag": "h2",
                "dom_path": "html > body > article:nth-of-type(1) > h2",
                "closest_anchor_id": {"id": "calcio"}
            }
        ]

        target_data = [
            {
                "type": "text",
                "content": "Historic Football",
                "tag": "h2",
                "dom_path": "html > body > article:nth-of-type(1) > h2",
                "closest_anchor_id": {"id": "calcio"}
            }
        ]

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
            create_test_json_file(f.name, source_data)
            source_path = f.name

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
            create_test_json_file(f.name, target_data)
            target_path = f.name

        try:
            result = align_localization_payloads(source_path, target_path)

            assert len(result) == 1
            assert result[0]["html_element_id"] == "calcio"
            assert result[0]["source_text"] == "Calcio Storico Fiorentino"
            assert result[0]["target_text"] == "Historic Football"

        finally:
            import os
            os.unlink(source_path)
            os.unlink(target_path)

    def test_multiple_elements_alignment(self):
        """Test aligning multiple elements"""
        source_data = [
            {
                "type": "text",
                "content": "Titolo",
                "tag": "h1",
                "dom_path": "html > body > h1",
                "closest_anchor_id": {"id": "header"}
            },
            {
                "type": "text",
                "content": "Descrizione",
                "tag": "p",
                "dom_path": "html > body > p",
                "closest_anchor_id": {"id": "header"}
            }
        ]

        target_data = [
            {
                "type": "text",
                "content": "Title",
                "tag": "h1",
                "dom_path": "html > body > h1",
                "closest_anchor_id": {"id": "header"}
            },
            {
                "type": "text",
                "content": "Description",
                "tag": "p",
                "dom_path": "html > body > p",
                "closest_anchor_id": {"id": "header"}
            }
        ]

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
            create_test_json_file(f.name, source_data)
            source_path = f.name

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
            create_test_json_file(f.name, target_data)
            target_path = f.name

        try:
            result = align_localization_payloads(source_path, target_path)

            assert len(result) == 2
            assert result[0]["source_text"] == "Titolo"
            assert result[0]["target_text"] == "Title"
            assert result[1]["source_text"] == "Descrizione"
            assert result[1]["target_text"] == "Description"

        finally:
            import os
            os.unlink(source_path)
            os.unlink(target_path)

    def test_image_alignment(self):
        """Test alignment of image alt text"""
        source_data = [
            {
                "type": "image",
                "alt": "Immagine del Palio",
                "tag": "img",
                "dom_path": "html > body > img",
                "closest_anchor_id": {"id": "palio"}
            }
        ]

        target_data = [
            {
                "type": "image",
                "alt": "Image of the Palio",
                "tag": "img",
                "dom_path": "html > body > img",
                "closest_anchor_id": {"id": "palio"}
            }
        ]

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
            create_test_json_file(f.name, source_data)
            source_path = f.name

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
            create_test_json_file(f.name, target_data)
            target_path = f.name

        try:
            result = align_localization_payloads(source_path, target_path)

            assert len(result) == 1
            assert result[0]["source_text"] == "Immagine del Palio"
            assert result[0]["target_text"] == "Image of the Palio"
            assert result[0]["element_tag"] == "img"

        finally:
            import os
            os.unlink(source_path)
            os.unlink(target_path)


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v"])
