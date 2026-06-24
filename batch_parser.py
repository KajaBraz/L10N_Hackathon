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


def parse_html_content(html_content):
    """
    Cleans the HTML structure and extracts visible text strings and image metadata.
    """
    soup = BeautifulSoup(html_content, 'html.parser')

    # Strip out scripts, styles, and metadata that users don't see
    for noise_tag in soup(["script", "style", "meta", "link", "noscript"]):
        noise_tag.decompose()

    extracted_items = []

    # Extract user-facing text strings
    for text_node in soup.find_all(string=True):
        cleaned_text = text_node.strip()
        if cleaned_text:
            parent_element = text_node.parent
            dom_path = get_dom_path(parent_element)

            extracted_items.append({
                "type": "text",
                "content": cleaned_text,
                "tag": parent_element.name,
                "dom_path": dom_path
            })

    # Extract image metadata (src and alt tags)
    for img_tag in soup.find_all('img'):
        src = img_tag.get('src', '').strip()
        alt = img_tag.get('alt', '').strip()

        if src or alt:
            dom_path = get_dom_path(img_tag)
            extracted_items.append({
                "type": "image",
                "src": src,
                "alt": alt,
                "tag": "img",
                "dom_path": dom_path
            })

    return extracted_items


def process_localization_templates(input_dir='templates', output_dir='extracted_data'):
    """
    Scans the input folder for multi-locale HTML files, parses them,
    and writes results to matching JSON targets inside the output folder.
    """
    # Defensive checks for hackathon directory state
    if not os.path.exists(input_dir):
        print(f"[ERROR] Target input directory '{input_dir}' does not exist.")
        print(f"Please create a '{input_dir}' directory and place your index_xx.html files there.")
        return

    # Automatically generate output folder if missing
    os.makedirs(output_dir, exist_ok=True)

    # Pattern matching for target locale files (e.g., templates/index_it.html)
    search_pattern = os.path.join(input_dir, "index_*.html")
    html_files = glob.glob(search_pattern)

    if not html_files:
        print(f"[WARNING] No files matching 'index_*.html' discovered in '{input_dir}'.")
        return

    print(f"--- Launching Batch Processing Framework ({len(html_files)} files found) ---\n")

    for file_path in html_files:
        filename = os.path.basename(file_path)  # e.g., "index_it.html"
        file_root, _ = os.path.splitext(filename)  # e.g., "index_it"
        output_filename = f"{file_root}.json"  # e.g., "index_it.json"
        output_path = os.path.join(output_dir, output_filename)

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                html_content = f.read()

            # Execute parsing pipeline
            parsed_data = parse_html_content(html_content)

            # Store the localized payload safely
            with open(output_path, 'w', encoding='utf-8') as out_f:
                json.dump(parsed_data, out_f, indent=2, ensure_ascii=False)

            print(
                f"[SUCCESS] Processed: {filename:20} -> Generated: {os.path.join(output_dir, output_filename)} ({len(parsed_data)} items)")

        except Exception as e:
            print(f"[FAILED] Error processing {filename}: {e}")

    print(f"\n--- Batch Pipeline Execution Complete ---")


if __name__ == "__main__":
    # Execute with default directories
    process_localization_templates()