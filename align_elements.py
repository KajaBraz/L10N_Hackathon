import json


def align_localization_payloads(source_json_path, target_json_path):
    with open(source_json_path, 'r', encoding='utf-8') as f:
        source_data = json.load(f)
    with open(target_json_path, 'r', encoding='utf-8') as f:
        target_data = json.load(f)

    # Map the English target elements by their DOM path for O(1) lookup
    target_map = {item['dom_path']: item for item in target_data}
    aligned_payload = []

    for src_item in source_data:
        dom_path = src_item['dom_path']
        if dom_path in target_map:
            tgt_item = target_map[dom_path]

            aligned_payload.append({
                "dom_path": dom_path,
                "element_tag": src_item['tag'],
                "html_element_id": src_item['closest_anchor_id']['id'] if src_item[
                    'closest_anchor_id'] else "global_banner",
                "css_class": src_item['attributes']['class'],
                # Handle text content vs image alt-text gracefully
                "source_text": src_item['content'] if src_item['type'] == 'text' else src_item['alt'],
                "target_text": tgt_item['content'] if tgt_item['type'] == 'text' else tgt_item['alt']
            })

    return aligned_payload