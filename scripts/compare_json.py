#!/usr/bin/env python3
"""
compare_json.py - Compare two karechat interface JSON files (dev vs prod)
Usage: python3 compare_json.py <dev_json_path> <prod_json_path>
"""

import json
import sys
from pathlib import Path


def load_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def deep_equal(a, b) -> bool:
    return json.dumps(a, sort_keys=True, ensure_ascii=False) == json.dumps(b, sort_keys=True, ensure_ascii=False)


def compare_section(dev_section: dict, prod_section: dict, section_name: str) -> dict:
    """Compare request or response section, returning diff per API key."""
    all_keys = sorted(set(list(dev_section.keys()) + list(prod_section.keys())))
    diffs = {}

    for key in all_keys:
        if key not in dev_section:
            diffs[key] = {"status": "only_in_prod", "dev": None, "prod": prod_section[key]}
        elif key not in prod_section:
            diffs[key] = {"status": "only_in_dev", "dev": dev_section[key], "prod": None}
        elif not deep_equal(dev_section[key], prod_section[key]):
            diffs[key] = {"status": "different", "dev": dev_section[key], "prod": prod_section[key]}
        # else: identical, skip

    return diffs


def print_diff_summary(request_diffs: dict, response_diffs: dict):
    """Print human-readable diff summary."""
    all_api_keys = sorted(set(list(request_diffs.keys()) + list(response_diffs.keys())))

    if not all_api_keys:
        print("✅ 두 파일이 완전히 동일합니다.")
        return

    print("=" * 60)
    print("📊 DEV vs PROD 차이 요약")
    print("=" * 60)

    only_in_dev = []
    only_in_prod = []
    different = []

    for key in all_api_keys:
        req_diff = request_diffs.get(key)
        res_diff = response_diffs.get(key)

        statuses = set()
        if req_diff:
            statuses.add(req_diff["status"])
        if res_diff:
            statuses.add(res_diff["status"])

        if "only_in_dev" in statuses:
            only_in_dev.append(key)
        elif "only_in_prod" in statuses:
            only_in_prod.append(key)
        else:
            different.append(key)

    if only_in_dev:
        print(f"\n🟦 DEV에만 존재 ({len(only_in_dev)}개): {', '.join(only_in_dev)}")
    if only_in_prod:
        print(f"\n🟧 PROD에만 존재 ({len(only_in_prod)}개): {', '.join(only_in_prod)}")
    if different:
        print(f"\n🔄 내용이 다름 ({len(different)}개): {', '.join(different)}")

    print("\n" + "=" * 60)
    print("📋 상세 차이 내용")
    print("=" * 60)

    for key in all_api_keys:
        req_diff = request_diffs.get(key)
        res_diff = response_diffs.get(key)

        print(f"\n[{key}]")

        if req_diff:
            status = req_diff["status"]
            if status == "only_in_dev":
                print(f"  request: 🟦 DEV에만 존재")
            elif status == "only_in_prod":
                print(f"  request: 🟧 PROD에만 존재")
            else:
                print(f"  request: 🔄 변경됨")
                dev_str = json.dumps(req_diff["dev"], indent=4, ensure_ascii=False)
                prod_str = json.dumps(req_diff["prod"], indent=4, ensure_ascii=False)
                print(f"    [DEV]\n{_indent(dev_str, 6)}")
                print(f"    [PROD]\n{_indent(prod_str, 6)}")

        if res_diff:
            status = res_diff["status"]
            if status == "only_in_dev":
                print(f"  response: 🟦 DEV에만 존재")
            elif status == "only_in_prod":
                print(f"  response: 🟧 PROD에만 존재")
            else:
                print(f"  response: 🔄 변경됨")
                dev_str = json.dumps(res_diff["dev"], indent=4, ensure_ascii=False)
                prod_str = json.dumps(res_diff["prod"], indent=4, ensure_ascii=False)
                print(f"    [DEV]\n{_indent(dev_str, 6)}")
                print(f"    [PROD]\n{_indent(prod_str, 6)}")


def _indent(text: str, spaces: int) -> str:
    prefix = " " * spaces
    return "\n".join(prefix + line for line in text.splitlines())


def main():
    if len(sys.argv) != 3:
        print("Usage: python3 compare_json.py <dev_json_path> <prod_json_path>")
        sys.exit(1)

    dev_path, prod_path = sys.argv[1], sys.argv[2]

    dev_json = load_json(dev_path)
    prod_json = load_json(prod_path)

    dev_request = dev_json.get("request", {})
    prod_request = prod_json.get("request", {})
    dev_response = dev_json.get("response", {})
    prod_response = prod_json.get("response", {})

    # Exclude non-API keys from request section (urlPath, contentType, etc.)
    api_keys_in_request = {k for k in set(list(dev_request.keys()) + list(prod_request.keys()))
                           if k.startswith("H_") or k.startswith("T_")}
    dev_request_apis = {k: v for k, v in dev_request.items() if k in api_keys_in_request}
    prod_request_apis = {k: v for k, v in prod_request.items() if k in api_keys_in_request}

    request_diffs = compare_section(dev_request_apis, prod_request_apis, "request")
    response_diffs = compare_section(dev_response, prod_response, "response")

    print_diff_summary(request_diffs, response_diffs)

    # Output machine-readable diff as JSON for merge_json.py
    diff_output = {
        "request_diffs": {k: {"status": v["status"]} for k, v in request_diffs.items()},
        "response_diffs": {k: {"status": v["status"]} for k, v in response_diffs.items()},
        "all_diff_keys": sorted(set(list(request_diffs.keys()) + list(response_diffs.keys())))
    }
    diff_file = Path(dev_path).parent / ".diff_result.json"
    with open(diff_file, "w", encoding="utf-8") as f:
        json.dump(diff_output, f, ensure_ascii=False, indent=2)
    print(f"\n💾 diff 결과가 {diff_file} 에 저장되었습니다.")


if __name__ == "__main__":
    main()
