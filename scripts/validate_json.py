#!/usr/bin/env python3
"""
validate_json.py - Validate karechat interface JSON structure
Usage: python3 validate_json.py <json_path>

Checks:
  - Valid JSON syntax
  - Top-level structure (request / response)
  - request API entries: methodType, subPath, parameter
  - response API entries: success, error, data
  - parameter fields: dataType, split, alias
  - methodType is one of GET / POST / PUT / DELETE
"""

import json
import sys

VALID_METHOD_TYPES = {"GET", "POST", "PUT", "DELETE"}


def load_json(path: str) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ JSON 문법 오류: {e}")
        sys.exit(1)


def is_api_key(key: str) -> bool:
    return key.startswith(("H_", "T_"))


def validate_parameter_fields(api_key: str, parameter: dict, errors: list):
    for field_name, field_def in parameter.items():
        if not isinstance(field_def, dict):
            errors.append(f"  [{api_key}] request.parameter.{field_name}: dict 형식이어야 함")
            continue
        for required in ("dataType", "split"):
            if required not in field_def:
                errors.append(f"  [{api_key}] request.parameter.{field_name}: '{required}' 필드 누락")


def validate_request(request: dict, errors: list, warnings: list):
    for key, value in request.items():
        if not is_api_key(key):
            continue
        if not isinstance(value, dict):
            errors.append(f"  [{key}] request 항목이 dict 형식이어야 함")
            continue

        # methodType
        method = value.get("methodType")
        if not method:
            errors.append(f"  [{key}] request.methodType 누락")
        elif method not in VALID_METHOD_TYPES:
            errors.append(f"  [{key}] request.methodType='{method}' 유효하지 않음 (허용: {', '.join(sorted(VALID_METHOD_TYPES))})")

        # subPath
        if not value.get("subPath"):
            errors.append(f"  [{key}] request.subPath 누락")

        # parameter
        parameter = value.get("parameter")
        if parameter is None:
            warnings.append(f"  [{key}] request.parameter 없음")
        elif not isinstance(parameter, dict):
            errors.append(f"  [{key}] request.parameter가 dict 형식이어야 함")
        else:
            validate_parameter_fields(key, parameter, errors)


def validate_response(response: dict, errors: list, warnings: list):
    for key, value in response.items():
        if not is_api_key(key):
            continue
        if not isinstance(value, dict):
            errors.append(f"  [{key}] response 항목이 dict 형식이어야 함")
            continue

        # success
        if "success" not in value:
            warnings.append(f"  [{key}] response.success 없음")

        # error
        if "error" not in value:
            warnings.append(f"  [{key}] response.error 없음")

        # data
        if "data" not in value:
            warnings.append(f"  [{key}] response.data 없음")


def validate(data: dict) -> tuple[list, list]:
    errors = []
    warnings = []

    # Top-level keys
    if "request" not in data:
        errors.append("  최상위 'request' 키 누락")
    if "response" not in data:
        errors.append("  최상위 'response' 키 누락")

    if errors:
        return errors, warnings

    request = data.get("request", {})
    response = data.get("response", {})

    # Check request common fields
    if "urlPath" not in request:
        warnings.append("  request.urlPath 없음")

    # Check API key consistency
    req_api_keys = {k for k in request if is_api_key(k)}
    res_api_keys = {k for k in response if is_api_key(k)}

    only_in_request = req_api_keys - res_api_keys
    only_in_response = res_api_keys - req_api_keys

    if only_in_request:
        warnings.append(f"  request에만 존재하는 API (response 없음): {', '.join(sorted(only_in_request))}")
    if only_in_response:
        warnings.append(f"  response에만 존재하는 API (request 없음): {', '.join(sorted(only_in_response))}")

    validate_request(request, errors, warnings)
    validate_response(response, errors, warnings)

    return errors, warnings


def main():
    if len(sys.argv) != 2:
        print("Usage: python3 validate_json.py <json_path>")
        sys.exit(1)

    path = sys.argv[1]
    data = load_json(path)
    errors, warnings = validate(data)

    req_count = sum(1 for k in data.get("request", {}) if is_api_key(k))
    res_count = sum(1 for k in data.get("response", {}) if is_api_key(k))

    print(f"\n📄 파일: {path}")
    print(f"   request API: {req_count}개 / response API: {res_count}개")

    if not errors and not warnings:
        print("✅ 구조 검증 통과 — 이상 없음\n")
        sys.exit(0)

    if warnings:
        print(f"\n⚠️  경고 ({len(warnings)}건):")
        for w in warnings:
            print(w)

    if errors:
        print(f"\n❌ 오류 ({len(errors)}건):")
        for e in errors:
            print(e)
        print()
        sys.exit(1)
    else:
        print("\n✅ 오류 없음 (경고만 있음)\n")
        sys.exit(0)


if __name__ == "__main__":
    main()
