# Coupang Bulk Upload Assistant V1 (prototype)

이미지 폴더 + 쿠팡 공식 Excel 양식을 넣으면, 품번 기준으로 상품을 자동분류하고
색상×사이즈 옵션을 자동생성해서 쿠팡 공식 Excel에 채워주는 로컬 프로그램.
**Coupang Open API는 쓰지 않는다.** 최종 결과물은 사람이 WING에 직접 업로드한다.

## 지금 상태 (STEP 10까지 완료: 1~5단계 워크플로우 전체 왕복 동작)

사용자가 정의한 작업 순서 그대로 동작 확인됨:

1. **이미지 폴더 + 쿠팡 엑셀 양식 입력** → `image_grouper` + 실제 `.xlsm` 읽기
2. **자동입력 vs 사용자입력 구분해서 제공** → `missing_input_excel.generate_missing_input_excel()`
   부족한 상품만 모아서, 이미 아는 값은 채워두고 부족한 컬럼만 빈칸으로 `추가입력필요.xlsx` 생성
3. **사용자가 보완해서 재입력** → `missing_input_excel.import_missing_input_excel()`
4. **오류체크(재검증)** → `pipeline.apply_overrides_and_revalidate()`: merge 후 옵션 재생성 + 재검증,
   여전히 부족하면 다시 blocked로 남김 (일부만 채워도 나머지 상품은 안 막힘)
5. **완벽한 엑셀 완성** → `excel_writer.write_products()`

그 외 동작 확인된 것:

- 이미지 폴더 스캔 → 품번(productCode) 기준 자동 grouping, `_1~_9` 역할 고정 매핑
- 품번 파싱 → 상품종류코드/시즌코드 인식 (`config/product_code_rules.json`, 모르는 코드는 절대 추측 안 하고 `UNKNOWN`)
- 사이즈 규칙 → DL/DA는 8사이즈, 그 외는 4사이즈 (`config/size_rules.json`)
- 색상 1개 × 사이즈 N개 옵션 row 자동생성, 재고 10 자동입력
- 고정값 자동적용 (`config/fixed_values.json`: 브랜드/제조사/상품상태/과세여부 등)
- 검증(validator) → ERROR/WARNING 분리, 색상·판매가격 없으면 ERROR로 막고 해당 상품만 제외 (batch 전체는 안 죽음)
- **실제 쿠팡 공식 `.xlsm` 템플릿**(`fixtures/coupang_template_v4.6.xlsm`)에 진짜로 값을 써서 저장
  - 1~4행(안내/헤더 영역), 다른 시트(`기본`/`2. 식품`/`3. 가전`/`hidden`/`env`)는 **완전히 원본 그대로** 유지되는지 자동 테스트로 검증됨
  - 5행부터 있던 샘플 예시행은 지우고 우리 데이터로 덮어씀

아직 안 만든 것 (다음 단계):

- Vision(GPT) 라벨 이미지(`_8`/`_9`) 분석 — 실제 라벨 사진 샘플 + OpenAI API 키 필요 (지금은 소재/제조국 등도
  전부 `추가입력필요.xlsx`를 통한 수동입력으로 처리됨. Vision이 붙으면 이 컬럼들이 자동으로 채워져서
  `추가입력필요.xlsx`에 아예 안 나타나게 됨)
- 로컬 웹 UI (지금은 Python 함수 호출/pytest로만 검증됨)
- 진짜 WING에서 방금 다운로드한 원본 파일로의 재검증 (지금 쓰는 `fixtures/coupang_template_v4.6.xlsm`은 예시/참고 파일이라 매크로가 비어있음 — 실제 파일은 매크로가 있을 수 있음)

## 실행

```bash
cd coupang-bulk-upload
pip install -r requirements.txt
python3 -m pytest -v
```

17개 테스트 전부 통과해야 정상.

## 폴더 구조

```
coupang-bulk-upload/
├── config/
│   ├── product_code_rules.json   # 품번 -> 상품종류/시즌 규칙 (여기만 고치면 됨)
│   ├── size_rules.json           # 사이즈 규칙 (DL/DA vs 기본)
│   └── fixed_values.json         # 고정값 (브랜드/제조사/재고 등)
├── core/
│   ├── models.py                 # Product/OptionRow/Issue 데이터 모델
│   ├── image_grouper.py          # 파일명 -> 품번 grouping, _1~_9 역할 분류, 오류 검출
│   ├── product_code_parser.py    # 품번 문자열 파싱 (config 기반, 모르는 코드는 UNKNOWN)
│   ├── size_rules.py             # 상품종류 -> 사이즈 목록
│   ├── option_expander.py        # 색상 x 사이즈 -> 옵션 row 생성
│   ├── validator.py               # ERROR/WARNING 검증
│   ├── missing_input_excel.py    # 추가입력필요.xlsx 생성 / 재import (2~3단계)
│   ├── excel_writer.py           # 실제 쿠팡 엑셀에 값 쓰기 (openpyxl, 헤더 기반 컬럼 매핑)
│   └── pipeline.py               # 위 전부를 이어붙인 오케스트레이터 (1~5단계 전체)
├── fixtures/
│   └── coupang_template_v4.6.xlsm  # 실제 쿠팡 공식 양식 샘플 (사용자 제공)
└── tests/                        # 단위테스트 + 통합테스트(실제 xlsm에 쓰고 원본보존 검증)
```

## 알아둘 것 (설계상 중요한 판단)

- **컬럼 매핑은 하드코딩된 번호가 아니라 "(1행 그룹명, 2행 필드명)" 헤더를 읽어서 찾는다** (`excel_writer.build_header_map`).
  실제 파일에서 "옵션유형1" 같은 필드명이 구매옵션/검색옵션 그룹에 중복 등장해서, 그룹명까지 같이 키로 써야 정확히 구분됨.
- **대표/추가 이미지 컬럼은 절대 자동으로 채우지 않는다 (확정, 근거 있음).** WING '이미지(파일) 업로드'에서
  파일명이 중복되면(예: 같은 파일을 상품이미지 탭과 상세설명 탭에 올리는 경우) WING이 서버에서 예측
  불가능한 랜덤 접미사를 붙여 파일명을 바꾼다 — 실제로 `TRHKA5F841156_2.jpg`가
  `TRHKA5F841156_2_kbqso.jpg`로 바뀌는 걸 스크린샷으로 확인함. 이 값은 업로드 전에는 알 수 없으므로,
  사용자가 WING에서 실제 업로드 후 '복사' 버튼으로 나온 값을 최종 엑셀에 직접 붙여넣어야 한다.
