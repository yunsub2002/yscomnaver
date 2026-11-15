# -*- coding: utf-8 -*-
"""
📸 인스타그램 · 🧵 스레드용 콘텐츠 만들기
  - 심층 글  → 인스타 카드뉴스(이미지 6장) + 캡션 / 스레드 연속 글 4~5개 + 표지 이미지
  - 화제 글  → 인스타 이슈 카드(1~2장) + 캡션 / 스레드 연속 글 3~4개 + 이미지
후킹은 강하게, 사실이 아닌 숫자·단정은 쓰지 않습니다. (스레드 글 1개는 500자 이내)
모든 콘텐츠는 data/social/ 에 최신 300개 + 월별 보관함(archive)으로 계속 쌓입니다.
"""
import datetime as dt, json, os, random, re

HOOK_DEEP = ["이거 모르고 지나치면 계속 손해예요 😱", "저장 필수 📌 나중에 꼭 다시 찾게 됩니다", "생각보다 많은 사람이 놓치는 부분, 정리했어요 👀",
             "알고 나면 왜 이제 알았나 싶은 것들 💡", "딱 5분만 투자하세요. 확 달라집니다 🔥", "주변에 꼭 공유해 주고 싶은 정보예요 🙌"]
CTA_INSTA = ["📌 저장해 두고 필요할 때 꺼내 보세요", "💬 도움 됐다면 저장 + 공유 부탁해요", "👉 더 자세한 내용은 프로필 링크(블로그)에서"]
CAT_TAGS = {"money": ["재테크", "돈관리", "경제공부", "재테크꿀팁", "월급관리"], "it": ["IT꿀팁", "스마트폰꿀팁", "디지털라이프", "생활꿀팁", "테크"],
            "parenting": ["육아", "육아꿀팁", "육아정보", "엄마표", "육아스타그램"], "health": ["건강", "건강관리", "생활습관", "건강정보", "웰니스"],
            "food": ["요리", "요리꿀팁", "집밥", "레시피", "살림꿀팁"], "travel": ["여행", "여행꿀팁", "여행준비", "여행스타그램", "여행정보"],
            "kids": ["아이랑가볼만한곳", "주말나들이", "어린이축제", "키즈카페", "육아스타그램", "초등맘", "아이랑놀기"],
            "culture": ["문화생활", "영화추천", "책추천", "취미", "문화"], "hot": ["실시간검색어", "오늘의이슈", "이슈", "화제", "트렌드"]}
COMMON = ["정보공유", "꿀팁", "알아두면좋은정보", "저장각"]

def clip(s, n=480):
    return s if len(s) <= n else s[: n - 1] + "…"

def hashtags(tags, cat, n=25):
    seen, out = set(), []
    for t in list(tags) + CAT_TAGS.get(cat, []) + COMMON:
        t = re.sub(r"[\s#·/]", "", t)
        if t and t not in seen:
            seen.add(t); out.append(t)
    return out[:n]

def from_deep(post, a):
    rnd = random.Random(post["id"])
    cat = a["cat"]
    hook = rnd.choice(HOOK_DEEP)
    tags = hashtags(post["tags"], cat)
    cap = [hook, "", f"[{a['title']}]", "", "👇 핵심만 3줄 요약"]
    cap += [f"✔ {x}" for x in a["summary"]]
    if a.get("tip"):
        cap += ["", f"💡 {a['tip']}"]
    cap += ["", rnd.choice(CTA_INSTA), ".", " ".join("#" + t for t in tags)]
    insta = {"id": post["id"] + "-ig", "src": "deep", "label": post["label"], "created": post["created"], "title": a["title"],
             "images": post["images"], "caption": "\n".join(cap), "tags": tags}
    # 스레드: 1 후킹 → 2~4 핵심 → 5 마무리
    posts = [clip(f"{hook}\n\n{a['title']}\n\n핵심만 짧게 정리해 볼게요 🧵")]
    for i, x in enumerate(a["summary"], 1):
        extra = ""
        for s in a["sections"]:
            if s.get("points") and len(s["points"]) >= i:
                extra = "\n→ " + s["points"][i - 1]
                break
        posts.append(clip(f"{i}/ {x}{extra}"))
    posts.append(clip(f"{a.get('tip', '')}\n\n도움 됐다면 저장해 두세요 🔖\n여러분은 어떻게 하고 계세요? 댓글로 알려 주세요 👇"))
    threads = {"id": post["id"] + "-th", "src": "deep", "label": post["label"], "created": post["created"], "title": a["title"],
               "images": post["images"][:1], "posts": posts, "tags": tags[:5]}
    return insta, threads

def from_hot(post):
    h = post["hot"]
    rnd = random.Random(post["id"])
    kw, news = h["keyword"], h["news"]
    tags = hashtags([kw, re.sub(r"\s+", "", kw) + "이슈"] + post["tags"], "hot")
    first = rnd.choice([f"🔥 지금 '{kw}' 검색 폭주 중", f"🚨 실시간 {h['rank']}위 '{kw}', 무슨 일?", f"👀 갑자기 다들 '{kw}' 찾는 이유"])
    cap = [first, "", f"구글 트렌드 실시간 {h['rank']}위 · 검색 {h['traffic']}", "", "📰 지금 나온 소식"]
    cap += [f"{'①②③'[i]} {n['title']} ({n['source']})" for i, n in enumerate(news[:3])] or ["아직 관련 보도가 많지 않아요. 곧 소식이 이어질 수 있어요."]
    if len(h["timeline"]) >= 2:
        cap += ["", "📈 검색 흐름: " + " → ".join(f"{t} {r}위" for t, r in h["timeline"][-4:])]
    cap += ["", "자세한 건 기사 원문에서 확인하세요 👉 정리 글은 프로필 링크", ".", " ".join("#" + t for t in tags)]
    insta = {"id": post["id"] + "-ig", "src": "hot", "label": post["label"], "created": post["created"], "title": f"'{kw}' 실시간 {h['rank']}위",
             "images": post["images"], "caption": "\n".join(cap), "tags": tags}
    posts = [clip(f"{first} 🧵\n\n실시간 {h['rank']}위, 검색 {h['traffic']}. 왜 이렇게 뜨는지 정리해 봤어요.")]
    if news:
        posts.append(clip("1/ 지금 나온 소식\n" + "\n".join(f"- {n['title']} ({n['source']})" for n in news[:3])))
    if len(h["timeline"]) >= 2:
        posts.append(clip("2/ 검색 흐름\n" + " → ".join(f"{t} {r}위" for t, r in h["timeline"][-6:]) + "\n관심이 계속 올라가는 중이에요."))
    posts.append(clip(f"여러분은 '{kw}' 소식 어떻게 보세요? 댓글로 의견 남겨 주세요 👇\n(기사 원문으로 꼭 사실 확인!)"))
    threads = {"id": post["id"] + "-th", "src": "hot", "label": post["label"], "created": post["created"], "title": f"'{kw}' 실시간 {h['rank']}위",
               "images": post["images"][:1], "posts": posts, "tags": tags[:5]}
    return insta, threads

def from_kids(post):
    k = post["kids"]
    rnd = random.Random(post["id"])
    when, F, news = k["when"], k["fests"], k["news"]
    tags = hashtags(post["tags"], "kids")
    first = rnd.choice([f"🎈 {when} 아이랑 어디 가지? 고민 끝!", f"📌 저장 필수! {when} 아이랑 갈 만한 곳 모음", f"👧 {when} 키즈 나들이 리스트 정리했어요"])
    cap = [first, "", f"📅 {k['range']}", ""]
    if F:
        cap += ["🎪 이번 주 축제·행사"] + [f"{i}. {f['title']} ({f['region']} · {f['period']})" for i, f in enumerate(F[:5], 1)] + [""]
    if news:
        cap += ["📰 새로 나온 키즈 소식"] + [f"• {n['title']}" for n in news[:4]] + [""]
    cap += ["일정·예약은 방문 전 공식 안내로 꼭 확인하세요 🙏", "👉 자세한 정리는 프로필 링크(블로그)", ".", " ".join("#" + t for t in tags)]
    insta = {"id": post["id"] + "-ig", "src": "kids", "label": post["label"], "created": post["created"], "title": post["title"],
             "images": post["images"], "caption": "\n".join(cap), "tags": tags}
    posts = [clip(f"{first} 🧵\n\n축제·공연·키즈카페·외식 소식까지 아이 키우는 집에 필요한 것만 모았어요.")]
    if F:
        posts.append(clip("1/ 이번 주 열리는 축제\n" + "\n".join(f"- {f['title']} ({f['region']}, {f['period']})" for f in F[:4])))
    if news:
        posts.append(clip(f"{2 if F else 1}/ 새로 나온 키즈 소식\n" + "\n".join(f"- {n['title']}" for n in news[:4])))
    posts.append(clip("여러분은 이번 주말 아이랑 어디 가세요?\n추천 장소 댓글로 알려 주세요 👇 (일정은 공식 안내 확인!)"))
    threads = {"id": post["id"] + "-th", "src": "kids", "label": post["label"], "created": post["created"], "title": post["title"],
               "images": post["images"][:1], "posts": posts, "tags": tags[:5]}
    return insta, threads

def from_kids_hot(post):
    h = post["kidshot"]
    rnd = random.Random(post["id"])
    n = h["name"]
    tags = hashtags(post["tags"], "kids")
    first = rnd.choice([f"👀 요즘 아이들 사이 ‘{n}’ 난리라던데?", f"🔥 초등맘들 사이 화제 ‘{n}’ 정리", f"📌 ‘{n}’ 모르면 아이랑 대화 안 돼요"])
    info = f"최근 기사 {h['count']}건" + (f" · 네이버 블로그 {h['blog_total']:,}건" if h.get("blog_total") else "")
    cap = [first, "", info, "", "📰 지금 나온 소식"] + [f"• {a['title']}" for a in h["arts"][:3]] + ["", "✅ 엄마 아빠 체크"] + [f"• {c}" for c in h["cps"][:3]]
    cap += ["", "자세한 정리는 프로필 링크(블로그) 👉", ".", " ".join("#" + t for t in tags)]
    insta = {"id": post["id"] + "-ig", "src": "kids", "label": post["label"], "created": post["created"], "title": f"키즈 화제 ‘{n}’",
             "images": post["images"], "caption": "\n".join(cap), "tags": tags}
    posts = [clip(f"{first} 🧵\n\n{info}. 무슨 일인지 짧게 정리해 볼게요."),
             clip("1/ 지금 나온 소식\n" + "\n".join(f"- {a['title']}" for a in h["arts"][:3])),
             clip("2/ 엄마 아빠 체크 포인트\n" + "\n".join(f"- {c}" for c in h["cps"])),
             clip(f"여러분 아이도 ‘{n}’ 좋아하나요? 댓글로 이야기 나눠요 👇")]
    threads = {"id": post["id"] + "-th", "src": "kids", "label": post["label"], "created": post["created"], "title": f"키즈 화제 ‘{n}’",
               "images": post["images"][:1], "posts": posts, "tags": tags[:5]}
    return insta, threads

def save(base, kind, item):
    d = os.path.join(base, "social")
    os.makedirs(os.path.join(d, "archive"), exist_ok=True)
    p = os.path.join(d, kind + ".json")
    lst = json.load(open(p, encoding="utf-8")) if os.path.exists(p) else []
    lst = [x for x in lst if x["id"] != item["id"]]
    lst.insert(0, item)
    lst.sort(key=lambda x: x["created"], reverse=True)
    json.dump(lst[:300], open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    ap = os.path.join(d, "archive", f"{kind}-{item['created'][:7]}.json")     # 월별 보관함 (지우지 않음)
    arc = json.load(open(ap, encoding="utf-8")) if os.path.exists(ap) else []
    arc = [x for x in arc if x["id"] != item["id"]] + [item]
    json.dump(arc, open(ap, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
