const axios = require('axios');
const { buildAuthorizationHeader } = require('./coupangAuth');

const CREATE_PRODUCT_PATH = '/v2/providers/seller_api/apis/api/v1/marketplace/seller-products';

class CoupangClient {
  constructor({ accessKey, secretKey, vendorId, baseUrl }) {
    if (!accessKey || !secretKey || !vendorId) {
      throw new Error('COUPANG_ACCESS_KEY / COUPANG_SECRET_KEY / COUPANG_VENDOR_ID 환경변수를 모두 설정해야 합니다.');
    }
    this.accessKey = accessKey;
    this.secretKey = secretKey;
    this.vendorId = vendorId;
    this.baseUrl = baseUrl || 'https://api-gateway.coupang.com';
  }

  async createSellerProduct(payload) {
    const method = 'POST';
    const authorization = buildAuthorizationHeader({
      method,
      path: CREATE_PRODUCT_PATH,
      query: '',
      accessKey: this.accessKey,
      secretKey: this.secretKey,
    });

    const response = await axios.post(`${this.baseUrl}${CREATE_PRODUCT_PATH}`, payload, {
      headers: {
        Authorization: authorization,
        'Content-Type': 'application/json;charset=UTF-8',
      },
      validateStatus: () => true,
    });

    return response;
  }
}

module.exports = { CoupangClient, CREATE_PRODUCT_PATH };
