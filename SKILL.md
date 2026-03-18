---
name: karechat-json-diff
description: >
  karechat HTTP API 인터페이스 JSON 파일의 개발(dev)과 운영(prod) 환경 간 차이를 비교하고,
  선택한 API(H_01, H_02 등)를 원하는 방향(dev→prod 또는 prod→dev)으로 병합하여
  새 JSON 파일을 생성하고 Notion 데이터베이스에 기록하는 스킬.
  트리거 키워드: 'convert json 변환', '인터페이스 설계서 json 변환', '컨퍼트 json 변환'
---

# karechat JSON Diff & Merge

## 워크플로우

아래 단계를 순서대로 진행한다.

### Step 1 — 파일 경로 입력 받기

사용자에게 다음을 요청한다:
- **dev JSON 파일 경로**
- **prod JSON 파일 경로**

경로가 주어지지 않은 경우 직접 입력을 요청한다.

### Step 2 — diff 비교

`scripts/compare_json.py`를 실행하여 두 파일의 차이를 출력한다:

```bash
python3 <skill_base_dir>/scripts/compare_json.py <dev_json_path> <prod_json_path>
```

결과를 사용자에게 보여주며 다음 세 범주로 정리한다:
- 🟦 DEV에만 존재하는 API
- 🟧 PROD에만 존재하는 API
- 🔄 내용이 다른 API

차이가 없으면 "두 파일이 동일합니다"를 알리고 워크플로우를 종료한다.

### Step 3 — 반영 방향 및 API 선택 입력 받기

사용자에게 다음을 입력받는다:

1. **반영 방향**:
   - `1` → DEV → PROD (dev 내용을 prod에 반영)
   - `2` → PROD → DEV (prod 내용을 dev에 반영)

2. **적용할 API 번호**:
   - 숫자만 입력 가능 (예: `58, 63`) → 자동으로 `H_58, H_63`으로 변환
   - `H_` prefix 포함해서 입력해도 됨 (예: `H_58, H_63`)
   - `ALL` 입력 시 diff에 나온 모든 API 적용

### Step 4 — 병합 실행

사용자에게 **병원명**을 입력받는다 (예: `hallym`, `snuh`).

출력 파일명: `merged-hsp-{병원명}-request-config.json` (source 파일과 같은 디렉토리에 저장)

```bash
python3 <skill_base_dir>/scripts/merge_json.py \
  <source_json_path> \
  <target_json_path> \
  <dev_to_prod|prod_to_dev> \
  <H_01,H_02 또는 ALL> \
  <output_path>
```

- 방향이 DEV→PROD이면: source=dev, target=prod
- 방향이 PROD→DEV이면: source=prod, target=dev

### Step 5 — 최종 검증 및 확인

병합 후 **merged 파일과 원본 target 파일**을 `compare_json.py`로 다시 비교하여 실제 반영 결과를 사용자에게 보여준다.

- DEV → PROD인 경우: `compare_json.py <merged> <original_prod>`
- PROD → DEV인 경우: `compare_json.py <merged> <original_dev>`

이 결과는 **의도한 API만 변경됐는지** 확인하는 용도다. 선택한 API만 diff에 나타나야 정상이다.

```bash
python3 <skill_base_dir>/scripts/compare_json.py <merged_path> <original_target_path>
```

결과를 보여준 후 아래 내용을 정리하여 최종 확인을 요청한다:

```
반영 방향: DEV → PROD
적용 API: H_58, H_63
변경 내역:
  - H_58: request 변경, response 변경
  - H_63: response 신규 추가
출력 파일: /path/to/merged_20260318_153000.json

위 내용이 맞습니까? (yes/no)
```

- `no` → Step 3으로 돌아가거나 취소
- `yes` → Step 6으로 진행

### Step 6 — 완료 보고

병합 결과를 최종 정리하여 사용자에게 알린다:
- 출력 파일 경로
- 적용된 API 목록 및 변경 내역 요약

## 스크립트 설명

| 스크립트 | 역할 |
|---|---|
| `scripts/compare_json.py` | 두 JSON을 비교하여 diff 출력 및 `.diff_result.json` 저장 |
| `scripts/merge_json.py` | 선택한 API를 source에서 target으로 복사하여 병합 JSON 생성 |

## JSON 구조 참고

최상위에 `request`와 `response` 섹션이 있다:
- `request.{API_KEY}`: methodType, subPath, parameter 정의
- `response.{API_KEY}`: success, error, data 정의
- API 키 형식: `H_01`, `H_02`, ..., `T_33` 등
- `request` 섹션의 `urlPath`, `contentType`, `token`, `header`, `headerList`는 공통 설정으로 비교 대상에서 제외

## 스크립트 실행 경로

스크립트를 실행할 때 `<skill_base_dir>`은 이 SKILL.md가 위치한 디렉토리의 절대 경로를 사용한다.
실행 전 `scripts/` 디렉토리의 절대 경로를 확인하여 사용한다.
