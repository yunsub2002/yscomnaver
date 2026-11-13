# -*- coding: utf-8 -*-
"""
요일별 생활 테마 글 (점심 12:23 생성)
  월 음식 · 화 영화·음악 · 수 육아 · 목 여행 · 금 취미·살림 · 토 음식 · 일 여행
원고는 themes/*.json (직접 쓴 글) 에서 안 쓴 것부터 고르고, 사진은 photos.py 로 가져옵니다.
"""
import datetime as dt, html, json, os, random, re
import photos

HERE = os.path.dirname(os.path.abspath(__file__))
WEEK = ["food", "culture", "parenting", "travel", "hobby", "food", "travel"]   # 월~일
MONTH_LINE = {
    1: "새해의 설렘이 남아 있는 1월이에요.", 2: "겨울의 끝자락, 봄이 기다려지는 2월이에요.", 3: "봄기운이 느껴지기 시작하는 3월이에요.",
    4: "꽃 소식이 반가운 4월이에요.", 5: "초록이 짙어지는 가정의 달 5월이에요.", 6: "초여름 햇살이 기분 좋은 6월이에요.",
    7: "본격적인 여름이 시작된 7월이에요.", 8: "한여름의 열기가 가득한 8월이에요.", 9: "선선한 바람이 반가운 9월이에요.",
    10: "가을이 깊어 가는 10월이에요.", 11: "쌀쌀한 바람에 따뜻한 것이 생각나는 11월이에요.", 12: "한 해를 마무리하는 12월이에요."}
SEASON_FOOD = {
    1: ["귤", "시금치", "굴", "꼬막", "대구"], 2: ["딸기", "시금치", "꼬막", "굴", "달래"], 3: ["냉이", "달래", "쑥", "주꾸미", "딸기"],
    4: ["두릅", "쑥", "주꾸미", "바지락", "미나리"], 5: ["마늘종", "완두콩", "참외", "멍게", "아스파라거스"], 6: ["매실", "감자", "오이", "참외", "애호박"],
    7: ["옥수수", "수박", "감자", "복숭아", "가지"], 8: ["복숭아", "포도", "옥수수", "가지", "깻잎"], 9: ["전어", "대하", "배", "사과", "고구마"],
    10: ["꽃게", "대하", "사과", "고구마", "밤"], 11: ["방어", "굴", "귤", "배추", "무"], 12: ["굴", "방어", "귤", "유자", "과메기"]}
NUM = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣"]
OUTRO = ["오늘 소개한 내용 중 하나라도 직접 해 보시면 좋겠어요. 다음 글에서 또 만나요!",
         "작은 변화가 하루를 바꾸기도 하죠. 마음에 드는 팁이 있었다면 저장해 두세요.",
         "여러분만의 방법이 있다면 댓글로 나눠 주세요. 함께 알아 가면 더 즐거워요."]

def esc(s):
    return html.escape(s, quote=True)

def load_theme(key):
    return json.load(open(os.path.join(HERE, "themes", key + ".json"), encoding="utf-8"))

def pick_entry(th, key, now, used):
    mine = used.setdefault(key, [])
    ok = [e for e in th["entries"] if not e.get("months") or now.month in e["months"]]
    fresh = [e for e in ok if e["id"] not in mine]
    if not fresh:                       # 다 썼으면 가장 오래전에 쓴 것부터 다시
        order = {i: n for n, i in enumerate(mine)}
        fresh = sorted(ok, key=lambda e: order.get(e["id"], -1))[:3]
    seasonal = [e for e in fresh if e.get("months") or e.get("seasonal")]
    e = (seasonal or fresh)[0] if seasonal and random.Random(now.isoformat()).random() < .5 else random.Random(now.strftime("%Y%m%d")).choice(fresh)
    if e["id"] in mine:
        mine.remove(e["id"])
    mine.append(e["id"])
    return e

def cover(photo_im, th, e, now, path, fonts):
    """사진 위에 제목을 얹은 대표 이미지 (1080x1080)"""
    from PIL import Image, ImageDraw, ImageFont
    fp = next((f for f in fonts if os.path.exists(f)), None)
    F = (lambda s: ImageFont.truetype(fp, s, index=0) if fp.endswith(".ttc") else ImageFont.truetype(fp, s)) if fp else None
    W = 1080
    if photo_im is not None:
        im = photo_im.copy()
        s = max(W / im.width, W / im.height)
        im = im.resize((round(im.width * s), round(im.height * s)))
        l, t = (im.width - W) // 2, (im.height - W) // 2
        im = im.crop((l, t, l + W, t + W))
    else:
        im = Image.new("RGB", (W, W), th["color"])
    shade = Image.new("L", (W, W), 0)
    sd = ImageDraw.Draw(shade)
    for y in range(W):  # 아래쪽으로 갈수록 어둡게
        sd.line([(0, y), (W, y)], fill=int(max(0, (y - W * .35) / (W * .65)) ** 1.3 * 215))
    im = Image.composite(Image.new("RGB", (W, W), "#0b0f19"), im, shade)
    if not F:
        im.save(path, "JPEG", quality=86); return
    d = ImageDraw.Draw(im)
    chip = f"{th['emoji']} {th['name']}".strip()
    cw = d.textlength(th["name"], font=F(34)) + 70
    d.rounded_rectangle([60, 60, 60 + cw, 120], 30, fill=th["color"])
    d.text((60 + cw / 2, 90), th["name"], font=F(34), fill="white", anchor="mm")
    # 제목 줄바꿈
    words, lines, cur = e["title"].split(" "), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if d.textlength(t, font=F(66)) > W - 130 and cur:
            lines.append(cur); cur = w
        else:
            cur = t
    lines.append(cur)
    lines = lines[:4]
    y = W - 125 - len(lines) * 84
    for ln in lines:
        d.text((62, y + 3), ln, font=F(66), fill=(0, 0, 0))
        d.text((60, y), ln, font=F(66), fill="white")
        y += 84
    d.text((60, W - 60), f"{now.month}월 {now.day}일", font=F(30), fill="#d7deea", anchor="ls")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    im.save(path, "JPEG", quality=86, optimize=True, progressive=True)

def build(now, base, out, fonts):
    key = WEEK[now.weekday()]
    th = load_theme(key)
    up = os.path.join(base, "theme_used.json")
    used = json.load(open(up, encoding="utf-8")) if os.path.exists(up) else {}
    e = pick_entry(th, key, now, used)
    pid = now.strftime("%Y%m%d") + "-theme"

    # 사진: 대표(제목 얹기) + 2장
    pu = os.path.join(base, "photo_used.json")
    pused = json.load(open(pu, encoding="utf-8")) if os.path.exists(pu) else []
    ph = photos.find(e["q"], 3, set(pused), pid)
    images, credits, first_im = [], [], None
    for i, p in enumerate(ph):
        rel = f"data/img/{pid}-{i + 1}.jpg"
        try:
            im = photos.download(p, os.path.join(out, rel))
        except Exception as ex:
            print(f"  사진 저장 실패: {ex}"); continue
        if first_im is None:
            first_im = im
        images.append(rel); credits.append(p); pused.append(p["id"])
    cov = f"data/img/{pid}-cover.jpg"
    try:
        cover(first_im, th, e, now, os.path.join(out, cov), fonts)
        images = [cov] + images[1:] if images else [cov]   # 첫 사진은 대표 이미지 배경으로 씀
    except Exception as ex:
        print(f"  대표 이미지 실패: {ex}")

    # 본문
    rnd = random.Random(pid)
    H, T = [], []
    def p(h_, t_=None):
        H.append(f"<p>{h_}</p>"); T.append(t_ if t_ is not None else re.sub(r"<[^>]+>", "", html.unescape(h_)))
    p(esc(MONTH_LINE[now.month] + " " + e["hook"]))
    if key == "food":
        p(esc(f"이번 달 제철 재료로는 {', '.join(SEASON_FOOD[now.month])} 등이 있어요. 장 볼 때 참고해 보세요."))
    p("")
    for i, it in enumerate(e["items"]):
        H.append(f"<h3>{NUM[i]} {esc(it['h'])}</h3>"); T.append(f"{NUM[i]} {it['h']}")
        p(esc(it["p"])); p("")
    H.append("<h3>💡 오늘의 팁</h3>"); T.append("💡 오늘의 팁")
    p(esc(e["tip"])); p("")
    p(esc(rnd.choice(OUTRO))); p("")
    if credits:
        cr = " / ".join(sorted({c["credit"] for c in credits}))
        p(f"<i>{esc('사진: ' + cr)}</i>")
    tags = e["tags"] + [th["name"].replace("·", ""), "생활정보"]
    p(esc(" ".join("#" + t for t in tags)))

    json.dump(used, open(up, "w", encoding="utf-8"), ensure_ascii=False)
    json.dump(pused[-600:], open(pu, "w", encoding="utf-8"))
    return {"id": pid, "kind": "theme", "label": f"점심 · {th['name']}", "theme": th["name"], "title": e["title"],
            "html": "\n".join(H), "text": "\n".join(T), "tags": tags, "keywords": [th["name"]], "edition": "theme",
            "created": now.isoformat(), "images": images, "entry": e["id"],
            "photo_credits": [{"credit": c["credit"], "page": c["page"]} for c in credits]}
