import os
import json
import glob
from bs4 import BeautifulSoup


def get_dom_path(element):
    """
    Recursively builds a unique CSS selector path for an element
    so the downstream TMX alignment engine knows exactly where it lives.
    """
    path = []
    current = element
    while current and current.name != '[document]':
        siblings = current.find_previous_siblings(current.name)
        index = len(siblings) + 1
        path.append(f"{current.name}:nth-of-type({index})")
        current = current.parent
    return " > ".join(reversed(path))


def get_structural_context(element):
    """
    Scans upwards from the current element to capture its direct parent metadata
    and the closest macro-container ID (e.g., id="palio") for deep LLM context.
    """
    metadata = {
        "attributes": {
            "id": element.get('id'),
            "class": " ".join(element.get('class', [])) if element.get('class') else None
        },
        "parent_node": None,
        "closest_anchor_id": None
    }

    # 1. Capture immediate parent details
    parent = element.parent
    if parent and parent.name != '[document]':
        metadata["parent_node"] = {
            "tag": parent.name,
            "id": parent.get('id'),
            "class": " ".join(parent.get('class', [])) if parent.get('class') else None
        }

    # 2. Bubble up to find the nearest structural ID context (e.g., <article id="palio">)
    ancestor = parent
    while ancestor and ancestor.name != '[document]':
        if ancestor.get('id'):
            metadata["closest_anchor_id"] = {
                "tag": ancestor.name,
                "id": ancestor.get('id')
            }
            break
        ancestor = ancestor.parent

    return metadata


def parse_html_content(html_content):
    """
    Cleans the HTML structure and extracts text strings and image metadata
    enriched with parental classes, IDs, and ancestral context blocks.
    """
    soup = BeautifulSoup(html_content, 'html.parser')

    # Clean out hidden layout noise
    for noise_tag in soup(["script", "style", "meta", "link", "noscript"]):
        noise_tag.decompose()

    extracted_items = []

    # Extract visible text strings
    for text_node in soup.find_all(string=True):
        from bs4 import Comment, Doctype
        if isinstance(text_node, (Comment, Doctype)):
            continue

        cleaned_text = text_node.strip()
        if cleaned_text:
            parent_element = text_node.parent

            # Skip strings attached directly to the root html/document elements
            if parent_element.name in ['html', '[document]']:
                continue

            dom_path = get_dom_path(parent_element)
            context = get_structural_context(parent_element)

            extracted_items.append({
                "type": "text",
                "content": cleaned_text,
                "tag": parent_element.name,
                "dom_path": dom_path,
                "attributes": context["attributes"],
                "parent_node": context["parent_node"],
                "closest_anchor_id": context["closest_anchor_id"]
            })

    # Extract image elements
    for img_tag in soup.find_all('img'):
        src = img_tag.get('src', '').strip()
        alt = img_tag.get('alt', '').strip()

        if src or alt:
            dom_path = get_dom_path(img_tag)
            context = get_structural_context(img_tag)

            extracted_items.append({
                "type": "image",
                "src": src,
                "alt": alt,
                "tag": "img",
                "dom_path": dom_path,
                "attributes": context["attributes"],
                "parent_node": context["parent_node"],
                "closest_anchor_id": context["closest_anchor_id"]
            })

    return extracted_items


def process_localization_templates(input_dir='templates', output_dir='extracted_data'):
    """
    Batch processes all localized template files using the metadata-enriched pipeline.
    """
    if not os.path.exists(input_dir):
        print(f"[ERROR] Target input directory '{input_dir}' does not exist.")
        return

    os.makedirs(output_dir, exist_ok=True)
    search_pattern = os.path.join(input_dir, "index_*.html")
    html_files = glob.glob(search_pattern)

    if not html_files:
        print(f"[WARNING] No files matching 'index_*.html' discovered in '{input_dir}'.")
        return

    print(f"--- Running Context-Aware Processing ({len(html_files)} files found) ---\n")

    for file_path in html_files:
        filename = os.path.basename(file_path)
        file_root, _ = os.path.splitext(filename)
        output_filename = f"{file_root}.json"
        output_path = os.path.join(output_dir, output_filename)

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                html_content = f.read()

            parsed_data = parse_html_content(html_content)

            with open(output_path, 'w', encoding='utf-8') as out_f:
                json.dump(parsed_data, out_f, indent=2, ensure_ascii=False)

            print(f"[SUCCESS] Parsed: {filename:20} -> Generated: {output_filename}")

        except Exception as e:
            print(f"[FAILED] Error processing {filename}: {e}")

    print(f"\n--- Batch Pipeline Execution Complete ---")

