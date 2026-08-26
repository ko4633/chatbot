require('dotenv').config();
const path = require('path');
const fs = require('fs');
const xlsx = require('xlsx');
const { loadRows } = require('./src/excelLoader');
const { buildProductPayload } = require('./src/payloadBuilder');
const { CoupangClient } = require('./src/coupangClient');

function parseArgs(argv) {
  const args = argv.slice(2);
  const isLive = args.includes('--live');
  const filePath = args.find((a) => !a.startsWith('--'));
  return { filePath, isLive };
}

function writeResults(results, sourceFilePath) {
  const outPath = sourceFilePath.replace(/\.xlsx?$/i, '') + '_results.xlsx';
  const worksheet = xlsx.utils.json_to_sheet(results);
  const workbook = xlsx.utils.book_new();
  xlsx.utils.book_append_sheet(workbook, worksheet, 'results');
  xlsx.writeFile(workbook, outPath);
  return outPath;
}

async function main() {
  const { filePath, isLive } = parseArgs(process.argv);

  if (!filePath) {
    console.error('사용법: node upload.js <엑셀파일경로> [--live]');
    console.error('  --live 옵션 없이 실행하면 실제 전송 없이 미리보기(dry-run)만 합니다.');
    process.exit(1);
  }

  const resolvedPath = path.resolve(filePath);
  if (!fs.existsSync(resolvedPath)) {
    console.error(`파일을 찾을 수 없습니다: ${resolvedPath}`);
    process.exit(1);
  }

  const defaults = {
    vendorId: process.env.COUPANG_VENDOR_ID,
    returnCenterCode: process.env.DEFAULT_RETURN_CENTER_CODE,
    outboundShippingPlaceCode: process.env.DEFAULT_OUTBOUND_SHIPPING_PLACE_CODE,
  };

  let client = null;
  if (isLive) {
    client = new CoupangClient({
      accessKey: process.env.COUPANG_ACCESS_KEY,
      secretKey: process.env.COUPANG_SECRET_KEY,
      vendorId: process.env.COUPANG_VENDOR_ID,
      baseUrl: process.env.COUPANG_API_BASE_URL,
    });
  } else {
    console.log('=== DRY-RUN 모드입니다. 실제로 쿠팡에 전송하지 않습니다. ===');
    console.log('실제로 업로드하려면 마지막에 --live 옵션을 붙여 실행하세요.\n');
  }

  const rows = loadRows(resolvedPath);
  console.log(`${rows.length}개 상품 행을 읽었습니다.\n`);

  const results = [];

  for (let i = 0; i < rows.length; i += 1) {
    const row = rows[i];
    const label = row.sellerProductName || `행 ${i + 2}`;

    try {
      const payload = buildProductPayload(row, defaults);

      if (!isLive) {
        console.log(`[미리보기 ${i + 1}/${rows.length}] ${label}`);
        console.log(JSON.stringify(payload, null, 2));
        console.log('---');
        results.push({ row: i + 2, sellerProductName: label, status: 'DRY_RUN', message: '' });
        continue;
      }

      const response = await client.createSellerProduct(payload);
      const ok = response.status >= 200 && response.status < 300 && response.data?.code === 'SUCCESS';

      if (ok) {
        console.log(`[성공 ${i + 1}/${rows.length}] ${label} -> sellerProductId=${response.data.data}`);
        results.push({
          row: i + 2,
          sellerProductName: label,
          status: 'SUCCESS',
          message: response.data.data,
        });
      } else {
        const message = response.data?.message || JSON.stringify(response.data);
        console.error(`[실패 ${i + 1}/${rows.length}] ${label} -> ${message}`);
        results.push({ row: i + 2, sellerProductName: label, status: 'FAIL', message });
      }

      // 쿠팡 API 초당 호출 제한을 피하기 위해 약간의 지연을 둔다.
      await new Promise((resolve) => setTimeout(resolve, 500));
    } catch (err) {
      const message = err.response?.data?.message || err.message;
      console.error(`[에러 ${i + 1}/${rows.length}] ${label} -> ${message}`);
      results.push({ row: i + 2, sellerProductName: label, status: 'ERROR', message });
    }
  }

  const outPath = writeResults(results, resolvedPath);
  console.log(`\n결과 파일 저장: ${outPath}`);
}

main().catch((err) => {
  console.error('실행 중 오류가 발생했습니다:', err.message);
  process.exit(1);
});
