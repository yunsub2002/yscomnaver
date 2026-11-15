# -*- coding: utf-8 -*-
"""
👧 키즈 실시간 — 아이·초등학생과 갈 만한 축제 · 행사 · 가볼만한곳 · 키즈카페(공공형 포함) · 맛집 · 공연 소식을
매시간 모아 대시보드 '키즈' 탭에 보여 주고, 하루 한 번 '키즈 나들이 블로거' 말투의 주간 정리 글을 만듭니다.

수집 출처
  1) 한국관광공사 TourAPI (국문 관광정보 KorService2 · searchFestival2)
     → 이번 주 진행 중인 전국 축제·행사 (무료 키 TOUR_API_KEY 필요, 없으면 건너뜀)
  2) Google 뉴스 RSS 검색 (키 없음) → 최근 7일 어린이 행사·키즈카페·나들이·외식 기사 제목과 링크

만드는 파일
  data/kids.json                 실시간 피드 (매시간)
  data/kids_archive/YYYY-MM.json 월별 기록 (지우지 않고 계속 쌓음)
  data/posts/YYYYMMDD-kids.json  주간 키즈 나들이 글 (하루 1편)

글은 '직접 다녀온 후기'처럼 꾸며 쓰지 않습니다. 공식 정보·기사·일반 팁만 정리하고,
실제 후기는 대시보드의 '후기 쓰기'에 내가 다녀온 내용을 넣어 만듭니다.
"""
import datetime as dt, hashlib, html, json, os, random, re, time, urllib.parse, urllib.request
import xml.etree.ElementTree as ET

KST = dt.timezone(dt.timedelta(hours=9))
UA = {"User-Agent": "Mozilla/5.0 (kids-blog-bot)", "Accept-Language": "ko-KR"}
WD = "월화수목금토일"

# ---------------------------------------------------------------- 분야
CATS = [
    {"key": "festival", "name": "축제·행사", "emo": "🎪"},
    {"key": "place", "name": "가볼만한곳", "emo": "🗺️"},
    {"key": "kidscafe", "name": "키즈카페", "emo": "🧸"},
    {"key": "food", "name": "맛집·외식", "emo": "🍽️"},
    {"key": "show", "name": "공연·전시", "emo": "🎭"},
    {"key": "trend", "name": "요즘 유행", "emo": "🔥"},
]
CAT = {c["key"]: c for c in CATS}

def queries(now):
    m = now.month
    q = {
        "festival": ["어린이 축제", "가족 축제 주말", "어린이 체험 행사", f"{m}월 어린이 행사"],
        "place": ["아이와 가볼만한곳", "아이랑 주말 나들이", "가족 나들이 명소 개장"],
        "kidscafe": ["공공형 키즈카페", "키즈카페 개관", "실내 놀이터 개장", "어린이 놀이시설 개장"],
        "food": ["아이와 맛집", "키즈 메뉴 출시", "가족 외식 맛집"],
        "show": ["어린이 공연", "어린이 뮤지컬", "어린이 전시 체험"],
        "trend": ["초등학생 유행", "아이들 사이 인기", "어린이 열풍", "초등학생 인기 간식", "어린이 인기 장난감", "키즈 품절 대란", "초등학생 사이 화제", "아이들 오픈런",
                  "잘파세대 유행", "알파세대 인기", "초등생 신조어", "어린이 인기 캐릭터", "학부모 사이 화제", "초등학생 사이 유행 간식"],
    }
    q["festival"] += ["이번 주말 축제", "축제 개막 가족", f"{m}월 축제 개최"]
    if m in (11, 12, 1, 2):
        q["festival"] += ["빛축제 가족", "크리스마스 어린이 행사"]
        q["place"] += ["눈썰매장 개장", "겨울방학 어린이 체험"]
    elif m in (3, 4, 5):
        q["festival"] += ["어린이날 행사" if m in (4, 5) else "봄 축제 가족", "봄꽃 축제 아이"]
        q["place"] += ["봄나들이 아이와"]
    elif m in (6, 7, 8):
        q["festival"] += ["여름 축제 가족"]
        q["place"] += ["물놀이장 개장", "여름방학 어린이 체험"]
    else:
        q["festival"] += ["가을 축제 가족", "핼러윈 어린이 행사" if m == 10 else "가을 체험 행사 어린이"]
        q["place"] += ["가을 나들이 아이와"]
    return q

# 아이·가족과 관련 있는 기사만 남기기 (아이돌·아이폰 등은 제외)
KID_RE = re.compile(r"아이(?!돌|폰|디|템|유|패드|콘|언|큐|오닉|브|젠|러브|파크|슬란드|비)|어린이|가족|키즈|유아|초등|아동|자녀|엄마|아빠|부모|놀이|눈썰매|동물원|과학관|체험|어린이집|방학")
# 아이 글에 어울리지 않는 기사 (사건·사고·학대·정치 등)
RISK = ["학대", "사망", "숨져", "숨진", "사고", "실종", "유괴", "추락", "폭행", "성범죄", "성폭", "추행", "살인", "흉기", "체포", "구속", "기소", "재판", "혐의",
        "수사", "경찰", "검찰", "고소", "식중독", "감염", "확진", "부상", "화재", "폭발", "익사", "논란", "의혹", "갑질", "횡령", "사기", "자살", "극단",
        "노키즈", "문 닫", "격차", "성료", "마무리", "폐막", "막 내려", "막내려", "성황리", "끝났", "마쳐", "마쳤", "日", "美", "中 ", "일본", "미국", "중국", "영화제", "싱가포르", "영국", "호주", "캐나다", "아이슬란드", "독일", "프랑스", "베트남", "해외", "적발", "행감", "위원장", "도지사", "군수", "구청장", "의장", "조롱", "목격담", "탄핵", "선거", "후보", "국회", "의원", "대통령", "장관", "정당", "민주당", "국민의힘", "파업", "폐업", "폐원", "중단", "취소", "연기돼"]
ADULT = ["술", "막걸리", "와인", "맥주", "소주", "전통주", "칵테일", "위스키", "주류"]
FEST_KID = ["어린이", "가족", "키즈", "아이", "체험", "동물", "과학", "빛", "루미나", "크리스마스", "산타", "눈", "썰매", "얼음", "놀이", "장난감", "그림",
            "동화", "인형", "공룡", "로봇", "레고", "캐릭터", "별", "마술", "버블", "딸기", "고구마", "귤", "감귤", "사과", "곤충", "나비", "뮤지컬", "인형극", "벌룬", "열기구", "트리"]

REGIONS = ["서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종", "경기", "강원", "충북", "충남", "전북", "전남", "경북", "경남", "제주",
           "수원", "성남", "고양", "용인", "부천", "안산", "안양", "남양주", "화성", "평택", "의정부", "시흥", "파주", "김포", "광명", "하남", "구리", "오산", "이천",
           "양평", "가평", "포천", "춘천", "원주", "강릉", "속초", "평창", "청주", "충주", "천안", "아산", "공주", "전주", "군산", "익산", "포항", "경주", "안동",
           "구미", "창원", "김해", "진주", "통영", "거제", "양산", "여수", "순천", "목포", "담양", "서귀포", "송도", "일산", "분당", "판교", "동탄"]
ADDR_SHORT = {"서울특별시": "서울", "부산광역시": "부산", "대구광역시": "대구", "인천광역시": "인천", "광주광역시": "광주", "대전광역시": "대전", "울산광역시": "울산",
              "세종특별자치시": "세종", "경기도": "경기", "강원특별자치도": "강원", "강원도": "강원", "충청북도": "충북", "충청남도": "충남", "전북특별자치도": "전북",
              "전라북도": "전북", "전라남도": "전남", "경상북도": "경북", "경상남도": "경남", "제주특별자치도": "제주"}

def esc(s):
    return html.escape(str(s), quote=True)

def _load(p, d):
    try:
        return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else d
    except Exception:
        return d

def _get(url, timeout=25):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout).read()

def region_of(text):
    for r in REGIONS:
        if r in text:
            return r
    return ""

def period_of(text):
    m = re.search(r"(\d{1,2})월\s?(\d{1,2})일?\s?(?:부터)?\s?[~∼\-–]\s?(?:(\d{1,2})월\s?)?(\d{1,2})일", text)
    if m:
        a, b, c, d = m.groups()
        return f"{a}/{b}~{(c or a)}/{d}"
    m = re.search(r"(\d{1,2})\s?[~∼\-–]\s?(\d{1,2})일", text)
    if m:
        return f"{m.group(1)}~{m.group(2)}일"
    m = re.search(r"(\d{1,2})월\s?(\d{1,2})일까지", text)
    if m:
        return f"~{m.group(1)}/{m.group(2)}"
    m = re.search(r"(\d{1,2})일까지", text)
    if m:
        return f"~{m.group(1)}일"
    return ""

def bigrams(s):
    s = re.sub(r"[^\w가-힣]", "", s)
    return {s[i:i + 2] for i in range(len(s) - 1)}

# ---------------------------------------------------------------- 1) 뉴스
def news_feed(now):
    out, cut = [], now - dt.timedelta(days=7)
    for cat, qs in queries(now).items():
        for q in qs:
            url = "https://news.google.com/rss/search?" + urllib.parse.urlencode({"q": f"{q} when:7d", "hl": "ko", "gl": "KR", "ceid": "KR:ko"})
            try:
                root = ET.fromstring(_get(url))
            except Exception as e:
                print(f"  뉴스 검색 실패 ({q}): {e}")
                continue
            for it in root.iter("item"):
                t = html.unescape((it.findtext("title") or "").strip())
                src = (it.findtext("source") or "").strip()
                if src and t.endswith(" - " + src):
                    t = t[: -len(src) - 3].strip()
                link = (it.findtext("link") or "").strip()
                try:
                    pub = dt.datetime.strptime(it.findtext("pubDate") or "", "%a, %d %b %Y %H:%M:%S %Z").replace(tzinfo=dt.timezone.utc).astimezone(KST)
                except Exception:
                    pub = now
                if not t or not link.startswith("http") or pub < cut:
                    continue
                if any(w in t for w in RISK) or not (KID_RE.search(t) or (cat == "trend" and re.search(r"잘파|알파세대|급식|학생|초등", t))):
                    continue
                if cat == "food" and not re.search(r"맛집|메뉴|식당|외식|레스토랑|카페|빵|디저트|먹거리|급식|간식|뷔페", t):
                    continue
                if cat in ("festival", "show", "place") and PAST.search(t):
                    continue
                if cat == "trend" and not re.search(r"인기|유행|열풍|품절|대란|화제|난리|오픈런|핫한|입소문|돌풍|신드롬|불티|완판", t):
                    continue
                if cat == "kidscafe" and not re.search(r"키즈카페|놀이터|놀이시설|놀이공간|놀이센터|실내놀이|키즈존|키즈파크|장난감", t):
                    continue
                age_h = max(0, (now - pub).total_seconds() / 3600)
                if src.startswith("http"):
                    src = re.sub(r"^https?://(www\.)?|/.*$", "", src)
                if re.match(r"^(www\.|m\.)", src):
                    src = re.sub(r"^(www\.|m\.)", "", src)
                soon = 3 if re.search(r"개최|열린다|열려|개장|문 연다|운영|진행|개막|모집|오픈|선보|출시|공연한다|초청|접수", t) else 0
                score = soon + len(KID_RE.findall(t)) * 2 + (3 if period_of(t) else 0) + (2 if region_of(t) else 0) - age_h / 24
                out.append({"cat": cat, "title": t, "source": src, "url": link, "pub": pub.isoformat(), "region": region_of(t),
                            "period": period_of(t), "score": round(score, 2)})
            time.sleep(0.3)
    # 중복 기사 합치기 (제목이 거의 같은 것)
    out.sort(key=lambda x: -x["score"])
    kept, grams = [], []
    for x in out:
        g = bigrams(x["title"])
        if any(len(g & h) / max(1, min(len(g), len(h))) > 0.5 for h in grams):
            continue
        grams.append(g)
        x["id"] = "n" + hashlib.md5(re.sub(r"\W", "", x["title"]).encode()).hexdigest()[:10]
        kept.append(x)
    # 분야별 최대 20개, 전체는 최신 + 점수 순
    per, res = {}, []
    for x in kept:
        if per.get(x["cat"], 0) < 20:
            per[x["cat"]] = per.get(x["cat"], 0) + 1
            res.append(x)
    res.sort(key=lambda x: x["pub"], reverse=True)
    return res, kept

# ---------------------------------------------------------------- 1-2) 기사에서 축제·행사 이름 뽑기 (키 없이)
QUOTE_RE = re.compile(r"[‘'\"“「『《<]([^’'\"”」』》>]{2,30})[’'\"”」』》>]")
EVENT_RE = re.compile(r"축제|페스티벌|마켓|박람회|페어|축전|한마당|체험전|특별전|기획전|전시|뮤지컬|빛|놀이터|캠프|대축제|썰매|트리|행사")
NAME_RE = re.compile(r"((?:제\d+회\s?)?(?:20\d\d\s?)?[가-힣A-Za-z0-9·]{2,14}\s?(?:빛축제|대축제|축제|페스티벌|크리스마스\s?마켓|마켓|박람회|키즈페어|페어|축전|한마당|체험전|특별전))")
PAST = re.compile(r"성황|호응|환호|열렸|펼쳐졌|가졌|진행했|개최했|참여했|성료|명 참여|명이 참여|명 참가|큰 인기 속|북적였|즐겼")
GENERIC_RE = re.compile(r"^(주민|가족|어린이|마을|전통문화|전통|지역|주말|육아|걷기|마을교육|문화|체험|과학|겨울|가을|봄|여름|세대|화합|행복|나눔|\d+)+(축제|한마당|대축제|페스티벌|마켓|체험전)$")
NOT_KID = ["김치", "김장", "수산물", "젓갈", "한우", "초장", "막걸리", "와인", "맥주", "불꽃", "도자기", "인삼", "곶감", "굴", "대게", "과메기", "음식문화"]
TREND_STOP = {"점점", "큰", "최고", "다시", "여전히", "급", "사이", "아이들", "초등학생", "초등생", "어린이", "아이", "요즘", "최근", "역대급", "폭발적", "꾸준한", "새로운", "학부모", "엄마들"}
GENERIC = {"축제", "가족축제", "어린이축제", "주말축제", "지역축제", "겨울축제", "가을축제", "봄축제", "여름축제", "체험행사", "행사", "전시", "특별전", "마켓", "페어", "박람회", "한마당"}

def norm(n):
    return re.sub(r"제\d+회|20\d\d|\s|[·\-]", "", n)

def event_name(t, cat):
    for m in QUOTE_RE.finditer(t):
        n = m.group(1).strip()
        if EVENT_RE.search(n) and norm(n) not in GENERIC and not GENERIC_RE.match(norm(n)) and not re.search(r"vs|이겨|\?|!|…", n) and not any(w in n for w in RISK):
            return n
    m = NAME_RE.search(t)
    if m:
        n = m.group(1).strip()
        if norm(n) not in GENERIC and not GENERIC_RE.match(norm(n)) and len(norm(n)) >= 4:
            return n
    return ""

def period_end(period, now):
    """'11/1~11/30', '~11/30', '~20일' → 끝나는 날짜 (모르면 None)"""
    m = re.search(r"(\d{1,2})/(\d{1,2})$", period or "")
    if m:
        mo, d = int(m.group(1)), int(m.group(2))
        y = now.year + (1 if mo < now.month - 6 else 0) - (1 if mo > now.month + 6 else 0)
        try:
            return dt.date(y, mo, d)
        except ValueError:
            return None
    m = re.search(r"~(\d{1,2})일$", period or "")
    if m:
        try:
            return dt.date(now.year, now.month, int(m.group(1)))
        except ValueError:
            return None
    return None

def news_festivals(arts, now):
    groups = {}
    for x in arts:
        if x["cat"] not in ("festival", "show", "place", "kidscafe"):
            continue
        n = event_name(x["title"], x["cat"])
        if not n:
            continue
        g = groups.setdefault(norm(n), {"name": n, "arts": []})
        g["arts"].append(x)
    out = []
    for k, g in groups.items():
        arts_ = sorted(g["arts"], key=lambda a: a["pub"], reverse=True)
        per = next((a["period"] for a in arts_ if a.get("period")), "")
        end = period_end(per, now)
        if end and end < now.date():
            continue
        reg = next((a["region"] for a in arts_ if a.get("region")), "")
        txt = g["name"] + " " + " ".join(a["title"] for a in arts_)
        kid = sum(w in g["name"] for w in FEST_KID) + (1 if re.search(r"어린이|가족|키즈|아이", txt) else 0) - 3 * sum(w in g["name"] for w in ADULT + NOT_KID)
        b = arts_[0]
        out.append({"id": "e" + hashlib.md5(k.encode()).hexdigest()[:10], "title": g["name"], "period": per or "기사에서 확인",
                    "addr": reg, "region": reg, "city": "", "img": "", "tel": "", "kid": kid, "count": len(arts_),
                    "status": f"기사 {len(arts_)}건", "tip": fest_tip(txt), "map": "https://map.naver.com/p/search/" + urllib.parse.quote(g["name"]),
                    "url": b["url"], "source": b["source"], "src_title": b["title"], "pub": b["pub"], "from": "news",
                    "arts": [{k2: a[k2] for k2 in ("title", "url", "source", "pub")} for a in arts_[:3]]})
    out = [x for x in out if x["kid"] > 0]
    out.sort(key=lambda x: (-x["kid"], -x["count"], x["pub"]))
    return out[:30]

# ---------------------------------------------------------------- 1-3) 요즘 아이들 사이 유행 (여러 기사에 나온 주제)
def trends(arts, fests, now):
    topics = {}
    for x in arts:
        if x["cat"] != "trend":
            continue
        names = [m.group(1).strip() for m in QUOTE_RE.finditer(x["title"])]
        names = [n for n in names if 2 <= len(norm(n)) <= 14 and not re.search(r"[?!…]", n) and not any(w in n for w in RISK)]
        if not names:
            m = [z for z in re.findall(r"([가-힣A-Za-z0-9]{2,12})\s?(?:이|가)?\s?(?:인기|열풍|유행|품절|대란|오픈런|돌풍|신드롬|완판|불티)", x["title"]) if z not in TREND_STOP]
            names = m[:1]
        if not names:
            continue
        n = names[0]
        t = topics.setdefault(norm(n), {"name": n, "arts": []})
        t["arts"].append(x)
    # 이름이 다른 기사 제목에도 나오면 함께 묶기
    for k, t in topics.items():
        for x in arts:
            if x not in t["arts"] and len(k) >= 3 and k in re.sub(r"\s", "", x["title"]):
                t["arts"].append(x)
    out = []
    for k, t in topics.items():
        a = sorted(t["arts"], key=lambda z: z["pub"], reverse=True)
        age = (now - dt.datetime.fromisoformat(a[0]["pub"])).total_seconds() / 3600
        out.append({"id": "t" + hashlib.md5(k.encode()).hexdigest()[:10], "kind": "trend", "name": t["name"], "count": len(a),
                    "score": round(8 + len(a) * 4 - age / 24, 2), "pub": a[0]["pub"], "region": next((z["region"] for z in a if z.get("region")), ""),
                    "arts": [{k2: z[k2] for k2 in ("title", "url", "source", "pub")} for z in a[:4]]})
    # 같은 기사 묶음이 겹치는 주제는 기사 많은 쪽만 남기기
    out.sort(key=lambda x: -x["count"])
    ded, seen_u = [], set()
    for x in out:
        us = {a["url"] for a in x["arts"]}
        if us and us <= seen_u:
            continue
        seen_u |= us
        ded.append(x)
    out = ded
    # 기사가 여러 건 나온 축제·행사도 '화제'로
    for f in fests:
        if (f.get("count", 1) >= 2 and f.get("kid", 0) >= 1) or f.get("kid", 0) >= 3:
            out.append({"id": "t" + f["id"], "kind": "fest", "name": f["title"], "count": f.get("count", 1), "pub": f.get("pub", now.isoformat()),
                        "score": round(f.get("count", 1) * 2.5 + max(0, f.get("kid", 0)), 2), "region": f.get("region", ""), "period": f.get("period", ""),
                        "tip": f.get("tip", ""), "map": f.get("map", ""), "arts": f.get("arts") or ([{"title": f.get("src_title", ""), "url": f.get("url", ""), "source": f.get("source", ""), "pub": f.get("pub", "")}] if f.get("url") else [])})
    out.sort(key=lambda x: -x["score"])
    return out[:15]

# ---------------------------------------------------------------- 1-4) 네이버 블로그 반응 (선택 · 네이버 검색 API 무료 키)
def naver_buzz(items, now):
    cid, sec = os.environ.get("NAVER_CLIENT_ID", "").strip(), os.environ.get("NAVER_CLIENT_SECRET", "").strip()
    if not (cid and sec):
        return False
    for it in items[:15]:
        q = it.get("name") or it.get("title")
        try:
            req = urllib.request.Request("https://openapi.naver.com/v1/search/blog.json?" + urllib.parse.urlencode({"query": q, "display": 5, "sort": "date"}),
                                         headers={"X-Naver-Client-Id": cid, "X-Naver-Client-Secret": sec})
            j = json.loads(urllib.request.urlopen(req, timeout=15).read())
        except Exception as e:
            print(f"  네이버 검색 실패 ({q}): {e}")
            continue
        blogs = []
        for b in j.get("items", []):
            pd = b.get("postdate", "")
            blogs.append({"title": html.unescape(re.sub(r"<[^>]+>", "", b.get("title", ""))), "url": b.get("link", ""),
                          "by": b.get("bloggername", ""), "date": f"{pd[4:6]}/{pd[6:8]}" if len(pd) == 8 else ""})
        recent = sum(1 for b in j.get("items", []) if b.get("postdate", "") >= (now - dt.timedelta(days=7)).strftime("%Y%m%d"))
        it["blog_total"], it["blogs"], it["blog_recent"] = int(j.get("total") or 0), blogs[:3], recent
        if "score" in it:
            it["score"] = round(it["score"] + recent * 1.5 + (len(str(it["blog_total"])) - 1) * 0.5, 2)
        time.sleep(0.15)
    if items and "score" in items[0]:
        items.sort(key=lambda x: -x["score"])
    return True

# ---------------------------------------------------------------- 2) 관광공사 축제
def fest_tip(t):
    if re.search(r"빛|루미나|야간|별빛|트리|일루미", t):
        return "해 진 뒤가 가장 예뻐요. 저녁엔 기온이 뚝 떨어지니 겉옷·핫팩을 챙기세요."
    if re.search(r"눈|썰매|얼음|빙어|스키", t):
        return "방수 장갑과 여벌 양말·옷은 필수예요. 젖으면 금방 추워져요."
    if re.search(r"크리스마스|산타", t):
        return "포토존이 많아 사진 남기기 좋아요. 주말 오후엔 붐비니 이른 시간이 여유로워요."
    if re.search(r"체험|만들기|공방|농장|따기|캐기", t):
        return "체험 프로그램은 조기 마감되는 경우가 많아요. 사전 예약·현장 접수 시간을 꼭 확인하세요."
    if re.search(r"동물|곤충|나비|공룡", t):
        return "아이들 반응이 제일 좋은 테마예요. 손 씻을 물티슈·손소독제를 챙기세요."
    if re.search(r"딸기|귤|감귤|고구마|사과|먹거리|음식|맛", t):
        return "먹거리 부스가 많은 편이에요. 아이 간식은 따로 챙기고, 결제 방법도 미리 확인하세요."
    if re.search(r"공연|뮤지컬|인형극|마술|음악", t):
        return "공연 시간표를 미리 확인하고 10~20분 일찍 도착하면 앞자리 잡기 좋아요."
    return "행사장 주차가 붐빌 수 있어요. 대중교통이나 오전 일찍 방문을 추천해요."

def tour_festivals(now, key, days=7):
    if not key:
        return None
    k = key if "%" in key else urllib.parse.quote(key, safe="")
    today = now.date()
    end = today + dt.timedelta(days=days)
    rows, page = [], 1
    while page <= 3:
        url = ("https://apis.data.go.kr/B551011/KorService2/searchFestival2?serviceKey=" + k + "&" + urllib.parse.urlencode({
            "MobileOS": "ETC", "MobileApp": "KidsBlog", "_type": "json", "arrange": "C", "numOfRows": 300, "pageNo": page,
            "eventStartDate": (today - dt.timedelta(days=60)).strftime("%Y%m%d")}))
        try:
            j = json.loads(_get(url, 30))
        except Exception as e:
            print(f"  관광공사 축제 정보 실패: {e}")
            return [] if not rows else rows
        body = (j.get("response") or {}).get("body") or {}
        items = (body.get("items") or {})
        items = items.get("item", []) if isinstance(items, dict) else []
        if isinstance(items, dict):
            items = [items]
        rows += items
        if len(rows) >= int(body.get("totalCount") or 0) or not items:
            break
        page += 1
    out = []
    for r in rows:
        try:
            s = dt.datetime.strptime(str(r.get("eventstartdate")), "%Y%m%d").date()
            e = dt.datetime.strptime(str(r.get("eventenddate")), "%Y%m%d").date()
        except Exception:
            continue
        if s > end or e < today:                       # 이번 주에 열리지 않음
            continue
        t = (r.get("title") or "").strip()
        if not t:
            continue
        kid = sum(w in t for w in FEST_KID) - 3 * sum(w in t for w in ADULT)
        addr = " ".join(x for x in [(r.get("addr1") or "").strip()] if x)
        first = addr.split(" ")[0] if addr else ""
        reg = ADDR_SHORT.get(first, first[:2])
        city = addr.split(" ")[1] if len(addr.split(" ")) > 1 else ""
        status = "진행 중" if s <= today else ("이번 주 시작" if (s - today).days <= days else "")
        out.append({"id": "f" + str(r.get("contentid", "")), "title": t, "start": s.isoformat(), "end": e.isoformat(),
                    "period": f"{s.month}/{s.day}({WD[s.weekday()]})~{e.month}/{e.day}({WD[e.weekday()]})",
                    "addr": addr, "region": reg, "city": city, "img": (r.get("firstimage") or "").replace("http://", "https://"),
                    "tel": (r.get("tel") or "").strip(), "kid": kid, "status": status, "tip": fest_tip(t),
                    "map": "https://map.naver.com/p/search/" + urllib.parse.quote(t)})
    out.sort(key=lambda x: (-(x["kid"] > 0), -x["kid"], x["end"]))   # 아이 친화 축제 → 곧 끝나는 순
    return out[:40]

# ---------------------------------------------------------------- 피드 갱신 (매시간)
def refresh_feed(now, base):
    prev = _load(os.path.join(base, "kids.json"), {})
    prev_ids = {x["id"] for x in prev.get("news", [])} | {x["id"] for x in prev.get("festivals", []) or []}
    news, arts = news_feed(now)
    fests = tour_festivals(now, os.environ.get("TOUR_API_KEY", "").strip())
    has_tour = bool(fests)
    nf = news_festivals(arts, now)
    if has_tour:                                            # 관광공사 목록 + 기사에만 나온 행사
        seen_n = {norm(f["title"]) for f in fests}
        fests_out = fests + [f for f in nf if norm(f["title"]) not in seen_n][:10]
    else:
        fests_out = nf
    tr = trends(arts, fests_out, now)
    has_naver = naver_buzz(tr, now)
    if not news and not fests_out and prev:
        print("키즈 소식을 새로 가져오지 못해 이전 내용을 유지합니다.")
        return prev
    prev_t = {x["id"] for x in prev.get("trends", [])}
    for x in news + fests_out:
        x["new"] = bool(prev_ids) and x["id"] not in prev_ids
    for x in tr:
        x["new"] = bool(prev_t) and x["id"] not in prev_t
    end = now.date() + dt.timedelta(days=7)
    cnt = {c["key"]: sum(1 for x in news if x["cat"] == c["key"]) for c in CATS}
    feed = {"updated": now.isoformat(), "has_tour": has_tour, "has_naver": has_naver, "trends": tr,
            "range": {"from": now.date().isoformat(), "to": end.isoformat(),
                      "label": f"{now.month}/{now.day}({WD[now.weekday()]}) ~ {end.month}/{end.day}({WD[end.weekday()]})"},
            "cats": [{**c, "count": cnt[c["key"]]} for c in CATS], "festivals": fests_out, "news": news}
    json.dump(feed, open(os.path.join(base, "kids.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    # 월별 기록 — 처음 본 소식·축제만 덧붙임
    ad = os.path.join(base, "kids_archive")
    os.makedirs(ad, exist_ok=True)
    ap = os.path.join(ad, now.strftime("%Y-%m") + ".json")
    arc = _load(ap, [])
    seen = {x["id"] for x in arc}
    for x in news + fests_out:
        if x["id"] not in seen:
            arc.append({k: x.get(k) for k in ("id", "cat", "title", "source", "url", "pub", "region", "period", "start", "end", "addr")} | {"seen": now.isoformat()})
    json.dump(arc, open(ap, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    print(f"키즈 소식 갱신: 기사 {len(news)}건 · 축제·행사 {len(fests_out)}건({'관광공사+기사' if has_tour else '기사에서 추출'}) · 화제 {len(tr)}건"
          + (" · 네이버 블로그 반응 반영" if has_naver else ""))
    return feed

# ---------------------------------------------------------------- 글 만들기 (하루 1편)
SEASON = {
    (12, 1, 2): ("겨울 나들이 준비물", ["두꺼운 외투 + 얇은 옷 여러 겹 (실내외 온도 차)", "핫팩·장갑·목도리·귀마개", "따뜻한 물 담은 보온병", "여벌 양말 (눈·물놀이 대비)", "입술·볼 보습제", "아이 상비약·체온계"]),
    (3, 4, 5): ("봄 나들이 준비물", ["얇은 겉옷 (일교차 대비)", "미세먼지 마스크", "모자·선크림", "돗자리·물티슈", "알레르기 상비약", "간식·물"]),
    (6, 7, 8): ("여름 나들이 준비물", ["모자·선크림·쿨토시", "물병 넉넉히 (탈수 주의)", "여벌 옷·수건", "모기 기피제", "휴대용 선풍기", "그늘 쉼터 위치 확인"]),
    (9, 10, 11): ("가을 나들이 준비물", ["일교차 대비 겉옷 (오후~저녁 쌀쌀)", "얇은 장갑·모자", "보온병에 따뜻한 물", "돗자리·물티슈", "간식·물", "상비약·밴드"]),
}
FOOD_CHECK = ["아기 의자·유아 식기가 있는지", "맵지 않은 메뉴(키즈 메뉴) 유무", "주차·유모차 진입이 편한지", "놀이 공간 또는 넓은 좌석", "웨이팅 시간 (아이는 오래 못 기다려요)", "노키즈존 여부 사전 확인"]
CAFE_TIP = ["공공형 키즈카페는 대부분 지자체 예약 사이트에서 회차별 사전 예약으로 운영돼요.",
            "이용료가 민간보다 저렴하거나 무료인 곳이 많지만, 거주 지역 제한이 있을 수 있어요.",
            "보호자 동반·양말 착용 같은 이용 규칙이 있으니 방문 전 안내문을 꼭 읽어 보세요.",
            "주말 회차는 금방 마감되니 예약 오픈 시간을 알람으로 맞춰 두면 좋아요."]

def season_pack(m):
    for ms, v in SEASON.items():
        if m in ms:
            return v
    return SEASON[(9, 10, 11)]

def build(now, base, out, feed=None):
    import render
    feed = feed or _load(os.path.join(base, "kids.json"), {})
    news, fests = feed.get("news", []), feed.get("festivals", []) or []
    if len(news) + len(fests) < 3:
        print("키즈 소식이 너무 적어 이번 키즈 글은 건너뜁니다.")
        return None
    up = os.path.join(base, "kids_used.json")
    used = _load(up, {})
    cut = (now - dt.timedelta(days=5)).isoformat()
    fresh = lambda x: used.get(x["id"], "") < cut
    def take(lst, n):
        a = [x for x in lst if fresh(x)]
        b = [x for x in lst if not fresh(x)]
        return (a + b)[:n]
    weekend = now.weekday() >= 3
    when = "이번 주말" if weekend else "이번 주"
    wk = ["첫", "둘", "셋", "넷", "다섯"][(now.day - 1) // 7]
    pid = now.strftime("%Y%m%d") + "-kids"
    n = 2
    while os.path.exists(os.path.join(base, "posts", pid + ".json")):
        pid = now.strftime("%Y%m%d") + f"-kids{n}"; n += 1
    rnd = random.Random(pid)

    F = take([f for f in fests if f["kid"] > 0], 6) or take(fests, 6)
    by = {c["key"]: take([x for x in news if x["cat"] == c["key"]], 3) for c in CATS}
    regs = [x["region"] for x in F if x.get("region")] + [x["region"] for v in by.values() for x in v if x.get("region")]
    top_reg = max(set(regs), key=regs.count) if regs else ""
    lead = F[0]["title"] if F else (by["festival"][0]["title"][:22] if by["festival"] else "")
    total = len(F) + sum(len(v) for v in by.values())
    titles = [
        f"[{when} 아이랑 어디 가지?] {now.month}월 {wk}째 주 어린이 축제·행사·키즈카페 총정리",
        f"{when} 아이와 가볼만한곳 {total}곳 모음 | 축제·공연·키즈카페 소식 한 번에",
        f"초등 아이랑 {when} 나들이 리스트 | {('‘' + lead + '’ 외 ') if F else ''}축제·체험·외식 정보 정리",
    ]
    title = rnd.choice(titles)

    # ---------- 이미지 ----------
    jobs, marks = [], {}
    def job(kind, data, where, label, pal="kids"):
        k = len(jobs) + 1
        jobs.append((kind, data, pal, f"data/img/{pid}-{k}.jpg"))
        marks.setdefault(where, []).append((k, label))
    top_items = [{"emo": "🎪", "t": f["title"], "s": f"{f['period']} · {f['region']}"} for f in F[:3]]
    for c in CATS:
        for x in by[c["key"]][:1]:
            if len(top_items) < 5:
                top_items.append({"emo": c["emo"], "t": x["title"], "s": c["name"] + (f" · {x['region']}" if x.get("region") else "")})
    job("kids_cover", {"badge": f"{when} 키즈 나들이", "title": f"{when}\n아이랑 어디 가지?", "date": feed.get("range", {}).get("label", ""),
                       "items": top_items}, "top", "대표 이미지")
    if F:
        job("kids_list", {"kicker": "이번 주 열리는 축제", "title": f"{when} 아이랑 갈 만한 축제", "items": [{"t": f["title"], "p": f["period"], "r": (f"{f['region']} {f.get('city', '')}".strip() or "전국"), "st": f.get("status", "")} for f in F],
                          "foot": "※ 한국관광공사 축제 정보·언론 보도 기준 · 일정은 방문 전 공식 안내 확인" if feed.get("has_tour") else "※ 언론 보도 기준 · 일정·장소는 방문 전 공식 안내 확인"}, "fest", "축제 리스트")
    job("checklist", {"title": "아이랑 외식할 곳 고를 때", "items": FOOD_CHECK}, "food", "외식 체크리스트", "kids")
    st, pack = season_pack(now.month)
    job("checklist", {"title": st, "items": pack}, "pack", "준비물 체크리스트", "kids2")

    # ---------- 본문 ----------
    H, T = [], []
    def mark(where):
        for k, label in marks.get(where, []):
            H.append(f'<p class="ph-mark">📷 사진 {k} · {esc(label)}</p>'); T.append(f"[📷 사진 {k} · {label}]")
    def p(t):
        H.append(f"<p>{esc(t)}</p>"); T.append(t)
    def blank():
        H.append("<p></p>"); T.append("")
    def h3(t):
        H.append(f"<h3>{esc(t)}</h3>"); T.append("━━━━━━━━━━━━\n" + t)
    def links(items):
        H.append("<ul>" + "".join(f'<li><a href="{esc(x["url"])}">{esc(x["title"])}</a>{" (" + esc(x["source"]) + ")" if x.get("source") else ""}'
                                  f'{" · " + esc(x["period"]) if x.get("period") else ""}</li>' for x in items) + "</ul>")
        T.extend(f"▶ {x['title']}{' (' + x['source'] + ')' if x.get('source') else ''}{' · ' + x['period'] if x.get('period') else ''}\n   {x['url']}" for x in items)

    mark("top"); blank()
    p(rnd.choice([
        f"안녕하세요! 주말만 되면 ‘아이랑 어디 가지?’가 제일 큰 고민인 키즈 나들이 블로거예요 😊 {when}에 아이와 함께 가기 좋은 축제·행사·키즈카페·외식 소식을 한 번에 모아 왔어요.",
        f"초등 아이 키우는 집이라면 매주 하는 고민, ‘{when} 뭐 하지?’ 🤔 그래서 {when} 아이랑 가볼 만한 곳과 새로 나온 키즈 소식을 정리해 봤어요.",
        f"{now.month}월 {wk}째 주, 아이랑 나들이 계획 세우셨나요? 🎈 {when} 열리는 축제부터 키즈카페·공연·외식 소식까지 엄마 아빠 입장에서 필요한 정보만 골라 담았어요.",
    ]))
    p(f"📅 기준 기간: {feed.get('range', {}).get('label', '')} · 일정과 운영 여부는 바뀔 수 있으니 출발 전에 공식 안내를 꼭 확인해 주세요!")
    blank()

    h3("📌 한눈에 보기")
    i = 1
    for f in F:
        p(f"{i}. 🎪 {f['title']} · {f['region']} · {f['period']}"); i += 1
    for c in CATS:
        for x in by[c["key"]][:2]:
            if i <= 10:
                p(f"{i}. {c['emo']} {x['title']}"); i += 1
    blank()

    if F:
        h3(f"🎪 {when} 열리는 축제 · 행사")
        p("한국관광공사 축제 정보와 최근 기사에서 이번 주 열리는 행사 중 아이와 가기 좋은 곳을 골랐어요." if feed.get("has_tour")
          else "최근 일주일 기사에 소개된 축제·행사 중 아이와 가기 좋은 곳을 골랐어요. 정확한 시간·장소는 기사 원문으로 확인해 주세요.")
        blank()
        for k, f in enumerate(F, 1):
            H.append(f"<h4>{k}. {esc(f['title'])}</h4>"); T.append(f"{k}. {f['title']}")
            p(f"📅 기간: {f['period']}{' · ' + f['status'] if f.get('status') else ''}")
            if f.get("addr"):
                p(f"📍 장소: {f['addr']}")
            if f.get("tel"):
                p(f"☎ 문의: {f['tel']}")
            if f.get("from") == "news" and f.get("url"):
                p(f"📰 관련 기사: {f.get('src_title', '')}{' (' + f['source'] + ')' if f.get('source') else ''}")
                p(f"   {f['url']}")
            p(f"👧 아이랑 팁: {f['tip']}")
            p(f"🗺 지도: {f['map']}")
            blank()
        mark("fest"); blank()

    sec = [("festival", "🎈 화제의 어린이 행사 · 체험 소식", "최근 일주일 동안 나온 어린이·가족 행사 기사예요. 지역 행사는 접수가 빨리 끝나니 관심 가는 곳은 바로 확인해 보세요."),
           ("show", "🎭 어린이 공연 · 전시", "실내에서 즐길 수 있는 공연·전시 소식이에요. 날씨가 애매한 날 플랜 B로 좋아요."),
           ("kidscafe", "🧸 키즈카페 · 실내 놀이터 소식", "새로 문 연 곳이나 공공형 키즈카페 소식이에요."),
           ("place", "🗺️ 아이랑 가볼만한 곳", "주말 나들이 장소로 눈여겨볼 만한 소식이에요."),
           ("food", "🍽️ 아이랑 외식 · 맛집 소식", "가족 외식 메뉴나 아이 동반하기 좋은 식당 관련 소식이에요.")]
    for key, head, intro in sec:
        items = by.get(key) or []
        if not items and key not in ("kidscafe", "food"):
            continue
        h3(head)
        if items:
            p(intro)
            links(items)
        if key == "kidscafe":
            blank(); p("💡 공공형 키즈카페 이용 팁")
            for t in rnd.sample(CAFE_TIP, 3):
                p(f"· {t}")
        if key == "food":
            blank(); p("💡 아이랑 식당 고를 때 이것만 체크!")
            for t in FOOD_CHECK:
                p(f"☑ {t}")
            mark("food")
        blank()

    h3(f"🎒 {st}")
    for t in pack:
        p(f"☑ {t}")
    mark("pack"); blank()

    h3("✍️ 마무리")
    p(rnd.choice([
        "아이랑 함께하는 하루는 거창하지 않아도 충분히 특별하더라고요. 이번 주 리스트 중 한 곳이라도 즐거운 추억이 되면 좋겠어요 💛",
        "모든 곳을 다 갈 수는 없지만, 아이 취향에 맞는 한 곳만 골라도 주말이 훨씬 알차져요. 다녀오신 곳 있으면 댓글로 후기 나눠 주세요!",
        "매주 아이랑 갈 만한 곳을 정리해서 올리고 있어요. 이웃 추가해 두시면 다음 주 나들이 리스트도 놓치지 않으실 거예요 😊",
    ]))
    p("여러분은 이번 주말 아이와 어디 가실 계획인가요? 댓글로 추천 장소도 알려 주세요 👇")
    blank()
    src = "※ 축제 정보: 한국관광공사 TourAPI · 소식: 각 언론사 기사(Google 뉴스 검색) · " if feed.get("has_tour") else "※ 소식·행사: 각 언론사 기사(Google 뉴스 검색) · "
    p(src + f"{now.strftime('%Y-%m-%d %H:%M')} 기준. 행사 일정·요금·예약은 변동될 수 있으니 방문 전 공식 안내를 확인하세요.")
    tags = ["아이랑가볼만한곳", "아이와가볼만한곳", "주말나들이", "어린이축제", "키즈카페", "공공형키즈카페", "아이랑맛집", "초등맘", "육아정보",
            f"{now.month}월축제", f"{now.month}월아이랑가볼만한곳"]
    for r in dict.fromkeys(regs):
        if len(tags) < 15:
            tags.append(f"{r}가볼만한곳")
    tags = list(dict.fromkeys(tags))[:15]
    p(" ".join("#" + t for t in tags))

    imgs = render.render_all(jobs, out)
    for x in F + [x for v in by.values() for x in v]:
        used[x["id"]] = now.isoformat()
    old = (now - dt.timedelta(days=60)).isoformat()
    used = {k: v for k, v in used.items() if v >= old}
    json.dump(used, open(up, "w", encoding="utf-8"), ensure_ascii=False)
    return {"id": pid, "kind": "kids", "label": f"키즈 · {when}", "title": title, "html": "\n".join(H), "text": "\n".join(T),
            "tags": tags, "keywords": [f["title"] for f in F[:3]] or [top_reg or "키즈"], "edition": "kids", "created": now.isoformat(),
            "images": imgs, "chars": len("".join(T)),
            "kids": {"when": when, "range": feed.get("range", {}).get("label", ""), "fests": F,
                     "news": [x for v in by.values() for x in v], "region": top_reg}}


# ---------------------------------------------------------------- 🔥 키즈 화제 글 (하루 여러 번 · 요즘 유행/화제 행사 하나를 골라서)
TREND_CP = {
    "food": ["성분표·알레르기 유발 성분 먼저 확인", "가격·양 대비 괜찮은지 비교", "당·나트륨이 높다면 간식 횟수 정하기", "줄 서는 곳은 웨이팅 시간 미리 확인"],
    "toy": ["KC 안전 인증 여부 확인", "정품·공식 판매처인지 확인 (품절 대란 땐 가품 주의)", "권장 연령·작은 부품 확인", "친구 따라 사는 분위기라면 아이와 용돈 기준 정하기"],
    "place": ["운영 시간·예약제 여부 확인", "주말엔 오픈 직후가 여유로워요", "주차·대중교통 미리 확인", "아이 연령에 맞는 체험인지 확인"],
    "media": ["시청 연령 등급 확인", "하루 시청·사용 시간 함께 정하기", "아이가 왜 좋아하는지 같이 이야기해 보기", "관련 굿즈 구매는 공식몰에서"],
    "etc": ["공식 안내·판매처에서 정보 확인", "아이와 함께 장단점 이야기해 보기", "유행 따라 무리한 소비는 금물", "주변 엄마들 후기도 한 번 더 확인"],
}
def trend_type(t):
    if re.search(r"간식|과자|빵|쿠키|젤리|음료|아이스크림|디저트|먹|메뉴|맛|탕후루|라면", t): return "food"
    if re.search(r"장난감|카드|피규어|인형|굿즈|문구|키링|스티커|블록|레고|게임기|딱지|팽이", t): return "toy"
    if re.search(r"애니|만화|캐릭터|유튜브|게임|영화|드라마|노래|챌린지|웹툰", t): return "media"
    if re.search(r"축제|행사|공원|놀이|체험|전시|공연|키즈카페|박물관|과학관|썰매|마켓", t): return "place"
    return "etc"

def due_hot(base, now, gap_min=170):
    """마지막 키즈 화제 글 뒤로 gap_min 분이 지났고, 아침 8시~밤 10시면 True"""
    if not (8 <= now.hour <= 22):
        return False
    lst = _load(os.path.join(base, "posts.json"), [])
    last = max((x["created"] for x in lst if x.get("kind") == "kids" and x.get("label", "").startswith("키즈 화제")), default="")
    return not last or (now - dt.datetime.fromisoformat(last)).total_seconds() / 60 >= gap_min

def build_hot(now, base, out, feed=None):
    import render
    feed = feed or _load(os.path.join(base, "kids.json"), {})
    tr = feed.get("trends", []) or []
    up = os.path.join(base, "kids_hot_used.json")
    used = _load(up, {})
    cut = (now - dt.timedelta(hours=36)).isoformat()
    pool = list(tr) + [{"id": "t" + f["id"], "kind": "fest", "name": f["title"], "count": f.get("count", 1), "region": f.get("region", ""),
                        "period": f.get("period", ""), "tip": f.get("tip", ""), "map": f.get("map", ""), "arts": f.get("arts") or []}
                       for f in (feed.get("festivals") or []) if f.get("kid", 0) >= 1]      # 유행 주제가 다 떨어지면 아이 친화 행사로
    cands = [t for t in pool if used.get(norm(t["name"]), "") < cut and t.get("arts")]
    if not cands:
        print("새로 쓸 키즈 화제 주제가 없어 이번에는 건너뜁니다.")
        return None
    t = cands[0]
    n, arts, fest = t["name"], t["arts"], t.get("kind") == "fest"
    tt = "place" if fest else trend_type(n + " " + " ".join(a["title"] for a in arts))
    pid = now.strftime("%Y%m%d-%H") + "k"
    k = 2
    while os.path.exists(os.path.join(base, "posts", pid + ".json")):
        pid = now.strftime("%Y%m%d-%H") + f"k{k}"; k += 1
    rnd = random.Random(pid + n)
    eul = "을" if (0xac00 <= ord(n[-1]) <= 0xd7a3 and (ord(n[-1]) - 0xac00) % 28) else "를"
    if fest:
        titles = [f"요즘 가족들 몰리는 ‘{n}’, 아이랑 가기 전 꼭 보세요", f"이번 주 아이랑 ‘{n}’ 어때요? 기간·꿀팁 정리",
                  f"{t.get('region') + ' ' if t.get('region') else ''}아이랑 가볼만한곳 | ‘{n}’ 화제인 이유"]
        badge = "🎪 요즘 화제인 행사"
    else:
        titles = [f"요즘 아이들 사이 난리 난 ‘{n}’, 부모님이 알아야 할 것", f"초등학생 사이 화제 ‘{n}’ 대체 뭐길래? 엄마가 정리했어요",
                  f"‘{n}’ 왜 이렇게 인기일까? 아이 키우는 집 필독 정리"]
        badge = "🔥 요즘 아이들 사이 화제"
    title = rnd.choice(titles)
    bt = t.get("blog_total")
    sub = f"기사 {t['count']}건" + (f" · 네이버 블로그 {bt:,}건" if bt else "")
    def ago(iso):
        try:
            h = int((now - dt.datetime.fromisoformat(iso)).total_seconds() // 3600)
            return f"{h}시간 전" if h < 24 else f"{h // 24}일 전"
        except Exception:
            return ""
    jobs = [("kids_cover", {"badge": badge, "title": n if len(n) <= 9 else n[:9] + "\n" + n[9:20], "date": sub,
                            "items": [{"emo": "📰", "t": a["title"], "s": f"{a.get('source', '')} · {ago(a['pub'])}"} for a in arts[:4]]}, "kids", f"data/img/{pid}-1.jpg"),
            ("kids_list", {"kicker": "엄마 아빠 체크 포인트", "title": f"‘{n}’ 이것만 확인!" if len(n) <= 12 else "이것만 확인하세요!",
                           "items": [{"t": c, "p": "", "r": ""} for c in TREND_CP[tt]], "foot": "※ 기사·공식 안내를 함께 확인하세요", "plain": True}, "kids2", f"data/img/{pid}-2.jpg")]
    imgs = render.render_all(jobs, out)

    H, T = [], []
    def p(x):
        H.append(f"<p>{esc(x)}</p>"); T.append(x)
    def blank():
        H.append("<p></p>"); T.append("")
    def h3(x):
        H.append(f"<h3>{esc(x)}</h3>"); T.append("━━━━━━━━━━━━\n" + x)
    def mk(i, label):
        if len(imgs) >= i:
            H.append(f'<p class="ph-mark">📷 사진 {i} · {esc(label)}</p>'); T.append(f"[📷 사진 {i} · {label}]")
    mk(1, "대표 이미지"); blank()
    p(rnd.choice([f"안녕하세요, 아이 키우는 집 소식은 제일 빠르게 챙기는 키즈 블로거예요 😊 요즘 ‘{n}’ 이야기가 정말 많이 보이더라고요.",
                  f"요즘 아이 친구 엄마들 만나면 꼭 나오는 이야기, 바로 ‘{n}’이에요 👀 무슨 일인지 정리해 봤어요.",
                  f"‘{n}’ 들어 보셨나요? 최근 아이 키우는 집 사이에서 자주 언급되길래 관련 소식을 모아 봤어요 🎈"]))
    blank()
    h3("🔥 왜 화제일까?")
    p(f"최근 일주일 동안 ‘{n}’ 관련 기사가 {t['count']}건 나왔어요." + (f" 네이버 블로그에도 관련 글이 {bt:,}건 올라와 있을 만큼 관심이 많아요." if bt else ""))
    if t.get("blog_recent"):
        p(f"특히 최근 일주일 사이에도 새 블로그 글이 계속 올라오고 있어요.")
    blank()
    h3("📰 관련 기사")
    H.append("<ul>" + "".join(f'<li><a href="{esc(a["url"])}">{esc(a["title"])}</a>{" (" + esc(a["source"]) + ")" if a.get("source") else ""}</li>' for a in arts[:4]) + "</ul>")
    T.extend(f"▶ {a['title']}{' (' + a['source'] + ')' if a.get('source') else ''}\n   {a['url']}" for a in arts[:4])
    blank()
    if fest:
        h3("📅 기본 정보")
        p(f"· 행사: {n}")
        if t.get("period"): p(f"· 기간: {t['period']}")
        if t.get("region"): p(f"· 지역: {t['region']}")
        if t.get("map"): p(f"· 지도: {t['map']}")
        if t.get("tip"): p(f"👧 아이랑 팁: {t['tip']}")
        blank()
    if t.get("blogs"):
        h3("📝 다른 부모님들 후기 글")
        H.append("<ul>" + "".join(f'<li><a href="{esc(b["url"])}">{esc(b["title"])}</a> ({esc(b["by"])} {esc(b["date"])})</li>' for b in t["blogs"]) + "</ul>")
        T.extend(f"▶ {b['title']} ({b['by']} {b['date']})\n   {b['url']}" for b in t["blogs"])
        blank()
    mk(2, "체크 포인트")
    h3("✅ 엄마 아빠 체크 포인트")
    for i, c in enumerate(TREND_CP[tt], 1):
        p(f"{i}. {c}")
    blank()
    h3("💬 제 생각")
    p({"food": "아이들 사이 유행 간식은 한 번쯤 경험해 보는 것도 추억이지만, 횟수와 양은 집에서 기준을 정해 두면 마음이 편하더라고요.",
       "toy": "유행 장난감은 금방 지나가기도 해서, 아이와 ‘정말 갖고 싶은지’ 한 번 더 이야기해 보고 사는 걸 추천해요.",
       "media": "아이가 좋아하는 콘텐츠를 같이 한 번 봐 두면 대화 거리도 생기고, 걱정되는 부분도 미리 알 수 있어요.",
       "place": "사람이 몰릴 때는 시간대만 잘 골라도 만족도가 확 달라져요. 아이 컨디션 좋은 오전을 추천해요!",
       "etc": "유행은 빠르게 바뀌지만, 아이가 왜 좋아하는지 들어 보면 의외로 배울 점이 많더라고요."}[tt])
    blank()
    p(f"한 줄 정리 👉 요즘 화제인 ‘{n}’, 핵심만 알고 아이와 즐겁게 이야기 나눠 보세요 💛")
    p(f"여러분 아이도 ‘{n}’ 좋아하나요? 댓글로 이야기 나눠요 👇")
    blank()
    p(f"※ 소식: 각 언론사 기사(Google 뉴스 검색){' · 네이버 블로그 검색' if bt else ''} · {now.strftime('%Y-%m-%d %H:%M')} 기준. 자세한 내용은 원문과 공식 안내로 확인하세요.")
    base_tag = re.sub(r"[^\w가-힣]", "", n)[:20]
    tags = list(dict.fromkeys([base_tag, base_tag + "후기", "요즘유행", "초등학생유행", "아이들사이인기", "초등맘", "육아정보", "육아맘", "키즈트렌드",
                               "아이랑가볼만한곳" if fest else "아이간식" if tt == "food" else "인기장난감" if tt == "toy" else "육아꿀팁"]))[:12]
    p(" ".join("#" + x for x in tags))
    used[norm(n)] = now.isoformat()
    old = (now - dt.timedelta(days=30)).isoformat()
    json.dump({a: b for a, b in used.items() if b >= old}, open(up, "w", encoding="utf-8"), ensure_ascii=False)
    return {"id": pid, "kind": "kids", "label": f"키즈 화제 {now.hour}시", "title": title, "html": "\n".join(H), "text": "\n".join(T),
            "tags": tags, "keywords": [n], "edition": "kids", "created": now.isoformat(), "images": imgs, "chars": len("".join(T)),
            "kidshot": {"name": n, "count": t["count"], "blog_total": bt or 0, "fest": fest, "arts": arts[:4], "cps": TREND_CP[tt]}}
