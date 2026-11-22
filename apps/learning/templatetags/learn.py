import random

from django import template
from django.utils.html import format_html, mark_safe

register = template.Library()

SHADES = ["#2F6FDB", "#E8A317", "#7A4FD6"]


@register.filter
def shuffled(seq):
    """FR-LRN-7: порядок вариантов перемешивается при каждом показе."""
    items = list(seq or [])
    random.shuffle(items)
    return items


@register.simple_tag
def visual_model(model):
    """Визуальные модели 11.9: полоска дроби, столбчатая модель, весы."""
    if not model:
        return ""
    kind = model.get("kind")
    if kind == "strip":
        n = int(model.get("n", 1))
        parts = [int(p) for p in model.get("parts", [])]
        w, h = 560, 64
        cw = w / n
        cells = []
        idx = 0
        colors = []
        for pi, cnt in enumerate(parts):
            colors += [SHADES[pi % len(SHADES)]] * cnt
        for i in range(n):
            fill = colors[i] if i < len(colors) else "#FFFFFF"
            cells.append(
                f'<rect x="{i * cw + 2:.1f}" y="2" width="{cw - 4:.1f}" height="{h - 4}" rx="8" '
                f'fill="{fill}" stroke="#2B2B33" stroke-width="2"/>'
            )
            idx += 1
        label = f"Полоска из {n} равных частей" + (f", закрашено: {' и '.join(map(str, parts))}" if parts else "")
        return mark_safe(
            f'<svg class="vmodel" viewBox="0 0 {w} {h}" role="img" aria-label="{label}">{"".join(cells)}</svg>'
        )
    if kind == "bar":
        segs = model.get("segments", [])
        w = 560
        sw = w / max(1, len(segs))
        out = []
        for i, s in enumerate(segs):
            lbl = s.get("label", "")
            unknown = "?" in lbl
            stroke = "#E8A317" if unknown else "#2F6FDB"
            out.append(
                f'<rect x="{i * sw + 2:.0f}" y="6" width="{sw - 4:.0f}" height="52" rx="8" fill="#E6EFFD" '
                f'stroke="{stroke}" stroke-width="3"/>'
                f'<text x="{i * sw + sw / 2:.0f}" y="38" text-anchor="middle" font-size="18" font-weight="700" fill="#2B2B33">{lbl}</text>'
            )
        return mark_safe(f'<svg class="vmodel" viewBox="0 0 {w} 64" role="img" aria-label="Столбчатая модель">{"".join(out)}</svg>')
    if kind == "scales":
        from django.templatetags.static import static
        return format_html('<img class="vmodel" style="max-width:220px" src="{}" alt="Весы">', static("img/scales.svg"))
    return ""


@register.filter
def get_item(d, key):
    try:
        return d.get(key)
    except AttributeError:
        return None


@register.simple_tag
def tiles_for(word, extra=2):
    letters = list(word.lower().replace(" ", ""))
    pool = "abcdeghiklmnoprstuw"
    for _ in range(extra):
        letters.append(random.choice([c for c in pool if c not in letters] or pool))
    random.shuffle(letters)
    return letters
