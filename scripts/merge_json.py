#!/usr/bin/env python3
"""
merge_json.py - Merge selected API entries from source JSON into target JSON
Usage: python3 merge_json.py <source_json> <target_json> <direction> <api_keys> <output_path>

Arguments:
  source_json   : path to source JSON (e.g., dev.json)
  target_json   : path to target JSON (e.g., prod.json)
  direction     : "dev_to_prod" or "prod_to_dev"
  api_keys      : comma-separated API keys to apply (e.g., "H_01,H_02" or "1,2,58,63")
                  numbers without prefix are auto-converted (58 → H_58)
                  use "ALL" to apply all differing keys
  output_path   : path for the output merged JSON file
"""

import json
import sys
from pathlib import Path
from datetime import datetime


def load_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(data: dict, path: str):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def merge(source: dict, target: dict, api_keys: list) -> tuple[dict, list]:
    """
    Merge selected API keys from source into target.
    Returns (merged_json, list_of_applied_changes).
    """
    import copy
    merged = copy.deepcopy(target)
    applied = []

    source_request = source.get("request", {})
    source_response = source.get("response", {})

    for key in api_keys:
        changed_sections = []

        # Merge request
        if key in source_request:
            if "request" not in merged:
                merged["request"] = {}
            merged["request"][key] = copy.deepcopy(source_request[key])
            changed_sections.append("request")
        elif key in merged.get("request", {}):
            # Key exists in target but not in source → remove it
            del merged["request"][key]
            changed_sections.append("request(삭제)")

        # Merge response
        if key in source_response:
            if "response" not in merged:
                merged["response"] = {}
            merged["response"][key] = copy.deepcopy(source_response[key])
            changed_sections.append("response")
        elif key in merged.get("response", {}):
            del merged["response"][key]
            changed_sections.append("response(삭제)")

        if changed_sections:
            applied.append({"key": key, "sections": changed_sections})

    return merged, applied


def main():
    if len(sys.argv) != 6:
        print("Usage: python3 merge_json.py <source_json> <target_json> <direction> <api_keys> <output_path>")
        print("  direction: dev_to_prod | prod_to_dev")
        print("  api_keys:  H_01,H_02 or ALL")
        sys.exit(1)

    source_path = sys.argv[1]
    target_path = sys.argv[2]
    direction = sys.argv[3]
    api_keys_arg = sys.argv[4]
    output_path = sys.argv[5]

    source_json = load_json(source_path)
    target_json = load_json(target_path)

    if api_keys_arg.upper() == "ALL":
        # Load diff result if available
        diff_file = Path(source_path).parent / ".diff_result.json"
        if diff_file.exists():
            diff_data = load_json(str(diff_file))
            api_keys = diff_data.get("all_diff_keys", [])
        else:
            # Compute all API keys from both
            all_keys = set()
            for section in ["request", "response"]:
                all_keys.update(k for k in source_json.get(section, {}) if k.startswith(("H_", "T_")))
                all_keys.update(k for k in target_json.get(section, {}) if k.startswith(("H_", "T_")))
            api_keys = sorted(all_keys)
    else:
        raw_keys = [k.strip() for k in api_keys_arg.split(",") if k.strip()]
        api_keys = []
        for k in raw_keys:
            if k.isdigit():
                api_keys.append(f"H_{k}")
            else:
                api_keys.append(k.upper())

    merged, applied = merge(source_json, target_json, api_keys)
    save_json(merged, output_path)

    direction_label = "DEV → PROD" if direction == "dev_to_prod" else "PROD → DEV"
    print(f"\n✅ 병합 완료 ({direction_label})")
    print(f"📁 출력 파일: {output_path}")
    print(f"\n📋 적용된 변경 사항 ({len(applied)}개 API):")
    for item in applied:
        sections_str = ", ".join(item["sections"])
        print(f"  - {item['key']}: {sections_str}")

    # Save change log
    change_log = {
        "timestamp": datetime.now().isoformat(),
        "direction": direction_label,
        "applied_keys": [item["key"] for item in applied],
        "details": applied,
        "output_path": output_path
    }
    log_file = Path(output_path).parent / ".merge_log.json"
    save_json(change_log, str(log_file))
    print(f"\n📝 변경 로그: {log_file}")


if __name__ == "__main__":
    main()
