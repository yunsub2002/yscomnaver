# -*- coding: utf-8 -*-
"""
블로그용 디자인 이미지 만들기 (외부 사진 없이 100% 자체 제작 → 저작권 걱정 없음)
HTML/CSS 로 카드를 디자인하고 Chromium(Playwright)으로 PNG 를 찍습니다.

  cover      표지 (제목 · 부제 · 분야 · 큰 이모지 일러스트)
  summary    핵심 요약 3줄
  table      비교표
  checklist  체크리스트
  points     소제목 + 핵심 포인트
  tip        한 줄 팁 / 인용
  trend_*    트렌드 글용 표지 · 순위표 · 분야 분포 그래프
"""
import html, os

PALETTES = {
    "money":     {"a": "#0b7a5a", "b": "#0f2e2a", "c": "#d6f5e9", "acc": "#21d19f", "emo": ["💰", "📈", "🏦", "🪙"]},
    "it":        {"a": "#3b5bdb", "b": "#141a3a", "c": "#e3e9ff", "acc": "#7c9cff", "emo": ["💻", "📱", "🔐", "⚙️"]},
    "parenting": {"a": "#f08c00", "b": "#3a2205", "c": "#fff1d6", "acc": "#ffb84d", "emo": ["👶", "🧸", "📚", "🌈"]},
    "health":    {"a": "#0c8599", "b": "#08303a", "c": "#d9f6fb", "acc": "#3bc9db", "emo": ["🏃", "🥗", "😴", "💧"]},
    "food":      {"a": "#e8590c", "b": "#3a1606", "c": "#ffe8d9", "acc": "#ff922b", "emo": ["🍳", "🥘", "🧄", "🍅"]},
    "travel":    {"a": "#1971c2", "b": "#0a2440", "c": "#dcecff", "acc": "#4dabf7", "emo": ["✈️", "🧳", "🗺️", "🏝️"]},
    "culture":   {"a": "#7048e8", "b": "#1f1446", "c": "#ece5ff", "acc": "#9775fa", "emo": ["🎬", "🎵", "📖", "🎧"]},
    "life":      {"a": "#2f9e44", "b": "#0f2e17", "c": "#e0f7e4", "acc": "#51cf66", "emo": ["🏠", "🧺", "🌿", "🧹"]},
    "hot":       {"a": "#ff2d3d", "b": "#2a0a12", "c": "#ffe3e6", "acc": "#ff6b76", "emo": ["🔥", "📈", "⚡", "👀"]},
    "kids":      {"a": "#ff7a45", "b": "#3b1d4a", "c": "#fff4e6", "acc": "#ffd43b", "emo": ["🎈", "🧸", "🎪", "🌈"]},
    "kids2":     {"a": "#12b886", "b": "#0b3a3a", "c": "#e6fcf5", "acc": "#63e6be", "emo": ["🎒", "🧤", "🧃", "☀️"]},
    "trend":     {"a": "#e03131", "b": "#1b1d2e", "c": "#ffe3e3", "acc": "#ff6b6b", "emo": ["🔥", "📊", "🔎", "⚡"]},
}

BASE_CSS = """
*{box-sizing:border-box;margin:0;padding:0}
body{width:1080px;font-family:"Noto Sans CJK KR","Noto Sans KR","Malgun Gothic",sans-serif;-webkit-font-smoothing:antialiased;word-break:keep-all}
.emo{font-family:"Noto Color Emoji","Apple Color Emoji","Segoe UI Emoji",sans-serif;line-height:1}
.card{width:1080px;position:relative;overflow:hidden}
.pill{display:inline-block;padding:12px 26px;border-radius:99px;font-size:30px;font-weight:800;letter-spacing:-.3px}
.brand{position:absolute;right:56px;bottom:40px;font-size:24px;font-weight:700;opacity:.6}
"""

def e(s):
    return html.escape(str(s), quote=True)

def pal(key):
    return PALETTES.get(key, PALETTES["life"])

# ---------------------------------------------------------------- 템플릿
def t_cover(d, p):
    em = p["emo"]
    main = e(d.get("emoji") or em[0])
    sub = e(d.get("subtitle", ""))
    return f"""<div class="card" style="height:1080px;background:radial-gradient(circle at 78% 22%,{p['a']} 0,{p['b']} 68%);color:#fff">
 <div style="position:absolute;right:-120px;top:-120px;width:620px;height:620px;border-radius:50%;background:{p['acc']};opacity:.18"></div>
 <div style="position:absolute;right:120px;top:300px;width:300px;height:300px;border-radius:50%;background:#fff;opacity:.06"></div>
 <div class="emo" style="position:absolute;right:120px;top:110px;font-size:300px;transform:rotate(-8deg);filter:drop-shadow(0 30px 40px rgba(0,0,0,.35))">{main}</div>
 <div class="emo" style="position:absolute;right:470px;top:120px;font-size:96px;transform:rotate(12deg);opacity:.95">{e(em[1])}</div>
 <div class="emo" style="position:absolute;right:60px;top:430px;font-size:110px;transform:rotate(-14deg);opacity:.95">{e(em[2])}</div>
 <div class="emo" style="position:absolute;right:420px;top:400px;font-size:70px;transform:rotate(18deg);opacity:.8">{e(em[3])}</div>
 <div style="position:absolute;left:72px;top:72px"><span class="pill" style="background:{p['acc']};color:{p['b']}">{e(d.get('badge',''))}</span></div>
 <div style="position:absolute;left:72px;right:72px;bottom:150px">
  <div style="font-size:74px;font-weight:900;line-height:1.22;letter-spacing:-2px;text-shadow:0 4px 24px rgba(0,0,0,.35)">{e(d['title'])}</div>
  {f'<div style="margin-top:26px;font-size:34px;font-weight:600;opacity:.88;line-height:1.45">{sub}</div>' if sub else ''}
 </div>
 <div style="position:absolute;left:72px;bottom:64px;font-size:26px;font-weight:700;opacity:.7">{e(d.get('foot',''))}</div>
</div>"""

def t_summary(d, p):
    items = "".join(f"""<div style="display:flex;gap:30px;align-items:flex-start;background:#fff;border-radius:28px;padding:38px 40px;margin-bottom:26px;box-shadow:0 10px 30px rgba(0,0,0,.06)">
   <div style="flex:none;width:76px;height:76px;border-radius:22px;background:{p['a']};color:#fff;font-size:40px;font-weight:900;display:flex;align-items:center;justify-content:center">{i}</div>
   <div style="font-size:38px;font-weight:700;line-height:1.5;color:#1d2330;letter-spacing:-.6px;padding-top:6px">{e(t)}</div></div>"""
                    for i, t in enumerate(d["items"], 1))
    return f"""<div class="card" style="background:{p['c']};padding:80px 64px 90px">
 <div style="font-size:30px;font-weight:800;color:{p['a']};margin-bottom:14px">{e(d.get('kicker','핵심 요약'))}</div>
 <div style="font-size:60px;font-weight:900;color:#141a26;letter-spacing:-1.5px;line-height:1.25;margin-bottom:48px">{e(d['title'])}</div>
 {items}
 <div class="emo" style="position:absolute;right:56px;top:60px;font-size:110px;opacity:.9">{e(p['emo'][1])}</div>
</div>"""

def t_table(d, p):
    head = "".join(f'<th style="padding:26px 22px;text-align:left;font-size:30px;color:#fff;background:{p["a"]};font-weight:800">{e(h)}</th>' for h in d["head"])
    rows = ""
    for r, row in enumerate(d["rows"]):
        bg = "#ffffff" if r % 2 == 0 else p["c"]
        rows += "<tr>" + "".join(f'<td style="padding:26px 22px;font-size:29px;line-height:1.45;color:#1d2330;background:{bg};{"font-weight:800" if c == 0 else ""}">{e(x)}</td>'
                                 for c, x in enumerate(row)) + "</tr>"
    return f"""<div class="card" style="background:#f6f7fb;padding:80px 56px 90px">
 <div style="font-size:30px;font-weight:800;color:{p['a']};margin-bottom:14px">한눈에 비교</div>
 <div style="font-size:56px;font-weight:900;color:#141a26;letter-spacing:-1.4px;line-height:1.25;margin-bottom:44px">{e(d['title'])}</div>
 <table style="width:100%;border-collapse:separate;border-spacing:0;border-radius:26px;overflow:hidden;box-shadow:0 12px 34px rgba(0,0,0,.08)"><tr>{head}</tr>{rows}</table>
</div>"""

def t_checklist(d, p):
    items = "".join(f"""<div style="display:flex;gap:26px;align-items:center;padding:30px 0;border-bottom:2px dashed rgba(255,255,255,.18)">
   <div style="flex:none;width:58px;height:58px;border-radius:16px;background:{p['acc']};color:{p['b']};font-size:40px;font-weight:900;display:flex;align-items:center;justify-content:center">✓</div>
   <div style="font-size:36px;font-weight:700;line-height:1.45;letter-spacing:-.5px">{e(t)}</div></div>""" for t in d["items"])
    return f"""<div class="card" style="background:linear-gradient(160deg,{p['b']},#000);color:#fff;padding:84px 70px 100px">
 <div style="font-size:30px;font-weight:800;color:{p['acc']};margin-bottom:14px">CHECK LIST</div>
 <div style="font-size:58px;font-weight:900;letter-spacing:-1.4px;line-height:1.25;margin-bottom:30px">{e(d['title'])}</div>
 {items}
 <div class="emo" style="position:absolute;right:60px;top:66px;font-size:100px">{e(p['emo'][2])}</div>
</div>"""

def t_points(d, p):
    items = "".join(f"""<div style="display:flex;gap:22px;align-items:flex-start;margin-bottom:30px">
   <div style="flex:none;width:18px;height:18px;border-radius:50%;background:{p['a']};margin-top:20px"></div>
   <div style="font-size:36px;line-height:1.55;color:#1d2330;font-weight:600;letter-spacing:-.5px">{e(t)}</div></div>""" for t in d["items"])
    return f"""<div class="card" style="background:#fff;padding:0 0 80px">
 <div style="background:{p['a']};color:#fff;padding:70px 70px 60px;position:relative">
  <div style="font-size:120px;font-weight:900;opacity:.25;position:absolute;right:60px;top:20px">{e(d.get('no',''))}</div>
  <div style="font-size:30px;font-weight:800;opacity:.85;margin-bottom:12px">{e(d.get('kicker','POINT'))}</div>
  <div style="font-size:58px;font-weight:900;letter-spacing:-1.4px;line-height:1.25;max-width:820px">{e(d['title'])}</div>
 </div>
 <div style="padding:64px 70px 0">{items}</div>
</div>"""

def t_tip(d, p):
    return f"""<div class="card" style="height:1080px;background:{p['c']};display:flex;flex-direction:column;justify-content:center;padding:0 90px">
 <div class="emo" style="font-size:150px;margin-bottom:40px">💡</div>
 <div style="font-size:34px;font-weight:800;color:{p['a']};margin-bottom:22px">{e(d.get('kicker','오늘의 팁'))}</div>
 <div style="font-size:56px;font-weight:900;color:#141a26;line-height:1.42;letter-spacing:-1.2px">{e(d['text'])}</div>
 <div style="width:120px;height:10px;border-radius:5px;background:{p['a']};margin-top:56px"></div>
</div>"""

def t_trend_cover(d, p):
    rows = "".join(f"""<div style="display:flex;align-items:center;gap:26px;background:{'rgba(255,255,255,.16)' if i == 1 else 'rgba(255,255,255,.07)'};border-radius:24px;padding:24px 30px;margin-bottom:16px">
  <div style="width:56px;font-size:46px;font-weight:900;color:{'#ffd43b' if i <= 3 else '#adb5bd'};text-align:center">{i}</div>
  <div style="flex:1;font-size:44px;font-weight:800;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{e(k['keyword'])}</div>
  <div style="font-size:26px;font-weight:700;color:#ced4da">{e(k.get('cat',''))}</div></div>""" for i, k in enumerate(d["items"][:5], 1))
    return f"""<div class="card" style="height:1080px;background:linear-gradient(150deg,#1b1d2e 0,#2b1220 100%);color:#fff;padding:70px 64px">
 <div style="position:absolute;right:-160px;top:-160px;width:560px;height:560px;border-radius:50%;background:#e03131;opacity:.25"></div>
 <div class="emo" style="position:absolute;right:70px;top:70px;font-size:130px">🔥</div>
 <span class="pill" style="background:#ff6b6b;color:#1b1d2e">{e(d['badge'])}</span>
 <div style="font-size:72px;font-weight:900;letter-spacing:-2px;margin:34px 0 8px">{e(d['date'])}</div>
 <div style="font-size:40px;font-weight:700;color:#ced4da;margin-bottom:44px">지금 사람들이 찾는 키워드</div>
 {rows}
 <div class="brand" style="color:#fff">Google 트렌드(대한민국) 기준</div>
</div>"""

def t_trend_dist(d, p):
    mx = max(v for _, v in d["dist"]) or 1
    bars = "".join(f"""<div style="display:flex;align-items:center;gap:24px;margin-bottom:30px">
  <div style="width:250px;font-size:34px;font-weight:800;color:#1d2330">{e(k)}</div>
  <div style="flex:1;height:58px;background:#eef1f6;border-radius:16px;overflow:hidden"><div style="width:{max(8, v / mx * 100):.0f}%;height:100%;background:linear-gradient(90deg,#ff6b6b,#e03131);border-radius:16px"></div></div>
  <div style="width:80px;font-size:36px;font-weight:900;color:#e03131;text-align:right">{v}</div></div>""" for k, v in d["dist"])
    notes = "".join(f'<div style="font-size:32px;line-height:1.6;color:#343a40;margin-bottom:8px">• {e(n)}</div>' for n in d.get("notes", []))
    return f"""<div class="card" style="background:#fff;padding:80px 64px 90px">
 <div style="font-size:30px;font-weight:800;color:#e03131;margin-bottom:14px">이번 회차 흐름</div>
 <div style="font-size:58px;font-weight:900;color:#141a26;letter-spacing:-1.4px;margin-bottom:50px">어떤 분야가 화제였나</div>
 {bars}
 <div style="margin-top:30px;background:#fff5f5;border-radius:24px;padding:34px 38px">{notes}</div>
</div>"""

def t_hot_cover(d, p):
    tl = d.get("timeline") or []
    tl_html = ""
    if len(tl) >= 2:
        tl_html = '<div style="display:flex;gap:10px;flex-wrap:wrap;margin-top:34px">' + "".join(
            f'<div style="background:rgba(255,255,255,.12);border-radius:16px;padding:12px 18px;font-size:26px;font-weight:700"><span style="opacity:.7">{e(t)}</span> <b style="color:#ffd43b">{e(r)}위</b></div>' for t, r in tl[-5:]) + "</div>"
    news_html = ""
    if d.get("news"):
        news_html = '<div style="position:absolute;left:66px;right:66px;bottom:120px;background:rgba(0,0,0,.35);border:2px solid rgba(255,255,255,.12);border-radius:26px;padding:28px 32px">' + \
            '<div style="font-size:26px;font-weight:800;color:#ff8a93;margin-bottom:12px">📰 지금 나온 소식</div>' + "".join(
            f'<div style="font-size:32px;font-weight:700;line-height:1.4;margin:8px 0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">· {e(n["title"])}</div>' for n in d["news"][:2]) + "</div>"
    kw = e(d["keyword"])
    fs = 150 if len(d["keyword"]) <= 4 else 120 if len(d["keyword"]) <= 6 else 92 if len(d["keyword"]) <= 9 else 72
    return f"""<div class="card" style="height:1080px;background:linear-gradient(155deg,#0d0d14 0,#2a0a12 60%,#4a0d14 100%);color:#fff;padding:70px 66px">
 <div style="position:absolute;inset:0;background:repeating-linear-gradient(135deg,rgba(255,255,255,.025) 0 14px,transparent 14px 28px)"></div>
 <div style="position:absolute;right:-140px;bottom:-160px;width:640px;height:640px;border-radius:50%;background:#ff2d3d;opacity:.22;filter:blur(10px)"></div>
 <div style="display:flex;gap:14px;align-items:center;position:relative">
  <span class="pill" style="background:#ff2d3d;color:#fff">● 실시간 {e(d['rank'])}위</span>
  <span class="pill" style="background:rgba(255,255,255,.14);color:#fff">{e(d.get('state',''))}</span>
 </div>
 <div style="position:relative;margin-top:96px;font-size:40px;font-weight:800;color:#ffb3b8">지금 검색 폭주 중</div>
 <div style="position:relative;font-size:{fs}px;font-weight:900;letter-spacing:-3px;line-height:1.1;margin-top:10px;text-shadow:0 6px 30px rgba(255,45,61,.45)">{kw}</div>
 <div style="position:relative;font-size:38px;font-weight:700;margin-top:28px;color:#e9ecef">{e(d.get('sub',''))}</div>
 {tl_html}
 {news_html}
 <div class="emo" style="position:absolute;right:66px;top:150px;font-size:150px">🔥</div>
 <div style="position:absolute;left:66px;bottom:58px;font-size:28px;font-weight:700;color:#adb5bd">{e(d.get('time',''))} · {e(d.get('cat',''))}</div>
 <div class="brand" style="color:#fff">Google 트렌드(대한민국) 기준</div>
</div>"""

def t_headlines(d, p):
    rows = "".join(f"""<div style="background:#fff;border-radius:26px;padding:34px 38px;margin-bottom:22px;box-shadow:0 10px 30px rgba(0,0,0,.07);border-left:12px solid #ff2d3d">
   <div style="font-size:36px;font-weight:800;line-height:1.45;color:#141a26;letter-spacing:-.6px">{e(h['title'])}</div>
   <div style="font-size:26px;font-weight:700;color:#868e96;margin-top:14px">{e(h.get('source',''))}</div></div>""" for h in d["items"][:3])
    return f"""<div class="card" style="background:#f4f5f8;padding:80px 60px 90px">
 <div style="font-size:30px;font-weight:800;color:#ff2d3d;margin-bottom:14px">무슨 일? 주요 보도</div>
 <div style="font-size:60px;font-weight:900;color:#141a26;letter-spacing:-1.5px;line-height:1.25;margin-bottom:46px">'{e(d['keyword'])}' 관련 소식</div>
 {rows}
 <div style="font-size:26px;color:#868e96;margin-top:20px">※ 기사 제목은 각 언론사 원문 · 자세한 내용은 원문 확인</div>
</div>"""

def t_kids_cover(d, p):
    rows = "".join(f"""<div style="display:flex;align-items:center;gap:22px;background:#fff;border-radius:26px;padding:22px 28px;margin-bottom:16px;box-shadow:0 8px 24px rgba(59,29,74,.12)">
  <div class="emo" style="flex:none;font-size:52px">{e(x.get('emo','🎈'))}</div>
  <div style="flex:1;min-width:0"><div style="font-size:36px;font-weight:900;color:#2b1b38;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;letter-spacing:-.6px">{e(x['t'])}</div>
  <div style="font-size:25px;font-weight:700;color:#8a7a99;margin-top:4px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{e(x.get('s',''))}</div></div></div>""" for x in d.get("items", [])[:5])
    title = "<br>".join(e(t) for t in d["title"].split("\n"))
    return f"""<div class="card" style="min-height:1080px;background:linear-gradient(165deg,#ffe8cc 0,#ffd8e4 55%,#e5dbff 100%);padding:70px 64px 110px">
 <div style="position:absolute;right:-90px;top:-90px;width:420px;height:420px;border-radius:50%;background:#ffd43b;opacity:.55"></div>
 <div style="position:absolute;left:-120px;bottom:-140px;width:380px;height:380px;border-radius:50%;background:#91a7ff;opacity:.35"></div>
 <div class="emo" style="position:absolute;right:70px;top:70px;font-size:120px;transform:rotate(10deg)">🎈</div>
 <div class="emo" style="position:absolute;right:230px;top:190px;font-size:70px;transform:rotate(-12deg)">🧸</div>
 <span class="pill" style="position:relative;background:{p['a']};color:#fff">{e(d.get('badge',''))}</span>
 <div style="position:relative;font-size:84px;font-weight:900;line-height:1.18;letter-spacing:-2.5px;color:#2b1b38;margin:34px 0 14px">{title}</div>
 <div style="position:relative;font-size:32px;font-weight:800;color:#7c4d9e;margin-bottom:40px">📅 {e(d.get('date',''))}</div>
 <div style="position:relative">{rows}</div>
 <div class="brand" style="color:#5f3d7a">아이랑 나들이 · 축제 · 키즈카페</div>
</div>"""

def t_kids_list(d, p):
    rows = "".join(f"""<div style="display:flex;gap:24px;align-items:center;background:#fff;border-radius:24px;padding:26px 30px;margin-bottom:18px;border:3px solid {p['c']}">
  <div style="flex:none;width:70px;height:70px;border-radius:50%;background:{p['a']};color:#fff;font-size:36px;font-weight:900;display:flex;align-items:center;justify-content:center">{i}</div>
  <div style="flex:1;min-width:0"><div style="font-size:35px;font-weight:900;color:#1d2330;line-height:1.3;letter-spacing:-.6px;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden">{e(x['t'])}</div>
  {'' if d.get('plain') else f'<div style="font-size:26px;font-weight:700;color:#6b7385;margin-top:8px">📅 {e(x.get("p",""))} · 📍 {e(x.get("r",""))}</div>'}</div>
  {f'<div style="flex:none;font-size:24px;font-weight:900;color:{p["a"]};background:{p["c"]};border-radius:99px;padding:8px 16px">{e(x["st"])}</div>' if x.get('st') else ''}</div>""" for i, x in enumerate(d["items"][:6], 1))
    return f"""<div class="card" style="background:{p['c']};padding:80px 56px 100px">
 <div style="font-size:30px;font-weight:800;color:{p['a']};margin-bottom:14px">{e(d.get('kicker',''))}</div>
 <div style="font-size:60px;font-weight:900;color:#2b1b38;letter-spacing:-1.5px;line-height:1.25;margin-bottom:44px">{e(d['title'])}</div>
 {rows}
 <div class="emo" style="position:absolute;right:56px;top:62px;font-size:110px">{'✅' if d.get('plain') else '🎪'}</div>
 <div style="font-size:24px;color:#8a8f9c;margin-top:16px">{e(d.get('foot','※ 일정은 방문 전 공식 안내 확인'))}</div>
</div>"""

T = {"kids_cover": t_kids_cover, "kids_list": t_kids_list, "hot_cover": t_hot_cover, "headlines": t_headlines, "cover": t_cover, "summary": t_summary, "table": t_table, "checklist": t_checklist, "points": t_points,
     "tip": t_tip, "trend_cover": t_trend_cover, "trend_dist": t_trend_dist}

# ---------------------------------------------------------------- 찍기
def render_all(jobs, out_dir_root):
    """jobs: [(kind, data, palette_key, rel_path)] → 성공한 rel_path 목록"""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("  (Playwright 없음 → 디자인 이미지 생략)")
        return []
    done = []
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        pg = b.new_page(viewport={"width": 1080, "height": 1080}, device_scale_factor=1)
        for kind, data, pk, rel in jobs:
            try:
                body = T[kind](data, pal(pk))
                pg.set_content(f"<!doctype html><html><head><meta charset='utf-8'><style>{BASE_CSS}</style></head><body>{body}</body></html>")
                pg.wait_for_timeout(120)
                h = pg.evaluate("document.querySelector('.card').getBoundingClientRect().height")
                h = int(min(max(h, 600), 1620))
                pg.set_viewport_size({"width": 1080, "height": h})
                path = os.path.join(out_dir_root, rel)
                os.makedirs(os.path.dirname(path), exist_ok=True)
                pg.screenshot(path=path, clip={"x": 0, "y": 0, "width": 1080, "height": h}, type="jpeg", quality=90)
                done.append(rel)
            except Exception as ex:
                print(f"  이미지 실패 ({kind}): {ex}")
        b.close()
    return done
