# -*- coding: utf-8 -*-
"""
구글 트렌드(대한민국) 인기 검색어를 모아 실시간 순위와 네이버 블로그용 '트렌드 정리' 글·사진을 만듭니다.
GitHub Actions 가 2시간마다 순위를, 하루 2번(오전·오후) 글을 만듭니다.

만드는 파일 (저장소 기준)
  data/rank.json               실시간 인기 검색어 순위 (2시간마다)
  data/rank_log.json           최근 순위 기록 24회분
  data/posts.json              글 목록 (최신순)
  data/posts/YYYYMMDD-am.json  회차별 블로그 글 (제목·본문·태그)
  data/img/YYYYMMDD-am.png     대표 카드 사진 / -rank.png 순위표 사진
  data/history.json            키워드 등장 기록 (새로 뜬 키워드 · 연속 화제 판단)
  index.html 이 이 파일들을 읽어 아이폰 대시보드로 보여 줍니다.

로컬 테스트:  python make_post.py --mode post --rss sample.xml --out ./out
"""
import argparse, datetime as dt, html, json, os, random, re, sys, time, urllib.request
import xml.etree.ElementTree as ET

RSS_URL = "https://trends.google.com/trending/rss?geo=KR"
NS = {"ht": "https://trends.google.com/trending/rss"}
KST = dt.timezone(dt.timedelta(hours=9))
TOP_N = int(os.environ.get("TOP_N", "10"))

# ---------------------------------------------------------------- 수집
def fetch_rss(path=None):
    if path:
        return open(path, "rb").read()
    last = None
    for i in range(4):
        try:
            req = urllib.request.Request(RSS_URL, headers={"User-Agent": "Mozilla/5.0 (trend-bot)", "Accept-Language": "ko-KR"})
            return urllib.request.urlopen(req, timeout=30).read()
        except Exception as e:  # 일시 오류는 재시도
            last = e
            time.sleep(5 * (i + 1))
    raise SystemExit(f"구글 트렌드 피드를 가져오지 못했습니다: {last}")

def traffic_num(t):
    """'500+', '2,000+', '1만+', '5천+' → 숫자"""
    t = (t or "").replace(",", "").replace("+", "").strip()
    m = re.match(r"([\d.]+)\s*(만|천|K|M)?", t, re.I)
    if not m:
        return 0
    v = float(m.group(1))
    unit = (m.group(2) or "").upper()
    return int(v * {"만": 10000, "천": 1000, "K": 1000, "M": 1000000}.get(unit, 1))

def traffic_label(t):
    n = traffic_num(t)
    if n >= 10000:
        return f"약 {n // 10000}만 회 이상"
    if n >= 1000:
        return f"약 {n:,}회 이상"
    return f"약 {n}회 이상" if n else "집계 중"

def parse(xml_bytes):
    root = ET.fromstring(xml_bytes)
    items = []
    for it in root.iter("item"):
        title = (it.findtext("title") or "").strip()
        if not title:
            continue
        news = []
        for n in it.findall("ht:news_item", NS):
            nt = html.unescape((n.findtext("ht:news_item_title", default="", namespaces=NS) or "").strip())
            nu = (n.findtext("ht:news_item_url", default="", namespaces=NS) or "").strip()
            ns_ = (n.findtext("ht:news_item_source", default="", namespaces=NS) or "").strip()
            if nt and nu.startswith("http"):
                news.append({"title": nt, "url": nu, "source": ns_})
        tr = it.findtext("ht:approx_traffic", default="", namespaces=NS) or ""
        items.append({"keyword": html.unescape(title), "traffic": tr, "n": traffic_num(tr),
                      "pub": it.findtext("pubDate") or "", "news": news[:3]})
    # 검색량 많은 순 → 같은 검색량이면 피드 순서(최신) 유지
    items = sorted(enumerate(items), key=lambda x: (-x[1]["n"], x[0]))
    out, seen = [], set()
    for _, x in items:
        k = x["keyword"].replace(" ", "").lower()
        if k in seen or len(k) < 2:  # 한 글자 검색어는 뜻이 모호해서 제외
            continue
        if not is_korean(x):          # 외국어 검색어 제외
            continue
        seen.add(k)
        out.append(x)
    return out[:TOP_N]

# 한국어 검색어만 남기기 — 구글 트렌드 한국 피드에 베트남어·태국어·러시아어·중국어 검색어가
# 섞여 들어오는 날이 있어서, 한글이 있거나(영문이면) 한국어 기사가 붙은 검색어만 씁니다.
HANGUL = re.compile("[\uac00-\ud7a3]")
LATIN_ONLY = re.compile(r"^[A-Za-z0-9 .,&+'\-]+$")
def is_korean(x):
    k = x["keyword"]
    if HANGUL.search(k):
        return True
    if LATIN_ONLY.match(k):
        return any(HANGUL.search(n.get("title", "")) for n in x.get("news", []))
    return False

# ---------------------------------------------------------------- 분류 (간단한 단어 사전)
CATS = [
    ("스포츠", "⚾", ["야구", "축구", "농구", "배구", "골프", "리그", "경기 결과", "경기에서", "선수", "감독", "시즌", "우승", "올림픽", "월드컵", "KBO", "FA", "구단", "득점", "홈런", "투수", "e스포츠", "LCK", "T1"]),
    ("연예·방송", "🎬", ["드라마", "배우", "가수", "아이돌", "컴백", "예능", "방송", "영화", "앨범", "뮤직", "팬미팅", "콘서트", "결혼", "열애", "출연", "시청률", "OST", "넷플릭스"]),
    ("경제·재테크", "💰", ["주가", "증시", "코스피", "코스닥", "금리", "환율", "부동산", "아파트", "공모", "상장", "주식", "비트코인", "실적", "매출", "투자", "청약", "물가", "관세", "은행"]),
    ("IT·테크", "💻", ["AI", "인공지능", "출시", "아이폰", "갤럭시", "앱", "업데이트", "반도체", "삼성전자", "애플", "구글", "카카오", "네이버", "게임", "챗GPT", "로봇", "전기차"]),
    ("날씨·생활", "🌤", ["날씨", "기온", "한파", "폭염", "태풍", "미세먼지", "눈", "비 소식", "지진", "수능", "연휴", "축제", "여행", "할인", "이벤트", "로또"]),
    ("사회·정치", "📰", ["정부", "대통령", "국회", "장관", "경찰", "검찰", "법원", "재판", "사고", "화재", "공단", "공사", "노동부", "고용", "교육", "선거", "정책", "부처", "의원", "국민의힘", "민주당", "여당", "야당", "정당", "당대표", "탄핵"]),
]
CAT_LINE = {
    "스포츠": ["경기 결과나 선수 소식에 관심이 몰렸어요.", "팬들의 관심이 뜨거운 스포츠 이슈예요.", "경기와 선수 관련 소식이 이어지고 있어요."],
    "연예·방송": ["방송·연예 소식으로 검색이 늘었어요.", "작품과 출연진 소식에 관심이 쏠렸어요.", "연예계 소식이 화제가 되고 있어요."],
    "경제·재테크": ["돈과 관련된 소식이라 많이들 찾아봤어요.", "시장 흐름과 관련해 관심이 커진 키워드예요.", "투자·생활 경제와 맞닿은 소식이에요."],
    "IT·테크": ["새 기술·제품 소식에 관심이 모였어요.", "IT 업계 소식으로 검색이 늘었어요.", "테크 분야에서 눈여겨볼 만한 이슈예요."],
    "날씨·생활": ["생활과 바로 맞닿은 소식이라 많이 찾았어요.", "일상에 영향을 주는 이슈예요.", "생활 정보로 챙겨 둘 만한 키워드예요."],
    "사회·정치": ["사회 이슈로 관심이 커진 키워드예요.", "여러 언론이 함께 다룬 사회 소식이에요.", "정책·사회 흐름과 관련된 이슈예요."],
    "기타": ["여러 사람이 함께 찾아본 키워드예요.", "갑자기 검색량이 늘어난 키워드예요.", "새롭게 관심을 끈 이슈예요."],
}

# 블로그 글에서 빼는 키워드 (사건·사고·재판·정치 → 명예훼손·초상권 위험)
RISK = ["재판", "혐의", "기소", "구속", "체포", "피의자", "피고", "고소", "고발", "검찰", "경찰", "수사", "법정", "판결", "선고",
        "사망", "숨져", "숨진", "사고로", "사고를", "사고가", "교통사고", "사망사고", "추락", "참사", "부상", "뺑소니", "음주", "폭행", "살인", "성범죄", "성폭", "마약", "도박", "학폭",
        "논란", "의혹", "사기", "횡령", "갑질", "자살", "극단", "실종", "화재", "폭발", "탄핵", "대통령", "국회", "의원", "선거",
        "여당", "야당", "국민의힘", "민주당", "정당", "후보", "장관", "총리"]

def is_safe(item):
    text = item["keyword"] + " " + " ".join(n["title"] for n in item["news"])
    return not any(w in text for w in RISK)

def classify(item):
    text = item["keyword"] + " " + " ".join(n["title"] for n in item["news"])
    best, score = ("기타", "🔎"), 0
    for name, emo, words in CATS:
        s = sum(text.count(w) for w in words)
        if s > score:
            best, score = (name, emo), s
    return best

# ---------------------------------------------------------------- 글 만들기
INTROS = [
    "{when} 기준으로 많이 검색된 키워드 {n}개를 정리했어요. 무슨 일이 있었는지 한 번에 훑어보세요.",
    "{when}, 사람들이 가장 많이 찾아본 검색어 {n}개예요. 키워드마다 관련 기사도 함께 모았어요.",
    "지금 어떤 이슈가 뜨거운지 궁금하셨죠? {when} 인기 검색어 {n}개를 간단히 정리했습니다.",
    "{when} 트렌드 정리입니다. 검색량이 많은 순서대로 {n}개 키워드를 살펴볼게요.",
]
OUTROS = [
    "오늘 트렌드는 여기까지예요. 다음 회차에서 새로운 키워드로 다시 정리해 드릴게요.",
    "관심 가는 키워드가 있었다면 관련 기사 링크로 자세한 내용을 확인해 보세요.",
    "검색어 흐름은 하루에도 여러 번 바뀌어요. 다음 정리도 기대해 주세요.",
]

def esc(s):
    return html.escape(s, quote=True)

def build(items, now, history):
    am = now.hour < 12
    ed = "am" if am else "pm"
    ed_ko = "오전" if am else "오후"
    date_ko = f"{now.month}월 {now.day}일"
    when = f"{date_ko} {ed_ko}"
    rnd = random.Random(now.strftime("%Y%m%d") + ed)
    pid = now.strftime("%Y%m%d") + "-" + ed

    for it in items:
        it["cat"], it["emo"] = classify(it)
        h = history.get(it["keyword"])
        it["new"] = not h
        it["seen"] = (h["seen"] if h else 0) + 1

    kws = [i["keyword"] for i in items]
    title = f"[{date_ko} {ed_ko} 트렌드] 지금 뜨는 검색어 {kws[0]}" + (f", {kws[1]}" if len(kws) > 1 else "") + (f" 외 {len(kws) - 2}개" if len(kws) > 2 else "")

    # 분류 집계
    cnt = {}
    for i in items:
        cnt[i["cat"]] = cnt.get(i["cat"], 0) + 1
    cat_sum = ", ".join(f"{k} {v}건" for k, v in sorted(cnt.items(), key=lambda x: -x[1]))
    new_k = [i["keyword"] for i in items if i["new"]]
    hot_k = [i for i in items if i["seen"] >= 3]

    H, T = [], []  # HTML / 일반 텍스트
    def p(h_, t_=None):
        H.append(f"<p>{h_}</p>")
        T.append(t_ if t_ is not None else re.sub(r"<[^>]+>", "", html.unescape(h_)))

    def mk(n, label):
        H.append(f'<p class="ph-mark">📷 사진 {n} · {label}</p>'); T.append(f"[📷 사진 {n} · {label}]")
    mk(1, "대표 이미지"); p("")
    p(esc(rnd.choice(INTROS).format(when=when, n=len(items))))
    p("")
    H.append("<h3>📌 한눈에 보기</h3>"); T.append("━━━━━━━━━━━━\n📌 한눈에 보기")
    for r, i in enumerate(items, 1):
        badge = " 🆕" if i["new"] else (f" 🔥 {i['seen']}회째 화제" if i["seen"] >= 3 else "")
        p(f"<b>{r}. {esc(i['keyword'])}</b> · {i['emo']} {esc(i['cat'])} · 검색 {esc(traffic_label(i['traffic']))}{esc(badge)}")
    p("")
    mk(2, "순위표"); p("")
    H.append("<h3>🔎 키워드별 정리</h3>"); T.append("━━━━━━━━━━━━\n🔎 키워드별 정리")
    for r, i in enumerate(items, 1):
        H.append(f"<h4>{r}. {esc(i['keyword'])}</h4>"); T.append(f"{r}. {i['keyword']}")
        line = rnd.choice(CAT_LINE.get(i["cat"], CAT_LINE["기타"]))
        extra = " 이번에 처음 순위에 올라왔어요." if i["new"] else (f" 최근 {i['seen']}번째 순위에 올라 꾸준히 관심을 받고 있어요." if i["seen"] >= 3 else "")
        p(esc(f"{i['emo']} {i['cat']} · 검색 {traffic_label(i['traffic'])}. {line}{extra}"))
        if i["news"]:
            p("관련 기사")
            H.append("<ul>")
            for n in i["news"]:
                src = f" ({esc(n['source'])})" if n["source"] else ""
                H.append(f'<li><a href="{esc(n["url"])}">{esc(n["title"])}</a>{src}</li>')
                T.append(f"- {n['title']}{' (' + n['source'] + ')' if n['source'] else ''} {n['url']}")
            H.append("</ul>")
        p("")
    H.append("<h3>📊 이번 회차 흐름</h3>"); T.append("━━━━━━━━━━━━\n📊 이번 회차 흐름")
    p(esc(f"분야별로 보면 {cat_sum}이 순위에 올랐어요."))
    if new_k:
        p(esc(f"새로 등장한 키워드: {', '.join(new_k[:6])}"))
    if hot_k:
        p(esc("계속 화제인 키워드: " + ", ".join(f"{i['keyword']}({i['seen']}회)" for i in hot_k[:5])))
    p("")
    mk(3, "분야별 흐름"); p("")
    p(esc(rnd.choice(OUTROS)))
    p("")
    stamp = now.strftime("%Y-%m-%d %H:%M")
    p(f"<i>{esc(f'※ 인기 검색어: Google 트렌드(대한민국) {stamp} 기준 · 기사 제목과 링크는 각 언론사 원문입니다.')}</i>")
    tags = ["트렌드", "실시간검색어", "오늘의이슈", "인기검색어"] + [re.sub(r"\s+", "", k)[:20] for k in kws[:6]]
    p(esc(" ".join("#" + t for t in tags)))

    return {"id": pid, "kind": "trend", "label": f"{ed_ko} 트렌드", "title": title, "html": "\n".join(H), "text": "\n".join(T), "tags": tags,
            "keywords": kws, "edition": ed, "created": now.isoformat(), "images": [],
            "items": [{k: i[k] for k in ("keyword", "traffic", "cat", "new", "seen", "news")} for i in items]}

# ---------------------------------------------------------------- 카드 이미지
FONT_PATHS = ["/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc", "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
              "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc", "C:/Windows/Fonts/malgunbd.ttf", "C:/Windows/Fonts/malgun.ttf"]

def card(post, path):
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("  (Pillow 없음 → 카드 이미지 생략)"); return False
    fp = next((f for f in FONT_PATHS if os.path.exists(f)), None)
    if not fp:
        print("  (한글 글꼴 없음 → 카드 이미지 생략)"); return False
    F = lambda s: ImageFont.truetype(fp, s, index=0) if fp.endswith(".ttc") else ImageFont.truetype(fp, s)
    W = 1080
    im = Image.new("RGB", (W, W), "#0f1729")
    d = ImageDraw.Draw(im)
    for y in range(W):  # 세로 그라데이션
        k = y / W
        d.line([(0, y), (W, y)], fill=(int(15 + 25 * k), int(23 + 10 * k), int(41 + 40 * k)))
    am = post["edition"] == "am"
    c = dt.datetime.fromisoformat(post["created"])
    d.rounded_rectangle([60, 60, 330, 120], 30, fill="#ff6b35" if am else "#7c5cff")
    d.text((195, 90), f"{'오전' if am else '오후'} 트렌드", font=F(34), fill="white", anchor="mm")
    d.text((60, 160), f"{c.month}월 {c.day}일", font=F(84), fill="white")
    d.text((60, 265), "지금 뜨는 검색어", font=F(56), fill="#c9d4ee")
    y = 370
    for r, it in enumerate(post["items"][:6], 1):
        kw = it["keyword"]
        while d.textlength(kw, font=F(50)) > 760 and len(kw) > 2:
            kw = kw[:-1]
        if kw != it["keyword"]:
            kw = kw[:-1] + "…"
        d.rounded_rectangle([60, y, W - 60, y + 92], 20, fill="#1c2a4a" if r > 1 else "#2b3f6e")
        d.text((110, y + 46), str(r), font=F(48), fill="#ffd166" if r <= 3 else "#8fa3c8", anchor="mm")
        d.text((170, y + 46), kw, font=F(46), fill="white", anchor="lm")
        if it.get("new"):
            d.text((W - 90, y + 46), "NEW", font=F(30), fill="#5cff9d", anchor="rm")
        y += 100
    d.text((W - 60, W - 40), "Google 트렌드(대한민국) 기준", font=F(26), fill="#7f8db0", anchor="rs")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    im.save(path, optimize=True)
    return True

# ---------------------------------------------------------------- 순위표 이미지 (TOP 10)
def rank_card(post, path):
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        return False
    fp = next((f for f in FONT_PATHS if os.path.exists(f)), None)
    if not fp:
        return False
    F = lambda s: ImageFont.truetype(fp, s, index=0) if fp.endswith(".ttc") else ImageFont.truetype(fp, s)
    W, H = 1080, 1350
    im = Image.new("RGB", (W, H), "#f6f7fb")
    d = ImageDraw.Draw(im)
    c = dt.datetime.fromisoformat(post["created"])
    d.rectangle([0, 0, W, 210], fill="#111a2e")
    d.text((60, 62), f"{c.month}월 {c.day}일 {'오전' if post['edition'] == 'am' else '오후'}", font=F(40), fill="#ffd166")
    d.text((60, 112), f"인기 검색어 TOP {min(10, len(post['items']))}", font=F(62), fill="white")
    y = 250
    for r, it in enumerate(post["items"][:10], 1):
        kw = it["keyword"]
        while d.textlength(kw, font=F(42)) > 560 and len(kw) > 2:
            kw = kw[:-1]
        if kw != it["keyword"]:
            kw = kw[:-1] + "…"
        d.rounded_rectangle([50, y, W - 50, y + 92], 18, fill="white", outline="#e3e7ef")
        d.text((105, y + 46), str(r), font=F(42), fill="#ff6b35" if r <= 3 else "#7a8499", anchor="mm")
        d.text((160, y + 46), kw, font=F(40), fill="#1d2330", anchor="lm")
        d.text((W - 80, y + 46), it.get("cat", ""), font=F(26), fill="#7a8499", anchor="rm")
        y += 104
    d.text((W - 60, H - 30), "Google 트렌드(대한민국) 기준", font=F(26), fill="#9aa3b5", anchor="rs")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    im.save(path, optimize=True)
    return True

# ---------------------------------------------------------------- 트렌드 이미지 3장 (디자인 엔진 → 안 되면 기존 카드)
def trend_images(post, out):
    pid, c = post["id"], dt.datetime.fromisoformat(post["created"])
    its = post["items"]
    cnt = {}
    for i in its:
        cnt[i["cat"]] = cnt.get(i["cat"], 0) + 1
    notes = []
    new = [i["keyword"] for i in its if i.get("new")]
    hot = [f"{i['keyword']}({i['seen']}회)" for i in its if i.get("seen", 0) >= 3]
    if new: notes.append("새로 등장: " + ", ".join(new[:5]))
    if hot: notes.append("계속 화제: " + ", ".join(hot[:4]))
    notes.append(f"총 {len(its)}개 키워드 · Google 트렌드(대한민국)")
    ed = "오전" if post["edition"] == "am" else "오후"
    jobs = [("trend_cover", {"badge": f"{ed} 트렌드", "date": f"{c.month}월 {c.day}일", "items": its}, "trend", f"data/img/{pid}-1.jpg"),
            ("table", {"title": f"{c.month}월 {c.day}일 {ed} 인기 검색어 TOP {len(its)}", "head": ["순위", "키워드", "분야", "검색량"],
                       "rows": [[str(r), i["keyword"], i["cat"], traffic_label(i["traffic"]).replace(" 이상", "+")] for r, i in enumerate(its, 1)]}, "trend", f"data/img/{pid}-2.jpg"),
            ("trend_dist", {"dist": sorted(cnt.items(), key=lambda x: -x[1]), "notes": notes}, "trend", f"data/img/{pid}-3.jpg")]
    try:
        import render
        done = render.render_all(jobs, out)
        if done:
            return done
    except Exception as ex:
        print(f"  디자인 이미지 실패 → 기본 카드 사용: {ex}")
    imgs = [f"data/img/{pid}.png", f"data/img/{pid}-rank.png"]
    ok = (card(post, os.path.join(out, imgs[0])), rank_card(post, os.path.join(out, imgs[1])))
    return [p for p, k in zip(imgs, ok) if k]

# ---------------------------------------------------------------- 실시간 순위 스냅샷 (2시간마다)
def snapshot(items, now, base):
    rp = os.path.join(base, "rank.json")
    prev = json.load(open(rp, encoding="utf-8")) if os.path.exists(rp) else {"items": []}
    prank = {x["keyword"]: x["rank"] for x in prev.get("items", [])}
    out = []
    for r, it in enumerate(items, 1):
        cat, emo = classify(it)
        pr = prank.get(it["keyword"])
        move = "new" if pr is None else ("up" if pr > r else "down" if pr < r else "same")
        out.append({"rank": r, "keyword": it["keyword"], "traffic": it["traffic"], "label": traffic_label(it["traffic"]),
                    "cat": cat, "emo": emo, "move": move, "delta": (pr - r) if pr else 0, "news": it["news"], "safe": is_safe(it)})
    snap = {"updated": now.isoformat(), "prev_updated": prev.get("updated", ""), "items": out}
    json.dump(snap, open(rp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    # 오늘 하루 순위 기록 (최근 24회)
    lp = os.path.join(base, "rank_log.json")
    lg = json.load(open(lp, encoding="utf-8")) if os.path.exists(lp) else []
    lg.append({"t": now.strftime("%m-%d %H:%M"), "k": [x["keyword"] for x in out]})
    json.dump(lg[-24:], open(lp, "w", encoding="utf-8"), ensure_ascii=False)
    # 날짜별 순위 기록 — 지우지 않고 계속 쌓음
    hd = os.path.join(base, "rank_history")
    os.makedirs(hd, exist_ok=True)
    hp = os.path.join(hd, now.strftime("%Y-%m-%d") + ".json")
    hist = json.load(open(hp, encoding="utf-8")) if os.path.exists(hp) else []
    hist.append({"t": now.strftime("%Y-%m-%d %H:%M"), "k": [x["keyword"] for x in out], "n": [x["traffic"] for x in out]})
    json.dump(hist, open(hp, "w", encoding="utf-8"), ensure_ascii=False)
    print(f"순위 갱신: {', '.join(x['keyword'] for x in out[:5])} …")
    return out

# ---------------------------------------------------------------- 실행
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rss", help="테스트용 RSS 파일")
    ap.add_argument("--out", default=".", help="저장소 폴더")
    ap.add_argument("--mode", default=os.environ.get("MODE", "rank"), choices=["rank", "hot", "post", "theme", "deep"],
                    help="rank = 순위만 · hot = 순위 + 화제 글·인스타·스레드(매시간) · post = 트렌드 글 · deep = 심층 글 + 인스타·스레드")
    ap.add_argument("--edition", default=os.environ.get("EDITION", "auto"), choices=["auto", "am", "pm"])
    a = ap.parse_args()

    now = dt.datetime.now(KST).replace(second=0, microsecond=0)
    if a.edition == "am" and now.hour >= 12:
        now = now.replace(hour=11, minute=0)
    if a.edition == "pm" and now.hour < 12:
        now = now.replace(hour=17, minute=0)

    base = os.path.join(a.out, "data")
    os.makedirs(os.path.join(base, "posts"), exist_ok=True)
    prune(a.out, now)

    if a.mode == "deep":
        import deep_post, social
        post = deep_post.build(now, base, a.out)
        art = post.pop("_article")
        save_post(post, base)
        ig, th = social.from_deep(post, art)
        social.save(base, "insta", ig); social.save(base, "threads", th)
        print("인스타·스레드 콘텐츠도 만들었습니다.")
        return

    if a.mode == "theme":
        import theme_post
        save_post(theme_post.build(now, base, a.out, FONT_PATHS), base)
        return

    items = parse(fetch_rss(a.rss))
    if len(items) < 3:
        raise SystemExit(f"인기 검색어가 {len(items)}개뿐이라 이번 회차는 건너뜁니다.")
    snap = snapshot(items, now, base)
    if a.mode == "rank":
        return
    if a.mode == "hot":
        import hot_post, social
        post = hot_post.build(items, snap, now, base, a.out, is_safe, classify, traffic_label)
        if post:
            save_post(post, base)
            ig, th = social.from_hot(post)
            social.save(base, "insta", ig); social.save(base, "threads", th)
            print("인스타·스레드 콘텐츠도 만들었습니다.")
        return

    safe = [i for i in items if is_safe(i)]
    dropped = [i["keyword"] for i in items if not is_safe(i)]
    if dropped:
        print(f"블로그 글에서 뺀 키워드 (사건·사고·정치 등): {', '.join(dropped)}")
    if len(safe) < 3:
        print(f"안전한 키워드가 {len(safe)}개뿐이라 이번 트렌드 글은 건너뜁니다.")
        return

    hp = os.path.join(base, "history.json")
    history = json.load(open(hp, encoding="utf-8")) if os.path.exists(hp) else {}
    post = build(safe, now, history)
    post["images"] = trend_images(post, a.out)

    for i in safe:
        h = history.setdefault(i["keyword"], {"first": post["id"], "seen": 0, "last": ""})
        if h["last"] != post["id"]:
            h["seen"] += 1
            h["last"] = post["id"]
    cutoff = (now - dt.timedelta(days=30)).strftime("%Y%m%d")
    history = {k: v for k, v in history.items() if v["last"][:8] >= cutoff}
    json.dump(history, open(hp, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    save_post(post, base)

def save_post(post, base):
    json.dump(post, open(os.path.join(base, "posts", post["id"] + ".json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    lst_p = os.path.join(base, "posts.json")
    lst = json.load(open(lst_p, encoding="utf-8")) if os.path.exists(lst_p) else []
    lst = [x for x in lst if x["id"] != post["id"]]
    lst.append({"id": post["id"], "kind": post.get("kind", "trend"), "label": post.get("label", ""), "title": post["title"],
                "created": post["created"], "thumb": (post["images"] or [""])[0]})
    lst.sort(key=lambda x: x["created"], reverse=True)
    json.dump(lst[:300], open(lst_p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    # 월별 보관함 — 모든 글 목록을 지우지 않고 계속 쌓음
    ad = os.path.join(base, "archive")
    os.makedirs(ad, exist_ok=True)
    mon = post["created"][:7]
    ap_ = os.path.join(ad, mon + ".json")
    arc = json.load(open(ap_, encoding="utf-8")) if os.path.exists(ap_) else []
    arc = [x for x in arc if x["id"] != post["id"]] + [lst[[x["id"] for x in lst].index(post["id"])]]
    json.dump(arc, open(ap_, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    ip = os.path.join(ad, "index.json")
    idx = json.load(open(ip, encoding="utf-8")) if os.path.exists(ip) else []
    idx = sorted(set(idx) | {mon}, reverse=True)
    json.dump(idx, open(ip, "w", encoding="utf-8"))
    print(f"글 완료: {post['id']} · {post['title']} · 사진 {len(post['images'])}장")

def prune(out, now, days=150):
    """GitHub Pages 용량(1GB) 한도를 넘지 않게 150일 지난 사진만 저장소에서 지움.
    글·순위·인스타·스레드 기록은 모두 남고, 사진 원본은 PC의 '전체자료' 폴더에 계속 쌓입니다."""
    d = os.path.join(out, "data", "img")
    if not os.path.isdir(d):
        return
    cut = (now - dt.timedelta(days=days)).strftime("%Y%m%d")
    for f in os.listdir(d):
        if f[:8].isdigit() and f[:8] < cut:
            os.remove(os.path.join(d, f))

if __name__ == "__main__":
    main()
