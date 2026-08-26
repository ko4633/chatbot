const path = require('path');
const xlsx = require('xlsx');

const HEADERS = [
  'sellerProductName',
  'displayCategoryCode',
  'itemName',
  'salePrice',
  'originalPrice',
  'stockQuantity',
  'images',
  'brand',
  'generalProductName',
  'displayProductName',
  'deliveryChargeType',
  'deliveryCharge',
  'returnCenterCode',
  'outboundShippingPlaceCode',
  'returnZipCode',
  'returnAddress',
  'returnAddressDetail',
  'companyContactNumber',
  'barcode',
  'modelNo',
  'searchTags',
  'saleStartedAt',
  'saleEndedAt',
  'noticeCategoryName',
  'extraJson',
];

const EXAMPLE_ROW = {
  sellerProductName: '[샘플] 순면 남성 반팔 티셔츠 3종 세트',
  displayCategoryCode: '76391',
  itemName: '화이트/그레이/블랙 - L',
  salePrice: 19900,
  originalPrice: 25000,
  stockQuantity: 100,
  images: 'https://example.com/images/product1_main.jpg,https://example.com/images/product1_detail1.jpg',
  brand: '샘플브랜드',
  generalProductName: '남성 반팔 티셔츠',
  displayProductName: '순면 남성 반팔 티셔츠 3종 세트',
  deliveryChargeType: 'FREE',
  deliveryCharge: 0,
  returnCenterCode: '여기에_반품지코드',
  outboundShippingPlaceCode: '여기에_출고지코드',
  returnZipCode: '12345',
  returnAddress: '서울특별시 강남구 테헤란로 1',
  returnAddressDetail: '101호',
  companyContactNumber: '0212345678',
  barcode: '',
  modelNo: '',
  searchTags: '티셔츠,여름옷,반팔',
  saleStartedAt: '',
  saleEndedAt: '',
  noticeCategoryName: '의류',
  extraJson: '',
};

const worksheet = xlsx.utils.json_to_sheet([EXAMPLE_ROW], { header: HEADERS });
const workbook = xlsx.utils.book_new();
xlsx.utils.book_append_sheet(workbook, worksheet, 'products');

const outputPath = path.join(__dirname, 'product_template.xlsx');
xlsx.writeFile(workbook, outputPath);

console.log(`템플릿 생성 완료: ${outputPath}`);
console.log('이 파일을 열어서 예시 행을 지우고, 실제 등록할 상품 정보로 채운 뒤 upload.js 에 경로를 넘겨주세요.');
