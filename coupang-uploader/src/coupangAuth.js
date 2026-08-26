const crypto = require('crypto');

// 쿠팡 Open API 서명 규칙 (HMAC-SHA256, CEA 알고리즘)
// https://developers.coupangcorp.com 문서의 "HMAC 서명 생성" 규칙을 따른다.
function buildSignedDate(date = new Date()) {
  const pad = (n) => String(n).padStart(2, '0');
  const yy = String(date.getUTCFullYear()).slice(2);
  const MM = pad(date.getUTCMonth() + 1);
  const dd = pad(date.getUTCDate());
  const HH = pad(date.getUTCHours());
  const mm = pad(date.getUTCMinutes());
  const ss = pad(date.getUTCSeconds());
  return `${yy}${MM}${dd}T${HH}${mm}${ss}Z`;
}

function buildAuthorizationHeader({ method, path, query = '', accessKey, secretKey }) {
  const signedDate = buildSignedDate();
  const message = `${signedDate}${method}${path}${query}`;
  const signature = crypto.createHmac('sha256', secretKey).update(message).digest('hex');

  return `CEA algorithm=HmacSHA256, access-key=${accessKey}, signed-date=${signedDate}, signature=${signature}`;
}

module.exports = { buildAuthorizationHeader };
