#!/usr/bin/env python3
"""네이버 블로그용 일본 정보 브리핑 생성기.

글은 직접 쓰고, 이 프로그램은 재료(정보 + 링크 + 이미지)만 모은다.

사용법:
    python blog_brief.py "도쿄 팝업" [--region 시부야] [--count 5] [--no-open]

출력: briefs/YYYY-MM-DD_분야/ 아래에 브리핑.html, 브리핑.md, data.json, images/
"""

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import mimetypes
import os
import re
import sys
import webbrowser
from pathlib import Path
from urllib.parse import parse_qsl, quote_plus, urlencode, urljoin, urlsplit, urlunsplit
from zoneinfo import ZoneInfo

import anthropic
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

DEFAULT_MODEL = "claude-sonnet-5-5"
# 서버측 refusal fallback("default" 형식)을 받는 모델
FALLBACK_MODELS = {"claude-sonnet-5-5", "claude-opus-5-5", "claude-opus-5", "claude-fable-5-1"}
MAX_CONTINUATIONS = 8
JST = ZoneInfo("Asia/Tokyo")
HTTP_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/128.0 Safari/537.36"
    ),
    "Accept-Language": "ja,ko;q=0.8,en;q=0.6",
}
HTTP_TIMEOUT = 15
# 페이지 본문에 이런 표현이 있으면 종료 가능성 경고
ENDED_MARKERS = [
    "終了しました", "販売終了", "受付終了", "閉店しました", "閉店いたしました",
    "営業終了", "開催終了", "終売", "完売しました", "閉幕",
]
TRACKING_PARAMS = {"fbclid", "gclid", "yclid", "ref"}


# ---------------------------------------------------------------- 날짜·계절

def season_of(month: int) -> str:
    if month in (3, 4, 5):
        return "봄(春)"
    if month in (6, 7, 8):
        return "여름(夏)"
    if month in (9, 10, 11):
        return "가을(秋)"
    return "겨울(冬)"


def parse_date(value) -> dt.date | None:
    if not value or not isinstance(value, str):
        return None
    m = re.search(r"(\d{4})[-/.年](\d{1,2})[-/.月](\d{1,2})", value)
    if not m:
        return None
    try:
        return dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None


# ---------------------------------------------------------------- Claude 검색

SYSTEM_PROMPT = """\
당신은 한국 네이버 블로거를 위한 일본 현지 정보 리서처입니다.
블로거가 직접 글을 쓰므로, 당신은 정확한 사실 재료만 모아 줍니다.

원칙:
- 반드시 web_search 도구로 찾은 페이지에 근거해서만 작성합니다. 기억이나 추측으로 쓰지 않습니다.
- 일본어로 검색합니다. 공식 사이트, PR TIMES(prtimes.jp), 일본 매체(Fashion Press, Walkerplus,
  TimeOut Tokyo 일본판, 각 매장 공식 페이지 등)를 우선합니다. 한국어 블로그·한국 매체는 근거로 쓰지 않습니다.
- URL은 web_search 결과에 실제로 나온 URL을 글자 그대로 복사합니다. URL을 조합·추측·단축·수정하면 안 됩니다.
  공식 URL이 검색 결과에 없으면 official_url은 null로 둡니다.
- 오늘 날짜 기준으로 이미 끝난 행사, 판매 종료, 폐점, 품절 종료된 것은 넣지 않습니다.
  기간이 확인되지 않거나 종료 여부가 불확실하면 넣지 않습니다.
- 지금 계절에 어울리지 않는 것(예: 여름에 뜨거운 나베 전문점, 겨울에 빙수 팝업)은 넣지 않습니다.
- 한국에 덜 알려진 것을 우선합니다. 이미 한국에서 유명한 대형 체인·관광 명소보다 새로운 것, 현지 화제를 고릅니다.
- 요약은 사실 위주로 3~4문장, 한국어로 씁니다. 과장·광고 문구는 쓰지 않습니다.
"""


def build_user_prompt(field: str, region: str | None, count: int, today: dt.date, season: str) -> str:
    where = f"지역: {region}\n" if region else ""
    return f"""\
오늘 날짜: {today.isoformat()} (일본 시간), 계절: {season}
분야: {field}
{where}필요한 항목 수: {count}개

위 분야에서 지금({today.isoformat()}) 시점에 블로그에 소개하기 좋은 일본 정보를 {count}개 찾아 주세요.
- 진행 중이거나 곧 시작하는 것, 지금 살 수 있는 것만.
- 후보를 넉넉히 찾은 뒤 기간·종료 여부·계절 적합성을 확인해서 걸러 주세요.

마지막 답변은 아래 형식의 JSON 하나만 ```json 코드블록에 넣어 주세요. 다른 설명은 코드블록 밖에 짧게만.

```json
{{
  "items": [
    {{
      "title_ko": "한국어 제목",
      "title_ja": "일본어 원제 (원문 그대로)",
      "category": "분류 (예: 팝업스토어, 신상품, 전시, 카페, 매장 오픈)",
      "summary": "사실 위주 3~4문장 한국어 요약",
      "why_now": "지금 쓸 이유 (기간 한정, 신규 오픈, 계절 한정 등)",
      "period": "기간 원문 표기 (예: 2026年10月1日(水)～10月14日(火))",
      "start_date": "YYYY-MM-DD 또는 null",
      "end_date": "YYYY-MM-DD 또는 null (상시 판매·상설이면 null)",
      "price": "가격 (원문 표기, 없으면 null)",
      "place_name": "장소명 (일본어 원문, 없으면 null)",
      "address": "주소 (일본어 원문, 없으면 null)",
      "source_url": "근거가 된 기사/보도자료 URL (web_search 결과의 URL 그대로)",
      "official_url": "공식 페이지 URL (web_search 결과에 있을 때만, 없으면 null)",
      "korea_note": "한국에서의 인지도에 대한 짧은 메모"
    }}
  ]
}}
```
"""


def web_search_tool(model: str) -> dict:
    # 동적 필터링 버전은 4.6 이상 모델만 지원
    old = re.search(r"claude-(?:3|haiku-4-5|sonnet-4-5|opus-4-5|opus-4-1|opus-4-0|sonnet-4-0)", model)
    return {
        "type": "web_search_20250305" if old else "web_search_20260209",
        "name": "web_search",
        "max_uses": 20,
        "user_location": {
            "type": "approximate",
            "country": "JP",
            "city": "Tokyo",
            "timezone": "Asia/Tokyo",
        },
    }


def _walk_urls(obj, out: set[str]) -> None:
    """도구 결과 블록 안의 모든 url 필드를 모은다."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "url" and isinstance(v, str) and v.startswith("http"):
                out.add(v)
            else:
                _walk_urls(v, out)
    elif isinstance(obj, list):
        for v in obj:
            _walk_urls(v, out)


def collect_search_urls(content) -> tuple[set[str], int]:
    """응답 content에서 실제 web_search 결과 URL과 검색 횟수를 뽑는다."""
    urls: set[str] = set()
    searches = 0
    for block in content:
        data = block.model_dump() if hasattr(block, "model_dump") else block
        btype = data.get("type", "")
        if btype == "server_tool_use" and data.get("name") == "web_search":
            searches += 1
        if btype.endswith("_tool_result"):
            _walk_urls(data.get("content"), urls)
        if btype == "text":
            for c in data.get("citations") or []:
                if isinstance(c, dict) and c.get("url"):
                    urls.add(c["url"])
    return urls, searches


def run_research(client: anthropic.Anthropic, model: str, user_prompt: str) -> tuple[str, set[str], int]:
    messages = [{"role": "user", "content": user_prompt}]
    kwargs = dict(
        model=model,
        max_tokens=32000,
        system=SYSTEM_PROMPT,
        tools=[web_search_tool(model)],
    )
    use_fallback = model in FALLBACK_MODELS
    all_content = []

    for turn in range(MAX_CONTINUATIONS + 1):
        print(f"  · Claude 검색 요청 {turn + 1}회차 ...", flush=True)
        if use_fallback:
            stream_ctx = client.beta.messages.stream(
                messages=messages,
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",
                **kwargs,
            )
        else:
            stream_ctx = client.messages.stream(messages=messages, **kwargs)
        with stream_ctx as stream:
            response = stream.get_final_message()

        all_content.extend(response.content)
        if response.stop_reason == "pause_turn":
            # 서버측 검색 루프가 중간에 멈춤 → 응답을 그대로 붙여 다시 요청하면 이어서 진행
            messages = [
                {"role": "user", "content": user_prompt},
                {"role": "assistant", "content": response.content},
            ]
            continue
        if response.stop_reason == "refusal":
            raise RuntimeError("모델이 요청을 거절했습니다(stop_reason=refusal).")
        if response.stop_reason == "max_tokens":
            print("  ! 응답이 max_tokens에서 잘렸습니다. 결과가 불완전할 수 있습니다.", file=sys.stderr)
        break
    else:
        print(f"  ! pause_turn이 {MAX_CONTINUATIONS}회를 넘어 중단했습니다.", file=sys.stderr)

    urls, searches = collect_search_urls(all_content)
    final_text = "".join(
        b.text for b in response.content if getattr(b, "type", None) == "text"
    )
    return final_text, urls, searches


def extract_json(text: str) -> dict:
    blocks = re.findall(r"```json\s*(.*?)```", text, re.S)
    candidates = list(reversed(blocks)) or [text]
    for cand in candidates:
        cand = cand.strip()
        start, end = cand.find("{"), cand.rfind("}")
        if start == -1 or end == -1:
            continue
        try:
            return json.loads(cand[start : end + 1])
        except json.JSONDecodeError:
            continue
    raise ValueError("Claude 응답에서 JSON을 찾지 못했습니다.\n--- 응답 ---\n" + text[-2000:])


# ---------------------------------------------------------------- 링크 검증

def normalize_url(url: str) -> str:
    try:
        p = urlsplit(url.strip())
    except ValueError:
        return url.strip()
    host = p.netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    path = p.path.rstrip("/") or "/"
    query = urlencode(
        sorted(
            (k, v)
            for k, v in parse_qsl(p.query, keep_blank_values=True)
            if not k.lower().startswith("utm_") and k.lower() not in TRACKING_PARAMS
        )
    )
    return urlunsplit(("https", host, path, query, ""))


def fetch_page(url: str) -> dict:
    """HTTP 접속 확인 + HTML 확보."""
    result = {"ok": False, "status": None, "final_url": None, "error": None, "html": ""}
    try:
        r = requests.get(url, headers=HTTP_HEADERS, timeout=HTTP_TIMEOUT, allow_redirects=True)
        result["status"] = r.status_code
        result["final_url"] = r.url
        result["ok"] = r.status_code < 400
        ctype = r.headers.get("Content-Type", "")
        if result["ok"] and "html" in ctype.lower():
            if not r.encoding or r.encoding.lower() == "iso-8859-1":
                r.encoding = r.apparent_encoding
            result["html"] = r.text
    except requests.RequestException as e:
        result["error"] = f"{type(e).__name__}: {e}"[:200]
    return result


def title_keywords(title_ja: str | None) -> list[str]:
    if not title_ja:
        return []
    parts = re.split(r"[\s　「」『』【】（）()\[\]・、。,.!！?？:：/／\-‐―〜～×&＆\"'“”]+", title_ja)
    return [p for p in parts if len(p) >= 2][:8]


def page_text(soup: BeautifulSoup) -> str:
    for t in soup(["script", "style", "noscript"]):
        t.decompose()
    return soup.get_text(" ", strip=True)


def check_link(url: str | None, search_set: set[str], keywords: list[str]) -> dict:
    if not url:
        return {"url": None}
    info = {
        "url": url,
        "in_search_results": normalize_url(url) in search_set,
    }
    page = fetch_page(url)
    info.update({k: page[k] for k in ("ok", "status", "final_url", "error")})
    warnings = []
    if not info["in_search_results"]:
        warnings.append("web_search 결과에 없던 URL (생성/변형 의심)")
    if not page["ok"]:
        reason = f"HTTP {page['status']}" if page["status"] else (page["error"] or "접속 실패")
        warnings.append(f"접속 실패: {reason}")

    info["og_image"] = None
    info["page_title"] = None
    if page["html"]:
        soup = BeautifulSoup(page["html"], "html.parser")
        if soup.title and soup.title.string:
            info["page_title"] = soup.title.string.strip()[:200]
        og = soup.find("meta", attrs={"property": "og:image"}) or soup.find(
            "meta", attrs={"name": "twitter:image"}
        )
        if og and og.get("content"):
            info["og_image"] = urljoin(page["final_url"] or url, og["content"].strip())
        text = page_text(soup)
        if keywords:
            hits = [k for k in keywords if k in text or k in (info["page_title"] or "")]
            info["keyword_hits"] = hits
            if not hits:
                warnings.append("페이지 본문에서 원제 키워드를 찾지 못함 (내용 불일치 가능)")
        ended = [m for m in ENDED_MARKERS if m in text]
        if ended:
            info["ended_markers"] = ended
            warnings.append("페이지에 종료 표현 감지: " + ", ".join(ended[:3]) + " (직접 확인 필요)")
    info["warnings"] = warnings
    return info


# ---------------------------------------------------------------- 이미지·지도

def download_image(img_url: str, dest_dir: Path, stem: str) -> str | None:
    try:
        r = requests.get(img_url, headers=HTTP_HEADERS, timeout=HTTP_TIMEOUT)
    except requests.RequestException:
        return None
    ctype = r.headers.get("Content-Type", "").split(";")[0].strip().lower()
    if r.status_code >= 400 or not ctype.startswith("image/") or len(r.content) < 1000:
        return None
    ext = mimetypes.guess_extension(ctype) or ".jpg"
    if ext == ".jpe":
        ext = ".jpg"
    dest_dir.mkdir(parents=True, exist_ok=True)
    path = dest_dir / f"{stem}{ext}"
    path.write_bytes(r.content)
    return f"images/{path.name}"


def maps_link(place: str | None, address: str | None) -> str | None:
    query = " ".join(x for x in (place, address) if x)
    if not query:
        return None
    return "https://www.google.com/maps/search/?api=1&query=" + quote_plus(query)


# ---------------------------------------------------------------- 출력

def safe_dirname(text: str) -> str:
    return re.sub(r'[\\/:*?"<>|\s]+', "_", text).strip("_") or "brief"


def esc(v) -> str:
    return html.escape(str(v)) if v not in (None, "") else ""


def render_html(meta: dict, items: list[dict]) -> str:
    cards = []
    for i, it in enumerate(items, 1):
        warns = it["warnings"]
        img = (
            f'<img src="{esc(it["image"]["path"])}" alt="">'
            f'<div class="credit">이미지 출처: {esc(it["image"]["domain"])}</div>'
            if it.get("image")
            else '<div class="noimg">이미지 없음</div>'
        )
        rows = [
            ("기간", it.get("period")),
            ("가격", it.get("price")),
            ("장소", it.get("place_name")),
            ("주소", it.get("address")),
        ]
        dl = "".join(f"<dt>{k}</dt><dd>{esc(v)}</dd>" for k, v in rows if v)
        buttons = []
        for key, label in (("source", "원문"), ("official", "공식")):
            link = it["links"].get(key) or {}
            if link.get("url"):
                cls = "btn" if not link.get("warnings") else "btn warn"
                buttons.append(
                    f'<a class="{cls}" href="{esc(link["url"])}" target="_blank" rel="noopener">{label}</a>'
                )
        if it.get("maps_url"):
            buttons.append(
                f'<a class="btn map" href="{esc(it["maps_url"])}" target="_blank" rel="noopener">구글맵</a>'
            )
        warn_html = (
            '<ul class="warnings">' + "".join(f"<li>⚠ {esc(w)}</li>" for w in warns) + "</ul>"
            if warns
            else '<div class="okline">✓ 링크 검증 통과</div>'
        )
        cards.append(
            f"""<article class="card{' has-warn' if warns else ''}">
  <div class="thumb">{img}</div>
  <div class="body">
    <div class="cat">{i}. {esc(it.get('category'))}</div>
    <h2>{esc(it.get('title_ko'))}</h2>
    <div class="ja">{esc(it.get('title_ja'))}</div>
    <p class="summary">{esc(it.get('summary'))}</p>
    <p class="why"><b>지금 쓸 이유</b> {esc(it.get('why_now'))}</p>
    <dl>{dl}</dl>
    {warn_html}
    <div class="buttons">{''.join(buttons)}</div>
  </div>
</article>"""
        )
    excluded = ""
    if meta.get("excluded"):
        excluded = (
            '<section class="excluded"><h3>자동 제외된 항목</h3><ul>'
            + "".join(f"<li>{esc(x['title'])} — {esc(x['reason'])}</li>" for x in meta["excluded"])
            + "</ul></section>"
        )
    return f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(meta['field'])} 브리핑 {esc(meta['date'])}</title>
<style>
:root {{ --bg:#f6f6f3; --card:#fff; --ink:#1d1d1f; --sub:#6b6b70; --line:#e4e4e0;
  --accent:#03c75a; --warn:#d9480f; --warnbg:#fff4e6; }}
@media (prefers-color-scheme: dark) {{ :root {{ --bg:#141414; --card:#1f1f1f; --ink:#ececec;
  --sub:#a0a0a0; --line:#333; --warnbg:#3a2412; }} }}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--bg); color:var(--ink);
  font-family:-apple-system,"Apple SD Gothic Neo","Malgun Gothic","Noto Sans KR","Hiragino Sans",sans-serif; }}
header {{ max-width:960px; margin:0 auto; padding:28px 16px 8px; }}
header h1 {{ margin:0 0 6px; font-size:24px; }}
header p {{ margin:0; color:var(--sub); font-size:14px; }}
main {{ max-width:960px; margin:0 auto; padding:16px; display:grid; gap:18px; }}
.card {{ background:var(--card); border:1px solid var(--line); border-radius:14px; overflow:hidden;
  display:grid; grid-template-columns:300px 1fr; }}
.card.has-warn {{ border-color:var(--warn); }}
.thumb {{ background:#0001; }}
.thumb img {{ width:100%; height:100%; max-height:320px; object-fit:cover; display:block; }}
.credit {{ font-size:11px; color:var(--sub); padding:4px 8px; }}
.noimg {{ display:flex; align-items:center; justify-content:center; height:100%; min-height:160px; color:var(--sub); }}
.body {{ padding:16px 20px; }}
.cat {{ color:var(--accent); font-weight:700; font-size:13px; }}
h2 {{ margin:4px 0 2px; font-size:19px; }}
.ja {{ color:var(--sub); font-size:13px; margin-bottom:10px; }}
.summary {{ line-height:1.65; margin:8px 0; }}
.why {{ font-size:14px; margin:8px 0; }}
dl {{ display:grid; grid-template-columns:48px 1fr; gap:4px 10px; font-size:14px; margin:10px 0; }}
dt {{ color:var(--sub); }} dd {{ margin:0; }}
.warnings {{ background:var(--warnbg); color:var(--warn); border-radius:8px; padding:8px 12px 8px 28px;
  font-size:13px; margin:10px 0; }}
.okline {{ color:var(--accent); font-size:13px; margin:10px 0; }}
.buttons {{ display:flex; gap:8px; flex-wrap:wrap; }}
.btn {{ display:inline-block; padding:7px 14px; border-radius:999px; background:var(--ink); color:var(--card);
  text-decoration:none; font-size:14px; }}
.btn.map {{ background:#1a73e8; color:#fff; }}
.btn.warn {{ background:var(--warn); color:#fff; }}
.excluded {{ font-size:13px; color:var(--sub); }}
@media (max-width:700px) {{ .card {{ grid-template-columns:1fr; }} }}
</style></head>
<body>
<header>
  <h1>{esc(meta['field'])}{(' · ' + esc(meta['region'])) if meta.get('region') else ''} 브리핑</h1>
  <p>{esc(meta['date'])} · {esc(meta['season'])} · 모델 {esc(meta['model'])} ·
     링크 {meta['link_stats']['ok']}/{meta['link_stats']['total']} 정상 · 검색 결과 URL {meta['search_url_count']}개</p>
</header>
<main>
{''.join(cards) if cards else '<p>조건에 맞는 항목이 없습니다.</p>'}
{excluded}
</main>
</body></html>
"""


def render_md(meta: dict, items: list[dict]) -> str:
    out = [
        f"# {meta['field']}{(' · ' + meta['region']) if meta.get('region') else ''} 브리핑 ({meta['date']}, {meta['season']})",
        "",
    ]
    for i, it in enumerate(items, 1):
        out += [f"## {i}. {it.get('title_ko')}", "", f"- 원제: {it.get('title_ja')}", f"- 분류: {it.get('category')}"]
        for label, key in (("기간", "period"), ("가격", "price"), ("장소", "place_name"), ("주소", "address")):
            if it.get(key):
                out.append(f"- {label}: {it[key]}")
        out += ["", it.get("summary") or "", "", f"**지금 쓸 이유:** {it.get('why_now')}", ""]
        src = it["links"].get("source") or {}
        off = it["links"].get("official") or {}
        if src.get("url"):
            out.append(f"- 원문: {src['url']}")
        if off.get("url"):
            out.append(f"- 공식: {off['url']}")
        if it.get("maps_url"):
            out.append(f"- 구글맵: {it['maps_url']}")
        if it.get("image"):
            out.append(f"- 이미지: {it['image']['path']} (출처: {it['image']['domain']})")
        for w in it["warnings"]:
            out.append(f"- ⚠ {w}")
        out.append("")
    return "\n".join(out)


# ---------------------------------------------------------------- 메인 처리

def process_items(raw_items: list[dict], search_urls: set[str], today: dt.date, out_dir: Path):
    search_set = {normalize_url(u) for u in search_urls}
    items, excluded = [], []
    for raw in raw_items:
        title = raw.get("title_ko") or raw.get("title_ja") or "(제목 없음)"
        end = parse_date(raw.get("end_date"))
        if end and end < today:
            excluded.append({"title": title, "reason": f"종료일 {end.isoformat()}이 오늘 이전"})
            continue
        if not raw.get("source_url"):
            excluded.append({"title": title, "reason": "source_url 없음"})
            continue
        print(f"  · 검증: {title}", flush=True)
        kws = title_keywords(raw.get("title_ja"))
        links = {
            "source": check_link(raw.get("source_url"), search_set, kws),
            "official": check_link(raw.get("official_url"), search_set, kws),
        }
        warnings = []
        for key, label in (("source", "원문"), ("official", "공식")):
            for w in links[key].get("warnings") or []:
                warnings.append(f"{label} 링크: {w}")
        start = parse_date(raw.get("start_date"))
        if start and (start - today).days > 60:
            warnings.append(f"시작일이 {start.isoformat()}로 두 달 이상 남음")
        if not raw.get("period") and not end:
            warnings.append("기간 정보 없음 (상시 여부 직접 확인)")

        item = dict(raw)
        item["links"] = links
        item["warnings"] = warnings
        item["maps_url"] = maps_link(raw.get("place_name"), raw.get("address"))
        item["image"] = None
        for key in ("source", "official"):
            og = links[key].get("og_image")
            if not og:
                continue
            path = download_image(og, out_dir / "images", f"{len(items) + 1:02d}_{key}")
            if path:
                item["image"] = {
                    "path": path,
                    "url": og,
                    "domain": urlsplit(og).netloc,
                    "page": links[key]["url"],
                }
                break
        items.append(item)
    return items, excluded


def link_stats(items: list[dict]) -> dict:
    total = ok = 0
    for it in items:
        for link in it["links"].values():
            if link.get("url"):
                total += 1
                if link.get("ok") and link.get("in_search_results"):
                    ok += 1
    return {"total": total, "ok": ok}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="일본 정보 블로그 브리핑 생성기")
    ap.add_argument("field", help='분야 (예: "도쿄 팝업", "일본 향수")')
    ap.add_argument("--region", help="지역 (예: 시부야, 오사카)")
    ap.add_argument("--count", type=int, default=5, help="항목 수 (기본 5)")
    ap.add_argument("--no-open", action="store_true", help="완료 후 브라우저를 열지 않음")
    ap.add_argument("--out", default="briefs", help="출력 상위 폴더 (기본 briefs)")
    args = ap.parse_args(argv)

    load_dotenv(Path(__file__).with_name(".env"))
    load_dotenv()
    model = os.environ.get("CLAUDE_MODEL") or DEFAULT_MODEL
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ANTHROPIC_API_KEY가 없습니다. .env 파일에 넣어 주세요.", file=sys.stderr)
        return 2

    today = dt.datetime.now(JST).date()
    season = season_of(today.month)
    out_dir = Path(args.out) / f"{today.isoformat()}_{safe_dirname(args.field)}"
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"[1/3] 검색: {args.field} / {today} {season} / 모델 {model}")
    client = anthropic.Anthropic()
    try:
        text, search_urls, searches = run_research(
            client, model, build_user_prompt(args.field, args.region, args.count, today, season)
        )
    except anthropic.AuthenticationError:
        print("API 키 인증 실패. .env의 ANTHROPIC_API_KEY를 확인하세요.", file=sys.stderr)
        return 2
    except anthropic.NotFoundError:
        print(f"모델을 찾을 수 없습니다: {model} (CLAUDE_MODEL 확인)", file=sys.stderr)
        return 2
    except anthropic.RateLimitError:
        print("요청 한도 초과. 잠시 후 다시 실행하세요.", file=sys.stderr)
        return 1
    except anthropic.APIStatusError as e:
        print(f"API 오류 {e.status_code}: {e.message}", file=sys.stderr)
        return 1
    except anthropic.APIConnectionError as e:
        print(f"API 연결 실패: {e}", file=sys.stderr)
        return 1
    print(f"  · web_search {searches}회, 결과 URL {len(search_urls)}개")
    if not search_urls:
        print("  ! 검색 결과 URL을 하나도 받지 못했습니다. 모든 링크가 '검색 결과에 없음'으로 표시됩니다.", file=sys.stderr)

    raw_items = extract_json(text).get("items") or []
    print(f"[2/3] 링크·이미지 검증 ({len(raw_items)}개 후보)")
    items, excluded = process_items(raw_items, search_urls, today, out_dir)

    meta = {
        "field": args.field,
        "region": args.region,
        "date": today.isoformat(),
        "season": season,
        "model": model,
        "requested_count": args.count,
        "search_count": searches,
        "search_url_count": len(search_urls),
        "excluded": excluded,
        "link_stats": link_stats(items),
    }
    (out_dir / "data.json").write_text(
        json.dumps({"meta": meta, "items": items, "search_urls": sorted(search_urls)}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (out_dir / "브리핑.md").write_text(render_md(meta, items), encoding="utf-8")
    html_path = out_dir / "브리핑.html"
    html_path.write_text(render_html(meta, items), encoding="utf-8")

    st = meta["link_stats"]
    print(f"[3/3] 완료: {out_dir}")
    print(f"  · 항목 {len(items)}개 (제외 {len(excluded)}개), 링크 {st['ok']}/{st['total']} 정상")
    for it in items:
        mark = "⚠" if it["warnings"] else "✓"
        print(f"    {mark} {it.get('title_ko')}")
        for w in it["warnings"]:
            print(f"        - {w}")
    if not args.no_open:
        webbrowser.open(html_path.resolve().as_uri())
    return 0


if __name__ == "__main__":
    sys.exit(main())
