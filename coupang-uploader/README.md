# 쿠팡 상품 자동업로드 프로그램

엑셀 파일에 상품 정보를 정리해두면, 쿠팡윙(Wing) 오픈 API를 통해 자동으로 상품을 등록해주는
Node.js 프로그램입니다.

## 1. 사전 준비: 쿠팡윙 오픈 API 키 발급

아직 API 키가 없다면 아래 순서로 발급받으세요.

1. [쿠팡윙](https://wing.coupang.com) 판매자 계정으로 로그인
2. 우측 상단 `판매자정보` > `오픈 API 관리` 메뉴로 이동
3. `Access Key`, `Secret Key` 발급 (최초 1회, 재발급 시 기존 키 무효화됨)
4. 같은 화면 또는 `업체정보`에서 `Vendor ID`(예: `A00012345`) 확인
5. `반품지 관리`, `출고지 관리` 메뉴에서 이미 등록해둔 반품지 코드 / 출고지 코드 확인
   (등록된 게 없다면 먼저 반품지·출고지를 하나 등록해야 상품등록이 가능합니다)

## 2. 설치

```bash
cd coupang-uploader
npm install
cp .env.example .env
```

`.env` 파일을 열어 위에서 발급받은 값을 채워 넣습니다.

```
COUPANG_ACCESS_KEY=...
COUPANG_SECRET_KEY=...
COUPANG_VENDOR_ID=A00012345
DEFAULT_RETURN_CENTER_CODE=...
DEFAULT_OUTBOUND_SHIPPING_PLACE_CODE=...
```

## 3. 상품 엑셀 템플릿 만들기

```bash
npm run template
```

`product_template.xlsx` 파일이 생성됩니다. 예시로 들어있는 1행을 참고해서
등록하려는 상품 수만큼 행을 채워주세요. 주요 컬럼 설명:

| 컬럼 | 필수 | 설명 |
|---|---|---|
| sellerProductName | ✅ | 상품 등록명 (내부 관리용) |
| displayCategoryCode | ✅ | 쿠팡 전시 카테고리 코드 (쿠팡윙 카테고리 검색 API/화면에서 확인) |
| itemName | ✅ | 옵션명 (예: "블랙 - L") |
| salePrice | ✅ | 판매가 |
| originalPrice | | 정가 (비워두면 판매가와 동일) |
| stockQuantity | | 판매 가능 재고 수량 |
| images | ✅ | 이미지 URL, 쉼표(,)로 구분. 첫 번째가 대표 이미지 (반드시 인터넷에서 접근 가능한 URL이어야 함) |
| returnCenterCode / outboundShippingPlaceCode | | 비워두면 `.env`의 기본값 사용 |
| searchTags | | 검색어, 쉼표로 구분 |
| noticeCategoryName | | 상품고시정보 카테고리명 (카테고리마다 필수 고시항목이 다름) |
| extraJson | | 위 컬럼으로 표현 안 되는 값을 JSON으로 직접 지정해 덮어쓰기/추가 (예: 상세 고시정보, 인증정보 등) |

> ⚠️ 카테고리별로 필수 고시정보(notices), 인증정보(certifications), 상세속성(attributes)이
> 다릅니다. 이 프로그램은 가장 기본적인 형태로 채워서 보내며, 카테고리 특성상 추가 항목이
> 필요하면 `extraJson` 컬럼에 JSON으로 넣어 보완하세요.

## 4. 실행

먼저 실제 전송 없이 결과를 미리 확인합니다 (dry-run, 기본 동작):

```bash
node upload.js product_template.xlsx
```

콘솔에 각 상품이 어떤 JSON으로 쿠팡에 전송될지 출력됩니다. 문제가 없으면 `--live` 옵션을
붙여 실제로 전송합니다.

```bash
node upload.js product_template.xlsx --live
```

- 행 별로 성공/실패 여부가 콘솔에 출력되고, 같은 폴더에 `product_template_results.xlsx`
  결과 파일이 생성됩니다.
- 실패한 행은 결과 파일의 `message` 컬럼에서 쿠팡이 반환한 오류 메시지를 확인할 수 있습니다.
  (카테고리 코드 오류, 필수 고시정보 누락 등이 흔한 원인입니다)
- 쿠팡 등록 후에도 바로 판매되는 것은 아니고, 쿠팡 상품 검수를 거쳐야 승인됩니다
  (쿠팡윙 `상품관리 > 상품조회/수정`에서 승인 상태 확인 가능).

## 폴더 구조

```
coupang-uploader/
├── upload.js              # 실행 진입점 (엑셀 읽기 -> API 호출)
├── generate-template.js   # 샘플 엑셀 템플릿 생성 스크립트
├── src/
│   ├── coupangAuth.js     # 쿠팡 Open API HMAC 서명 생성
│   ├── coupangClient.js   # 쿠팡 상품등록 API 호출
│   ├── excelLoader.js     # 엑셀 -> JSON 행 변환
│   └── payloadBuilder.js  # 엑셀 행 -> 쿠팡 API 요청 바디 변환
├── .env.example
└── product_template.xlsx  # (npm run template 실행 후 생성)
```
