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
import re
import sys
from pathlib import Path
from datetime import datetime


def load_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def find_block_end(text: str, start: int) -> int:
    """{ 위치에서 시작해 짝이 맞는 } 위치를 반환한다."""
    depth = 0
    in_string = False
    escape = False
    for i in range(start, len(text)):
        ch = text[i]
        if escape:
            escape = False
            continue
        if ch == "\\" and in_string:
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return i
    return -1


def extract_key_block(text: str, section: str, key: str):
    """
    text에서 "section" 섹션 안의 "key" 블록의 (start, end) 인덱스를 반환한다.
    start: 키 따옴표 시작, end: 값 } 포함 위치.
    없으면 None 반환.
    """
    # "section" : { 또는 "section": { 위치 찾기
    section_match = re.search(rf'"({re.escape(section)})"(\s*:\s*)\{{', text)
    if not section_match:
        return None
    section_brace_start = section_match.end() - 1  # { 위치

    # section 블록 끝 찾기
    section_end = find_block_end(text, section_brace_start)
    if section_end == -1:
        return None

    section_body = text[section_brace_start:section_end + 1]
    body_offset = section_brace_start

    # section body 안에서 "key" 찾기
    key_match = re.search(rf'"({re.escape(key)})"(\s*:\s*)\{{', section_body)
    if not key_match:
        return None

    key_start = body_offset + key_match.start()
    value_brace_start = body_offset + key_match.end() - 1
    value_end = find_block_end(text, value_brace_start)
    if value_end == -1:
        return None

    return key_start, value_end


def get_key_sep(text: str) -> str:
    """파일에서 사용하는 key-value 구분자(" : " vs ": ")를 감지한다."""
    m = re.search(r'"[^"]+"\s*:\s*', text)
    if m:
        raw = m.group()
        colon_idx = raw.index(":")
        before = raw[colon_idx - 1] if colon_idx > 0 else ""
        after = raw[colon_idx + 1] if colon_idx + 1 < len(raw) else ""
        if before == " " and after == " ":
            return " : "
    return ": "


def get_indent(text: str) -> str:
    """파일의 들여쓰기 문자열을 감지한다."""
    for line in text.splitlines():
        if line.startswith("\t"):
            return "\t"
        stripped = line.lstrip(" ")
        if stripped and stripped != line:
            spaces = len(line) - len(stripped)
            return " " * spaces
    return "    "


def serialize_value(value: dict, indent_str: str, key_sep: str, base_depth: int) -> str:
    """
    dict 값을 target 파일과 동일한 포맷(들여쓰기, 콜론 구분자)으로 직렬화한다.
    base_depth: 현재 중첩 깊이 (들여쓰기 계산용).
    """
    def _serialize(obj, depth):
        if isinstance(obj, dict):
            if not obj:
                return "{}"
            lines = ["{"]
            items = list(obj.items())
            for i, (k, v) in enumerate(items):
                comma = "," if i < len(items) - 1 else ""
                val_str = _serialize(v, depth + 1)
                lines.append(f"{indent_str * (depth + 1)}{json.dumps(k, ensure_ascii=False)}{key_sep}{val_str}{comma}")
            lines.append(f"{indent_str * depth}}}")
            return "\n".join(lines)
        elif isinstance(obj, list):
            if not obj:
                return "[]"
            lines = ["["]
            for i, item in enumerate(obj):
                comma = "," if i < len(obj) - 1 else ""
                lines.append(f"{indent_str * (depth + 1)}{_serialize(item, depth + 1)}{comma}")
            lines.append(f"{indent_str * depth}]")
            return "\n".join(lines)
        else:
            return json.dumps(obj, ensure_ascii=False)

    return _serialize(value, base_depth)


def get_key_depth(text: str, section: str, key: str) -> int:
    """target 파일에서 key가 위치한 들여쓰기 깊이를 반환한다."""
    block = extract_key_block(text, section, key)
    if block is None:
        return 2  # 기본값: request/response 내부는 depth 2
    key_start = block[0]
    line_start = text.rfind("\n", 0, key_start) + 1
    line = text[line_start:key_start]
    indent_str = get_indent(text)
    if not indent_str:
        return 2
    stripped = line.lstrip()
    if not stripped and line:
        return len(line) // max(len(indent_str), 1)
    return len(line.expandtabs(4)) // max(len(indent_str.expandtabs(4)), 1)


def replace_key_block(text: str, section: str, key: str, new_value: dict, indent_str: str, key_sep: str) -> str:
    """
    target raw text에서 section.key 블록을 new_value로 교체한다.
    key가 없으면 section 마지막에 삽입한다.
    """
    depth = get_key_depth(text, section, key) if extract_key_block(text, section, key) else 2
    new_val_str = serialize_value(new_value, indent_str, key_sep, depth)
    new_entry = f'"{key}"{key_sep}{new_val_str}'

    block = extract_key_block(text, section, key)
    if block:
        # 기존 블록 교체: "key" : { ... } 범위 교체
        start, end = block
        # key 앞의 따옴표까지 포함해서 교체
        return text[:start] + new_entry + text[end + 1:]
    else:
        # 없으면 section 끝 } 바로 앞에 삽입
        section_match = re.search(rf'"({re.escape(section)})"(\s*:\s*)\{{', text)
        if not section_match:
            return text
        section_brace_start = section_match.end() - 1
        section_end = find_block_end(text, section_brace_start)
        if section_end == -1:
            return text

        # 삽입 위치: section_end 바로 앞 (닫는 } 전)
        insert_pos = section_end
        # 앞에 , 붙이기
        prefix = f",\n{indent_str * depth}"
        return text[:insert_pos] + prefix + new_entry + "\n" + text[insert_pos:]


def remove_key_block(text: str, section: str, key: str) -> str:
    """target raw text에서 section.key 블록을 제거한다."""
    block = extract_key_block(text, section, key)
    if not block:
        return text
    start, end = block

    # 앞쪽 쉼표+공백/개행 또는 뒤쪽 쉼표+공백/개행도 함께 제거
    before = text[:start]
    after = text[end + 1:]

    # 앞에 쉼표가 있으면 제거
    before_stripped = before.rstrip()
    if before_stripped.endswith(","):
        before = before_stripped[:-1]
    elif after.lstrip().startswith(","):
        after = after.lstrip()[1:]

    # 앞 개행/공백 정리
    before = before.rstrip(" \t")  # 줄 앞 공백만 제거 (개행은 유지)

    return before + after


def merge_text(target_text: str, source: dict, target: dict, api_keys: list):
    """
    target raw text를 기반으로, 선택한 api_keys만 source 값으로 교체/삽입/삭제한다.
    """
    indent_str = get_indent(target_text)
    key_sep = get_key_sep(target_text)
    result = target_text
    applied = []

    source_request = source.get("request", {})
    source_response = source.get("response", {})
    target_request = target.get("request", {})
    target_response = target.get("response", {})

    for key in api_keys:
        changed_sections = []

        # request 처리
        if key in source_request:
            result = replace_key_block(result, "request", key, source_request[key], indent_str, key_sep)
            changed_sections.append("request")
        elif key in target_request:
            result = remove_key_block(result, "request", key)
            changed_sections.append("request(삭제)")

        # response 처리
        if key in source_response:
            result = replace_key_block(result, "response", key, source_response[key], indent_str, key_sep)
            changed_sections.append("response")
        elif key in target_response:
            result = remove_key_block(result, "response", key)
            changed_sections.append("response(삭제)")

        if changed_sections:
            applied.append({"key": key, "sections": changed_sections})

    return result, applied


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

    with open(target_path, "r", encoding="utf-8") as f:
        target_text = f.read()

    if api_keys_arg.upper() == "ALL":
        diff_file = Path(source_path).parent / ".diff_result.json"
        if diff_file.exists():
            diff_data = load_json(str(diff_file))
            api_keys = diff_data.get("all_diff_keys", [])
        else:
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

    merged_text, applied = merge_text(target_text, source_json, target_json, api_keys)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(merged_text)

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
    with open(str(log_file), "w", encoding="utf-8") as f:
        json.dump(change_log, f, ensure_ascii=False, indent=2)
    print(f"\n📝 변경 로그: {log_file}")


if __name__ == "__main__":
    main()
