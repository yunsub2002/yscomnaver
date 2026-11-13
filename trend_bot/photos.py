# -*- coding: utf-8 -*-
"""
블로그용 사진 가져오기 (저작권 걱정 없는 출처만)
  1순위 Pixabay  : 무료 API 키(PIXABAY_KEY) 필요 · 상업적 이용 가능 · 출처 표기 의무 없음 · 내려받아 사용 허용
  2순위 Openverse: 키 없음 · CC0/퍼블릭 도메인 사진만 검색
같은 사진이 반복되지 않도록 data/photo_used.json 에 쓴 사진을 기록합니다.
"""
import io, json, os, random, urllib.parse, urllib.request

UA = {"User-Agent": "Mozilla/5.0 (trend-blog-bot; +https://github.com/yunsub2002/yscomnaver)"}

def _get(url, timeout=30):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout).read()

def _pixabay(q, key):
    u = "https://pixabay.com/api/?" + urllib.parse.urlencode({
        "key": key, "q": q, "image_type": "photo", "orientation": "horizontal", "safesearch": "true",
        "per_page": 40, "min_width": 1200, "order": "popular"})
    hits = json.loads(_get(u)).get("hits", [])
    return [{"id": f"px{h['id']}", "url": h["largeImageURL"], "credit": f"Pixabay · {h.get('user', '')}",
             "page": h.get("pageURL", "")} for h in hits]

def _openverse(q):
    u = "https://api.openverse.org/v1/images/?" + urllib.parse.urlencode({
        "q": q, "license": "cc0,pdm", "page_size": 20, "mature": "false", "aspect_ratio": "wide"})
    res = json.loads(_get(u)).get("results", [])
    out = []
    for r in res:
        if (r.get("width") or 0) < 1000:
            continue
        lic = "퍼블릭 도메인" if r.get("license") == "pdm" else "CC0"
        out.append({"id": f"ov{r['id']}", "url": r["url"], "credit": f"{lic} · {r.get('creator') or '작자 미상'}",
                    "page": r.get("foreign_landing_url", "")})
    return out

def find(queries, n, used, seed):
    """queries 순서대로 검색해서 아직 안 쓴 사진 n장 고르기"""
    key = os.environ.get("PIXABAY_KEY", "").strip()
    rnd = random.Random(seed)
    picked = []
    for q in queries * 2:
        if len(picked) >= n:
            break
        cands = []
        for src in (["pixabay"] if key else []) + ["openverse"]:
            try:
                cands = _pixabay(q, key) if src == "pixabay" else _openverse(q)
            except Exception as e:
                print(f"  사진 검색 실패 ({src}, {q}): {e}")
                cands = []
            cands = [c for c in cands if c["id"] not in used and c["id"] not in {p["id"] for p in picked}]
            if cands:
                break
        if cands:
            top = cands[: max(8, len(cands) // 2)]  # 인기 상위 절반 안에서 무작위
            picked.append(rnd.choice(top))
    return picked

def download(photo, path, width=1080):
    """사진을 내려받아 가로 1080px JPEG 로 저장 (Pixabay 안내대로 내 저장소에 보관)"""
    from PIL import Image
    im = Image.open(io.BytesIO(_get(photo["url"], 60))).convert("RGB")
    if im.width > width:
        im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    im.save(path, "JPEG", quality=84, optimize=True, progressive=True)
    return im
