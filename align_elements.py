import json
from difflib import SequenceMatcher


def align_localization_payloads(source_json_path, target_json_path):
    with open(source_json_path, 'r', encoding='utf-8') as f:
        source_data = json.load(f)
    with open(target_json_path, 'r', encoding='utf-8') as f:
        target_data = json.load(f)

    # 1. Map target elements into lists to completely prevent DOM Path Collision data loss
    target_path_map = {}
    for item in target_data:
        target_path_map.setdefault(item['dom_path'], []).append(item)

    # 2. Cluster target elements by anchor IDs to handle layout/structural drift gracefully
    target_anchor_clusters = {}
    for item in target_data:
        anchor = item['closest_anchor_id']['id'] if item.get('closest_anchor_id') else "global_banner"
        target_anchor_clusters.setdefault(anchor, []).append(item)

    # Track already aligned target elements to prevent duplicate assignments
    consumed_target_ptrs = set()
    aligned_payload = []

    for src_item in source_data:
        dom_path = src_item['dom_path']
        src_type = src_item['type']
        src_text = src_item['content'] if src_type == 'text' else src_item.get('alt', '')

        tgt_item = None

        # --- Tier 1: Exact DOM Path Match (Consuming Sequentially for Sibling Text Nodes) ---
        if dom_path in target_path_map:
            for cand in target_path_map[dom_path]:
                cand_ptr = id(cand)
                if cand_ptr not in consumed_target_ptrs and cand['type'] == src_type:
                    tgt_item = cand
                    break

        # --- Tier 2: Anchor Container Proximity Matching (Fuzzy Text Similarity Fallback) ---
        if not tgt_item:
            src_anchor = src_item['closest_anchor_id']['id'] if src_item.get('closest_anchor_id') else "global_banner"
            candidates = target_anchor_clusters.get(src_anchor, [])

            best_match = None
            best_score = -1.0

            for cand in candidates:
                cand_ptr = id(cand)
                if cand_ptr in consumed_target_ptrs or cand['type'] != src_type:
                    continue

                cand_text = cand['content'] if src_type == 'text' else cand.get('alt', '')

                # Check lexical overlap (highly effective for matching shared structural tokens/numbers/img tags)
                score = SequenceMatcher(None, src_text, cand_text).ratio()
                if score > best_score:
                    best_score = score
                    best_match = cand

            # Allow a match if it shares a meaningful semantic affinity under the same container block
            if best_match and (best_score >= 0.3 or src_type == 'image'):
                tgt_item = best_match

        # --- Tier 3: Positional Order Fallback within the Anchor Container ---
        if not tgt_item:
            src_anchor = src_item['closest_anchor_id']['id'] if src_item.get('closest_anchor_id') else "global_banner"
            candidates = target_anchor_clusters.get(src_anchor, [])
            for cand in candidates:
                cand_ptr = id(cand)
                if cand_ptr not in consumed_target_ptrs and cand['type'] == src_type and cand['tag'] == src_item['tag']:
                    tgt_item = cand
                    break

        # If a valid pair is established across source and target, commit it to the alignment array
        if tgt_item:
            consumed_target_ptrs.add(id(tgt_item))

            aligned_payload.append({
                "dom_path": dom_path,
                "element_tag": src_item['tag'],
                "html_element_id": src_item['closest_anchor_id']['id'] if src_item.get(
                    'closest_anchor_id') else "global_banner",
                "css_class": src_item['attributes'].get('class') if src_item.get('attributes') else None,
                "source_text": src_text,
                "target_text": tgt_item['content'] if tgt_item['type'] == 'text' else tgt_item.get('alt', '')
            })

    return aligned_payload