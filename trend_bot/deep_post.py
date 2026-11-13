# -*- coding: utf-8 -*-
"""
심층 분석 글 (요일별 분야 · 직접 쓴 장문 원고 + 자체 제작 디자인 이미지 4~6장)
  월 재테크·경제 · 화 IT·디지털 · 수 육아·교육 · 목 건강·생활 · 금 음식·요리 · 토 여행 · 일 영화·책·음악
본문에는 '[📷 사진 N]' 자리 표시가 들어가서 네이버 블로그에 사진을 어디에 넣을지 바로 알 수 있습니다.
"""
import html, json, os, random, re
import render

HERE = os.path.dirname(os.path.abspath(__file__))
WEEK = ["money", "it", "parenting", "health", "food", "travel", "culture"]
CAT = {"money": "재테크·경제", "it": "IT·디지털", "parenting": "육아·교육", "health": "건강·생활",
       "food": "음식·요리", "travel": "여행", "culture": "영화·책·음악", "life": "살림·생활"}
NOTE = {"money": "※ 이 글은 일반적인 금융 상식을 정리한 것으로, 특정 상품의 가입이나 투자를 권유하지 않습니다. 세금·금리 등 세부 기준은 시기에 따라 바뀌니 해당 기관에서 최신 내용을 꼭 확인하세요.",
        "health": "※ 이 글은 일반적인 생활 건강 정보이며 의학적 진단이나 치료를 대신하지 않습니다. 증상이 있거나 지병이 있다면 전문의와 상담하세요.",
        "parenting": "※ 아이마다 발달 속도와 성향이 다릅니다. 걱정되는 부분이 있다면 소아청소년과나 전문 기관에 상담해 보세요."}

def esc(s):
    return html.escape(str(s), quote=True)

def load_bank():
    bank = {}
    d = os.path.join(HERE, "articles")
    for f in sorted(os.listdir(d)):
        if f.endswith(".json"):
            for a in json.load(open(os.path.join(d, f), encoding="utf-8")):
                bank.setdefault(a["cat"], []).append(a)
    return bank

def pick(now, base):
    bank = load_bank()
    up = os.path.join(base, "deep_used.json")
    used = json.load(open(up, encoding="utf-8")) if os.path.exists(up) else []
    want = WEEK[now.weekday()]
    order = [want] + [c for c in WEEK if c != want]           # 그 요일 분야가 다 떨어지면 다른 분야에서
    for c in order:
        fresh = [a for a in bank.get(c, []) if a["id"] not in used]
        if fresh:
            a = fresh[0]
            break
    else:                                                       # 전부 썼으면 가장 오래된 것부터 다시
        allx = [a for v in bank.values() for a in v]
        a = sorted(allx, key=lambda x: used.index(x["id"]) if x["id"] in used else -1)[0]
        used.remove(a["id"])
    used.append(a["id"])
    json.dump(used, open(up, "w", encoding="utf-8"))
    return a

def build(now, base, out):
    a = pick(now, base)
    pid = now.strftime("%Y%m%d") + "-deep"
    n = 2
    while os.path.exists(os.path.join(base, "posts", pid + ".json")):   # 같은 날 여러 편이면 -deep2, -deep3 …
        pid = now.strftime("%Y%m%d") + f"-deep{n}"; n += 1
    cat = a["cat"]
    catname = CAT.get(cat, "생활")
    date = f"{now.year}. {now.month}. {now.day}."

    # ---------- 이미지 계획 ----------
    jobs, marks = [], {}
    def job(kind, data, where, label):
        n = len(jobs) + 1
        jobs.append((kind, data, cat, f"data/img/{pid}-{n}.jpg"))
        marks.setdefault(where, []).append((n, label))
    job("cover", {"title": a["title"], "subtitle": a.get("subtitle", ""), "badge": catname, "emoji": a.get("emoji"), "foot": date}, "top", "대표 이미지")
    job("summary", {"title": a.get("summary_title", "이 글의 핵심 3가지"), "items": a["summary"]}, "summary", "핵심 요약")
    pt_done = tb_done = False
    for i, s in enumerate(a["sections"]):
        if s.get("table") and not tb_done:
            t = s["table"]; job("table", {"title": t.get("title", s["h"]), "head": t["head"], "rows": t["rows"]}, f"s{i}", "비교표"); tb_done = True
        elif s.get("points") and not pt_done:
            job("points", {"title": s["h"], "items": s["points"][:5], "no": f"{i + 1:02d}", "kicker": f"POINT {i + 1}"}, f"s{i}", s["h"]); pt_done = True
    if a.get("checklist"):
        job("checklist", {"title": a["checklist"]["title"], "items": a["checklist"]["items"][:6]}, "check", "체크리스트")
    if a.get("tip"):
        job("tip", {"text": a["tip"], "kicker": "기억해 두면 좋은 한 가지"}, "end", "팁 카드")

    # ---------- 본문 ----------
    H, T = [], []
    def mark(where):
        for n, label in marks.get(where, []):
            H.append(f'<p class="ph-mark">📷 사진 {n} · {esc(label)}</p>'); T.append(f"[📷 사진 {n} · {label}]")
    def p(t):
        H.append(f"<p>{esc(t)}</p>"); T.append(t)
    def blank():
        H.append("<p></p>"); T.append("")

    mark("top"); blank()
    for x in a["intro"]:
        p(x); blank()
    H.append("<h3>📌 이 글의 핵심</h3>"); T.append("━━━━━━━━━━━━\n📌 이 글의 핵심")
    for i, x in enumerate(a["summary"], 1):
        p(f"{i}. {x}")
    mark("summary"); blank()
    for i, s in enumerate(a["sections"]):
        H.append(f"<h3>{i + 1}. {esc(s['h'])}</h3>"); T.append(f"━━━━━━━━━━━━\n■ {i + 1}. {s['h']}")
        for x in s.get("paras", []):
            p(x); blank()
        if s.get("points"):
            H.append("<ul>" + "".join(f"<li>{esc(x)}</li>" for x in s["points"]) + "</ul>")
            T.extend(f"▶ {x}" for x in s["points"]); blank()
        if s.get("table"):
            t = s["table"]
            H.append("<table border='1' cellpadding='6' style='border-collapse:collapse'><tr>" + "".join(f"<th>{esc(h)}</th>" for h in t["head"]) + "</tr>"
                     + "".join("<tr>" + "".join(f"<td>{esc(c)}</td>" for c in r) + "</tr>" for r in t["rows"]) + "</table>")
            T.append(" | ".join(t["head"]))
            T.extend("· " + " | ".join(r) for r in t["rows"]); blank()
        if s.get("tip"):
            p(f"✔ 포인트: {s['tip']}"); blank()
        mark(f"s{i}")
        if marks.get(f"s{i}"):
            blank()
    if a.get("checklist"):
        H.append(f"<h3>✅ {esc(a['checklist']['title'])}</h3>"); T.append(f"━━━━━━━━━━━━\n✅ {a['checklist']['title']}")
        for x in a["checklist"]["items"]:
            p(f"☑ {x}")
        mark("check"); blank()
    if a.get("faq"):
        H.append("<h3>❓ 자주 묻는 질문</h3>"); T.append("━━━━━━━━━━━━\n❓ 자주 묻는 질문")
        for q in a["faq"]:
            p(f"Q. {q['q']}"); p(f"A. {q['a']}"); blank()
    H.append("<h3>✍️ 마무리</h3>"); T.append("━━━━━━━━━━━━\n✍️ 마무리")
    for x in (a["outro"] if isinstance(a["outro"], list) else [a["outro"]]):
        p(x)
    mark("end"); blank()
    if NOTE.get(cat):
        H.append(f"<p><i>{esc(NOTE[cat])}</i></p>"); T.append(NOTE[cat]); blank()
    tags = a["tags"][:10]
    p(" ".join("#" + t for t in tags))

    imgs = render.render_all(jobs, out)
    return {"id": pid, "kind": "deep", "label": f"심층 · {catname}", "theme": catname, "title": a["title"],
            "html": "\n".join(H), "text": "\n".join(T), "tags": tags, "keywords": [catname], "edition": "deep",
            "created": now.isoformat(), "images": imgs, "entry": a["id"], "chars": len("".join(T)), "_article": a}
