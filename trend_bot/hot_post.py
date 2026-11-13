# -*- coding: utf-8 -*-
"""
🔥 화제 글 (매시간) — 실시간 인기 검색어 중 '지금 막 뜬' 키워드 하나를 골라
조회수 상위 이슈 글 형식(후킹 제목 · 무슨 일? · 검색 흐름 · 체크 포인트 · 함께 뜨는 키워드)으로 정리합니다.
사건·사고·재판·정치 키워드는 make_post.is_safe 로 미리 걸러진 것만 씁니다.
"""
import datetime as dt, html, json, os, random, re, urllib.parse
import render

QUESTIONS = {
    "연예·방송": ["어떤 작품·활동과 관련된 소식인지", "공식 발표나 소속사 입장이 있었는지", "앞으로 공개될 일정은 무엇인지"],
    "스포츠": ["경기 결과와 화제가 된 장면", "선수·팀에 어떤 영향이 있는지", "다음 경기 일정과 관전 포인트"],
    "경제·재테크": ["내 생활·지갑에 어떤 영향이 있는지", "언제부터, 누구에게 적용되는지", "공식 발표에서 확인할 숫자"],
    "IT·테크": ["무엇이 새로 나오거나 바뀌는지", "언제, 누구에게 적용되는지", "사용자가 지금 해 둘 일"],
    "날씨·생활": ["언제, 어느 지역에 해당하는지", "생활에 어떤 영향이 있는지", "미리 준비할 것"],
    "사회·정치": ["무엇이 달라지는지", "대상과 시기", "공식 안내를 어디서 확인할 수 있는지"],
    "기타": ["왜 갑자기 관심이 몰렸는지", "핵심 사실이 무엇인지", "앞으로 지켜볼 부분"],
}

def esc(s):
    return html.escape(str(s), quote=True)

def _load(p, d):
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else d

def timeline(base, kw, now):
    """오늘(+어제) 순위 기록에서 이 키워드의 순위 흐름"""
    out = []
    for day in (now - dt.timedelta(days=1), now):
        for snap in _load(os.path.join(base, "rank_history", day.strftime("%Y-%m-%d") + ".json"), []):
            if kw in snap["k"]:
                out.append((snap["t"][-5:], snap["k"].index(kw) + 1))
    # 같은 순위 연속은 하나로
    tl = []
    for t, r in out:
        if not tl or tl[-1][1] != r:
            tl.append((t, r))
    return tl, len(out)

def pick(items, base, now, safe):
    used = _load(os.path.join(base, "hot_used.json"), {})
    cut = (now - dt.timedelta(hours=18)).isoformat()
    cands = [i for i in items if safe(i) and used.get(i["keyword"], "") < cut]
    if not cands:
        return None, used
    return cands[0], used        # items 는 검색량 순 → 가장 위의 새 키워드

def build(items, rank_items, now, base, out, safe, classify, traffic_label):
    it, used = pick(items, base, now, safe)
    if not it:
        print("이번 시간에는 새로 쓸 화제 키워드가 없어 건너뜁니다.")
        return None
    kw = it["keyword"]
    rank = next((x["rank"] for x in rank_items if x["keyword"] == kw), items.index(it) + 1)
    move = next((x["move"] for x in rank_items if x["keyword"] == kw), "new")
    cat, emo = classify(it)
    tl, seen = timeline(base, kw, now)
    rnd = random.Random(now.strftime("%Y%m%d%H") + kw)
    hm = now.strftime("%H:%M")
    if rank == 1:
        state = "검색 1위"
        title = rnd.choice([f"실시간 1위 '{kw}', 지금 다들 이걸 찾는 이유", f"검색 1위 찍은 '{kw}'…지금 무슨 일이 벌어지고 있나"])
    elif seen >= 3:
        state = f"{seen}회 연속 상위권"
        title = rnd.choice([f"'{kw}' 몇 시간째 검색 상위권…아직 모르는 분들 위한 핵심 정리", f"계속 검색되는 '{kw}', 왜 관심이 식지 않을까?"])
    elif move == "new":
        state = "급상승 NEW"
        title = rnd.choice([f"방금 급상승한 '{kw}', 갑자기 왜 뜬 걸까?", f"'{kw}' 검색이 갑자기 몰린 이유, 3분 만에 정리"])
    else:
        state = "상승 중"
        title = rnd.choice([f"지금 뜨는 '{kw}', 핵심만 빠르게 정리했습니다", f"'{kw}' 왜 이렇게 많이 검색될까? 지금 상황 총정리"])
    pid = now.strftime("%Y%m%d-%H") + "h"
    n = 2
    while os.path.exists(os.path.join(base, "posts", pid + ".json")):   # 같은 시간에 또 돌리면 -2, -3 …
        pid = now.strftime("%Y%m%d-%H") + f"h{n}"; n += 1
    tr = traffic_label(it["traffic"])
    news = it["news"]

    # 이미지 2장
    jobs = [("hot_cover", {"keyword": kw, "rank": rank, "state": state, "sub": f"검색 {tr}", "time": f"{now.month}/{now.day} {hm}",
                           "cat": f"{emo} {cat}", "timeline": tl, "news": news}, "hot", f"data/img/{pid}-1.jpg")]
    if news:
        jobs.append(("headlines", {"keyword": kw, "items": news}, "hot", f"data/img/{pid}-2.jpg"))
    imgs = render.render_all(jobs, out)

    H, T = [], []
    def p(t, raw=False):
        H.append(f"<p>{t if raw else esc(t)}</p>"); T.append(re.sub(r"<[^>]+>", "", html.unescape(t)) if raw else t)
    def mk(n, label):
        if len(imgs) >= n:
            H.append(f'<p class="ph-mark">📷 사진 {n} · {label}</p>'); T.append(f"[📷 사진 {n} · {label}]")
    def h3(t):
        H.append(f"<h3>{esc(t)}</h3>"); T.append("━━━━━━━━━━━━\n" + t)

    mk(1, "대표 이미지"); p("")
    p(f"{now.month}월 {now.day}일 {hm} 기준, 구글 트렌드 실시간 인기 검색어 {rank}위에 '{kw}'가 올라 있어요. 검색량은 {tr}. "
      f"지금 왜 이렇게 많이들 찾아보는지, 핵심만 빠르게 정리했습니다.")
    p("")
    h3("🔥 지금 무슨 일?")
    if news:
        p(f"현재 '{kw}'와 관련해 이런 보도가 나와 있어요.")
        H.append("<ul>" + "".join(f'<li><a href="{esc(n["url"])}">{esc(n["title"])}</a> ({esc(n["source"])})</li>' for n in news) + "</ul>")
        T.extend(f"▶ {n['title']} ({n['source']})\n   {n['url']}" for n in news)
    else:
        p("아직 관련 보도가 많지 않아요. 검색량이 먼저 늘어난 경우라 곧 소식이 이어질 수 있습니다.")
    mk(2, "주요 보도"); p("")
    h3("📈 검색 흐름")
    if len(tl) >= 2:
        p(" → ".join(f"{t} {r}위" for t, r in tl[-6:]) + f" (지금 {rank}위)")
        p("순위가 계속 유지되거나 올라가고 있다면, 당분간 관련 소식이 더 이어질 가능성이 커요.")
    else:
        p(f"이번 시간에 처음 순위권에 들어온 '{state}' 키워드예요. 짧은 시간에 관심이 확 몰린 경우입니다.")
    p("")
    h3("✅ 체크 포인트")
    for q in QUESTIONS.get(cat, QUESTIONS["기타"]):
        p(f"☑ {q}")
    p("위 내용은 기사 원문과 공식 발표에서 확인하는 것이 가장 정확해요.")
    p("")
    others = [x for x in items if x is not it and safe(x)][:5]
    if others:
        h3("👀 함께 뜨는 키워드")
        p(" · ".join(f"{x['keyword']}" for x in others))
        p("")
    h3("한 줄 정리")
    p(rnd.choice([f"'{kw}', 지금 가장 뜨거운 관심사 중 하나예요. 새 소식이 나오면 순위가 또 움직일 수 있으니 계속 지켜보세요.",
                  f"정리하면, '{kw}'는 {cat} 분야에서 지금 관심이 몰린 키워드입니다. 공식 발표와 원문 기사를 함께 확인해 보세요."]))
    p("")
    q = urllib.parse.quote(kw)
    p(f"🔎 더 찾아보기: 네이버에서 '{kw}' 검색 → https://search.naver.com/search.naver?query={q}")
    p(f"※ 인기 검색어: Google 트렌드(대한민국) {now.strftime('%Y-%m-%d %H:%M')} 기준 · 기사 제목·링크는 각 언론사 원문입니다.")
    tags = [re.sub(r"\s+", "", kw)[:20], "실시간검색어", "오늘의이슈", "이슈정리", "화제", re.sub(r"[·\s]", "", cat), "트렌드"]
    p(" ".join("#" + t for t in tags))

    used[kw] = now.isoformat()
    json.dump(used, open(os.path.join(base, "hot_used.json"), "w", encoding="utf-8"), ensure_ascii=False)
    return {"id": pid, "kind": "hot", "label": f"화제 {now.strftime('%H')}시", "title": title, "html": "\n".join(H), "text": "\n".join(T),
            "tags": tags, "keywords": [kw], "edition": "hot", "created": now.isoformat(), "images": imgs,
            "hot": {"keyword": kw, "rank": rank, "state": state, "cat": cat, "emo": emo, "traffic": tr, "timeline": tl, "news": news}}
