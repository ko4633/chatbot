const dayjs = require('dayjs');

function toNumber(value, fallback = 0) {
  if (value === undefined || value === null || value === '') return fallback;
  const n = Number(value);
  return Number.isNaN(n) ? fallback : n;
}

function splitList(value) {
  if (!value) return [];
  return String(value)
    .split(',')
    .map((v) => v.trim())
    .filter(Boolean);
}

function parseExtraJson(value) {
  if (!value) return {};
  try {
    return JSON.parse(value);
  } catch (err) {
    throw new Error(`extraJson 컬럼의 JSON 형식이 올바르지 않습니다: ${err.message}`);
  }
}

// 엑셀 한 행(row)을 쿠팡 상품등록 API 요청 바디로 변환한다.
// 카테고리별 필수 고시정보(notices), 인증정보(certifications) 등은 상품마다 달라서
// 일반화가 어려우므로 extraJson 컬럼으로 필요한 값을 덮어쓰거나 추가할 수 있게 했다.
function buildProductPayload(row, defaults) {
  const missing = ['sellerProductName', 'displayCategoryCode', 'itemName', 'salePrice'].filter(
    (key) => !row[key] && row[key] !== 0
  );
  if (missing.length) {
    throw new Error(`필수 항목 누락: ${missing.join(', ')}`);
  }

  const returnCenterCode = row.returnCenterCode || defaults.returnCenterCode;
  const outboundShippingPlaceCode = row.outboundShippingPlaceCode || defaults.outboundShippingPlaceCode;
  if (!returnCenterCode || !outboundShippingPlaceCode) {
    throw new Error(
      'returnCenterCode / outboundShippingPlaceCode 가 없습니다. 엑셀 컬럼으로 입력하거나 .env의 DEFAULT_RETURN_CENTER_CODE / DEFAULT_OUTBOUND_SHIPPING_PLACE_CODE 를 설정하세요.'
    );
  }

  const images = splitList(row.images).map((url, idx) => ({
    imageOrder: idx,
    imageType: idx === 0 ? 'REPRESENTATION' : 'DETAIL',
    vendorPath: url,
  }));
  if (images.length === 0) {
    throw new Error('images 컬럼에 최소 1개 이상의 이미지 URL이 필요합니다.');
  }

  const saleStartedAt = row.saleStartedAt
    ? dayjs(row.saleStartedAt).format('YYYY-MM-DDTHH:mm:ss')
    : dayjs().format('YYYY-MM-DDTHH:mm:ss');
  const saleEndedAt = row.saleEndedAt
    ? dayjs(row.saleEndedAt).format('YYYY-MM-DDTHH:mm:ss')
    : dayjs().add(2, 'year').format('YYYY-MM-DDTHH:mm:ss');

  const basePayload = {
    displayCategoryCode: Number(row.displayCategoryCode),
    sellerProductName: String(row.sellerProductName),
    vendorId: defaults.vendorId,
    vendorUserId: row.vendorUserId || undefined,
    saleStartedAt,
    saleEndedAt,
    displayProductName: row.displayProductName || row.sellerProductName,
    brand: row.brand || '',
    generalProductName: row.generalProductName || row.sellerProductName,
    productGroup: row.productGroup || undefined,
    deliveryMethod: row.deliveryMethod || 'SEQUENCIAL',
    deliveryCompanyCode: row.deliveryCompanyCode || 'CJGLS',
    deliveryChargeType: row.deliveryChargeType || 'FREE',
    deliveryCharge: toNumber(row.deliveryCharge, 0),
    freeShipOverAmount: toNumber(row.freeShipOverAmount, 0),
    deliveryChargeOnReturn: toNumber(row.deliveryChargeOnReturn, 2500),
    remoteAreaDeliverable: row.remoteAreaDeliverable || 'N',
    unionDeliveryType: row.unionDeliveryType || 'NOT_UNION_DELIVERY',
    returnCenterCode,
    returnChargeName: row.returnChargeName || '반품지',
    companyContactNumber: row.companyContactNumber || '',
    returnZipCode: row.returnZipCode || '',
    returnAddress: row.returnAddress || '',
    returnAddressDetail: row.returnAddressDetail || '',
    returnCharge: toNumber(row.returnCharge, 2500),
    outboundShippingPlaceCode,
    items: [
      {
        itemName: String(row.itemName),
        originalPrice: toNumber(row.originalPrice, toNumber(row.salePrice)),
        salePrice: toNumber(row.salePrice),
        maximumBuyCount: toNumber(row.stockQuantity, 999),
        maximumBuyForPerson: toNumber(row.maximumBuyForPerson, 0),
        maximumBuyForPersonPeriod: toNumber(row.maximumBuyForPersonPeriod, 1),
        outboundShippingTimeDay: toNumber(row.outboundShippingTimeDay, 2),
        unitCount: toNumber(row.unitCount, 1),
        adultOnly: row.adultOnly || 'EVERYONE',
        taxType: row.taxType || 'TAX',
        parallelImported: row.parallelImported || 'NOT_PARALLEL_IMPORTED',
        overseasPurchased: row.overseasPurchased || 'NOT_OVERSEAS_PURCHASED',
        pccNeeded: row.pccNeeded === true || row.pccNeeded === 'true',
        externalVendorSku: row.externalVendorSku || undefined,
        barcode: row.barcode || '',
        emptyBarcode: row.barcode ? false : true,
        emptyBarcodeReason: row.barcode ? undefined : '바코드 없는 상품',
        modelNo: row.modelNo || undefined,
        searchTags: splitList(row.searchTags),
        images,
        notices: [
          {
            noticeCategoryName: row.noticeCategoryName || '기타 재화',
            noticeCategoryDetailNames: [
              { noticeCategoryDetailName: '품명 및 모델명', content: row.sellerProductName },
              { noticeCategoryDetailName: '상품상세 참조', content: '상세페이지 참조' },
            ],
          },
        ],
      },
    ],
    requested: false,
  };

  const merged = { ...basePayload, ...parseExtraJson(row.extraJson) };
  return merged;
}

module.exports = { buildProductPayload };
