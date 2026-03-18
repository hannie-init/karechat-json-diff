# karechat-json-diff

karechat HTTP API 인터페이스 JSON 파일의 **개발(dev) ↔ 운영(prod) 환경 간 diff 및 선택적 병합**을 지원하는 Claude Code 스킬입니다.

## 주요 기능

- dev/prod JSON 파일 간 차이를 API 번호별로 분류하여 표시
- 반영 방향(dev→prod / prod→dev)과 적용할 API를 선택적으로 지정
- 병합 후 실제 변경 내용을 재검증하여 의도한 API만 반영됐는지 확인
- 결과 파일을 `merged-hsp-{병원명}-request-config.json` 형식으로 저장

## 설치

`~/.claude/skills/` 디렉토리에 클론합니다.

```bash
git clone https://github.com/hannie-init/karechat-json-diff.git ~/.claude/skills/karechat-json-diff
```

Claude Code를 재시작하면 스킬이 자동으로 로드됩니다.

## 사용법

새 대화에서 아래 키워드 중 하나를 입력하면 스킬이 트리거됩니다:

- `convert json 변환`
- `인터페이스 설계서 json 변환`
- `컨퍼트 json 변환`

### 워크플로우

```
Step 1. dev / prod JSON 파일 경로 입력
Step 2. 환경 간 diff 확인 (API별 분류)
Step 3. 반영 방향 및 적용할 API 번호 선택
Step 4. 병원명 입력 후 병합 실행
Step 5. 최종 검증 (merged vs 원본 target diff)
Step 6. 완료 보고
```

### API 번호 입력 예시

```
# 숫자만 입력 (H_ 자동 보완)
58, 63

# prefix 포함 입력도 가능
H_58, H_63

# 전체 적용
ALL
```

## 파일 구조

```
karechat-json-diff/
├── SKILL.md                  # 스킬 정의 및 워크플로우
└── scripts/
    ├── compare_json.py       # 두 JSON 파일 비교 (API별 diff)
    └── merge_json.py         # 선택한 API 병합
```

### JSON 구조

대상 JSON 파일은 아래 구조를 따릅니다:

```json
{
  "request": {
    "urlPath": "...",
    "headerList": { ... },
    "H_01": { "methodType": "GET", "subPath": "...", "parameter": { ... } },
    "H_02": { ... }
  },
  "response": {
    "H_01": { "success": { ... }, "error": { ... }, "data": { ... } },
    "H_02": { ... }
  }
}
```

## 스크립트 직접 실행

스킬 없이 스크립트만 단독으로 사용할 수도 있습니다.

```bash
# diff 비교
python3 scripts/compare_json.py dev.json prod.json

# 병합 (숫자 입력 가능)
python3 scripts/merge_json.py dev.json prod.json dev_to_prod "58,63" merged-hsp-hallym-request-config.json
```

## 요구사항

- Python 3.7+
- Claude Code (스킬 기능 사용 시)
