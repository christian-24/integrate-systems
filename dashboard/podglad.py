"""Jeden obraz PNG z podglądem reklamy albo posta: Facebook, Instagram i Story obok siebie (przycisk „Kopiuj obraz”
w osi publikacji). Tylko Pillow i czcionki systemowe; bez sieci."""
import io
import os
import re

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:            # bez Pillow: przycisk zgłasza błąd zamiast obrazu
    Image = None

FONTS = ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/System/Library/Fonts/Supplemental/Arial.ttf")
FONTS_B = ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "/System/Library/Fonts/Supplemental/Arial Bold.ttf")
BG, CARD, INK, MUTE, LINE, SUNK, BTN = (240, 242, 245), (255, 255, 255), (5, 5, 5), (101, 103, 107), (218, 221, 225), (240, 242, 245), (228, 230, 235)
IG_BLUE, AV = (55, 151, 240), (17, 17, 17)
W_FB, W_ST, GAP = 540, 405, 44


def _font(bold, size):
    for p in (FONTS_B if bold else FONTS):
        if os.path.isfile(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def parse(raw):
    """Tekst reklamy z post.md: Tekst główny, Nagłówek, Opis, Przycisk; zwykły post: sekcja z treścią albo cały tekst."""
    raw = raw or ""

    def g(k):
        m = re.search(r"\*\*" + k + r":\*\*\s*([\s\S]*?)(?=\n\*\*[^*]+:\*\*|$)", raw)
        return m.group(1).strip() if m else ""
    body = g("Tekst główny")
    if not body:
        secs = raw.split("\n## ")
        pick = next((x for x in secs if re.match(r"(Post|Tekst|Treść|Opis posta)", x, re.I)), None)
        body = re.sub(r"^[^\n]*\n", "", pick) if pick else re.sub(r"^# [^\n]*\n", "", raw)
        body = re.sub(r"^#+ .*$", "", body, flags=re.M).replace("**", "").strip()
    return {"body": body[:900], "head": g("Nagłówek"), "desc": g("Opis"), "cta": g("Przycisk") or "Wyślij wiadomość"}


def _wrap(d, text, f, width, lines):
    out = []
    for para in text.split("\n"):
        cur = ""
        for w in para.split():
            t = (cur + " " + w).strip()
            if d.textlength(t, font=f) <= width:
                cur = t
            else:
                out.append(cur)
                cur = w
        out.append(cur)
    if len(out) > lines:
        out = out[:lines]
        last = out[-1]
        while last and d.textlength(last + "… Wyświetl więcej", font=f) > width:
            last = last[:-1]
        out[-1] = last.rstrip() + "…"
    return [x for x in out if x is not None]


def _initials(name):
    ws = [w for w in re.split(r"\s+", name) if w and (w[0].isalpha() or w[0] == "&")]
    return "".join(w[0] for w in ws[:2]).upper() or "?"


def _avatar(d, x, y, r, name):
    d.ellipse((x, y, x + 2 * r, y + 2 * r), fill=AV)
    f = _font(True, int(r * 0.7))
    d.text((x + r, y + r), _initials(name), font=f, fill=(255, 255, 255), anchor="mm")


def _fit(img, w):
    return img.resize((w, int(img.height * w / img.width)), Image.LANCZOS)


def _placeholder(w, h, text):
    im = Image.new("RGB", (w, h), SUNK)
    ImageDraw.Draw(im).text((w // 2, h // 2), text, font=_font(False, 18), fill=MUTE, anchor="mm")
    return im


def _facebook(img, tx, name, ad, when):
    f, fb, fs = _font(False, 17), _font(True, 17), _font(False, 14)
    tmp = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    lines = _wrap(tmp, tx["body"] or "Tekst posta pojawi się po przygotowaniu.", f, W_FB - 32, 4)
    pic = _fit(img, W_FB)
    h = 70 + len(lines) * 24 + 12 + pic.height + (78 if ad else 0) + 48
    c = Image.new("RGB", (W_FB, h), CARD)
    d = ImageDraw.Draw(c)
    _avatar(d, 16, 14, 21, name)
    d.text((68, 18), name, font=fb, fill=INK)
    d.text((68, 42), ("Sponsorowane" if ad else when) + " · ◎", font=fs, fill=MUTE)
    d.text((W_FB - 30, 22), "···", font=fb, fill=MUTE)
    y = 70
    for i, ln in enumerate(lines):
        d.text((16, y), ln, font=f, fill=INK)
        if i == len(lines) - 1 and ln.endswith("…"):
            d.text((16 + d.textlength(ln + " ", font=f), y), "Wyświetl więcej", font=_font(True, 17), fill=MUTE)
        y += 24
    y += 12
    c.paste(pic, (0, y))
    y += pic.height
    if ad:
        d.rectangle((0, y, W_FB, y + 78), fill=SUNK)
        d.text((16, y + 14), (tx["desc"] or "Messenger")[:60], font=fs, fill=MUTE)
        d.text((16, y + 38), (tx["head"] or "")[:44], font=_font(True, 18), fill=INK)
        cta = tx["cta"]
        bw = d.textlength(cta, font=_font(True, 16)) + 28
        d.rounded_rectangle((W_FB - 16 - bw, y + 20, W_FB - 16, y + 58), 6, fill=BTN)
        d.text((W_FB - 16 - bw / 2, y + 39), cta, font=_font(True, 16), fill=INK, anchor="mm")
        y += 78
    d.line((12, y, W_FB - 12, y), fill=LINE, width=1)
    for i, t in enumerate(("Lubię to!", "Komentarz", "Udostępnij")):
        d.text((W_FB * (2 * i + 1) // 6, y + 24), t, font=_font(True, 15), fill=MUTE, anchor="mm")
    return c


def _instagram(img, tx, name, ad):
    handle = re.sub(r"[^a-z0-9ąćęłńóśźż]+", "", name.lower())[:28] or "konto"
    f, fb, fs = _font(False, 16), _font(True, 16), _font(False, 13)
    tmp = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    lines = _wrap(tmp, handle + " " + (tx["body"] or ""), f, W_FB - 32, 3)
    pic = _fit(img, W_FB)
    h = 60 + pic.height + (46 if ad else 0) + 48 + len(lines) * 22 + 14
    c = Image.new("RGB", (W_FB, h), CARD)
    d = ImageDraw.Draw(c)
    _avatar(d, 14, 12, 18, name)
    d.text((60, 13), handle, font=fb, fill=INK)
    if ad:
        d.text((60, 35), "Sponsorowane", font=fs, fill=INK)
    d.text((W_FB - 30, 16), "···", font=fb, fill=INK)
    y = 60
    c.paste(pic, (0, y))
    y += pic.height
    if ad:
        d.rectangle((0, y, W_FB, y + 46), fill=IG_BLUE)
        d.text((16, y + 23), tx["cta"], font=_font(True, 16), fill=(255, 255, 255), anchor="lm")
        d.text((W_FB - 20, y + 23), "›", font=_font(True, 22), fill=(255, 255, 255), anchor="mm")
        y += 46
    for i, t in enumerate(("♡", "◯", "➤")):
        d.text((24 + i * 42, y + 24), t, font=_font(False, 24), fill=INK, anchor="mm")
    y += 48
    for i, ln in enumerate(lines):
        if i == 0 and ln.startswith(handle):
            d.text((16, y), handle, font=fb, fill=INK)
            d.text((16 + d.textlength(handle + " ", font=fb), y), ln[len(handle):].strip(), font=f, fill=INK)
        else:
            d.text((16, y), ln, font=f, fill=INK)
        y += 22
    return c


def _story(img, tx, name, ad):
    h = int(W_ST * 16 / 9)
    r = max(W_ST / img.width, h / img.height)
    im = img.resize((int(img.width * r) + 1, int(img.height * r) + 1), Image.LANCZOS)
    x0, y0 = (im.width - W_ST) // 2, (im.height - h) // 2
    c = im.crop((x0, y0, x0 + W_ST, y0 + h)).convert("RGB")
    shade = Image.new("L", (1, 90), 0)
    for y in range(90):
        shade.putpixel((0, y), int(120 * (1 - y / 90)))
    c.paste(Image.new("RGB", (W_ST, 90), (0, 0, 0)), (0, 0), shade.resize((W_ST, 90)))
    d = ImageDraw.Draw(c)
    d.rounded_rectangle((10, 10, W_ST - 10, 13), 2, fill=(170, 170, 170))
    d.rounded_rectangle((10, 10, W_ST // 3, 13), 2, fill=(255, 255, 255))
    _avatar(d, 12, 24, 16, name)
    d.text((52, 30), name[:26], font=_font(True, 14), fill=(255, 255, 255))
    if ad:
        d.text((52, 48), "Sponsorowane", font=_font(False, 12), fill=(235, 235, 235))
        cta = tx["cta"]
        f = _font(True, 15)
        bw = d.textlength(cta, font=f) + 40
        d.rounded_rectangle((W_ST / 2 - bw / 2, h - 70, W_ST / 2 + bw / 2, h - 30), 20, fill=(255, 255, 255))
        d.text((W_ST / 2, h - 50), cta, font=f, fill=INK, anchor="mm")
    return c


def render(folder, name, title, ad, when):
    """PNG (bytes) z trzema podglądami dla folderu posta/reklamy."""
    if Image is None:
        raise RuntimeError("brak Pillow na serwerze")
    raw = ""
    if folder and os.path.isfile(os.path.join(folder, "post.md")):
        with open(os.path.join(folder, "post.md"), encoding="utf-8", errors="replace") as f:
            raw = f.read(20000)
    tx = parse(raw)
    feed = next((os.path.join(folder, n) for n in ("grafika.png", "grafika.jpg") if folder and os.path.isfile(os.path.join(folder, n))), None)
    story = os.path.join(folder, "grafika-story.png") if folder and os.path.isfile(os.path.join(folder, "grafika-story.png")) else feed
    fimg = Image.open(feed).convert("RGB") if feed else _placeholder(W_FB, 675, "Grafika jeszcze nie jest gotowa")
    simg = Image.open(story).convert("RGB") if story else _placeholder(W_ST, 720, "Grafika jeszcze nie jest gotowa")
    cards = [("Facebook", _facebook(fimg, tx, name, ad, when)), ("Instagram", _instagram(fimg, tx, name, ad)),
             ("Story", _story(simg, tx, name, ad))]
    top = 96
    H = top + 34 + max(c.height for _, c in cards) + GAP
    W = GAP + sum(c.width + GAP for _, c in cards)
    out = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(out)
    title = re.sub(r"^(Przygotuj|Opublikuj)\s+(reklamę|reklame|post|film)?\s*", "", title or "").strip() or "Podgląd"
    d.text((GAP, 30), title[:110], font=_font(True, 26), fill=INK)
    d.text((GAP, 64), "Podgląd: tak będzie wyglądać na Facebooku, Instagramie i w Story", font=_font(False, 16), fill=MUTE)
    x = GAP
    for label, c in cards:
        d.text((x, top), label, font=_font(True, 16), fill=MUTE)
        out.paste(c, (x, top + 30))
        d.rectangle((x - 1, top + 29, x + c.width, top + 30 + c.height), outline=LINE)
        x += c.width + GAP
    buf = io.BytesIO()
    out.save(buf, "PNG", optimize=True)
    return buf.getvalue()
