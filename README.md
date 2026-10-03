# chatbot

## blog_brief.py — 일본 정보 블로그 브리핑 생성기

글은 직접 쓰고, 프로그램은 재료(정보·링크·이미지)만 모아 줍니다.

```bash
pip install -r requirements.txt
cp .env.example .env   # ANTHROPIC_API_KEY 입력
python blog_brief.py "도쿄 팝업" --count 3
python blog_brief.py "일본 향수" --region 오사카 --count 5
```

- 모델: 환경변수 `CLAUDE_MODEL` (기본 `claude-sonnet-5-5`)
- 출력: `briefs/날짜_분야/` 아래 `브리핑.html`(자동으로 열림), `브리핑.md`, `data.json`, `images/`
- 링크 검증: 원문/공식 URL마다 ① 실제 web_search 결과에 있던 URL인지 ② HTTP 접속이 되는지 확인하고,
  페이지에 원제 키워드가 있는지와 종료 표현(販売終了 등)이 있는지도 봅니다. 하나라도 걸리면 카드에 ⚠ 경고가 붙습니다.
- 종료일이 오늘 이전인 항목은 자동으로 빠지고, HTML 하단의 "자동 제외된 항목"에 기록됩니다.
- `--no-open`: 브라우저를 열지 않음
