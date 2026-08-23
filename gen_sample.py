# -*- coding: utf-8 -*-
"""KanjiVGから一画ずつ分解した筆順コマを生成する"""
import re, os, html

KANJI_DIR = os.path.expanduser("~/kanjivg/kanji")

def load_kanji(ch):
    code = format(ord(ch), "05x")
    path = os.path.join(KANJI_DIR, code + ".svg")
    with open(path, encoding="utf-8") as f:
        src = f.read()
    # 画のパス(d属性)を順に取得 — StrokePaths グループ内の path 要素は文書順=筆順
    strokes = re.findall(r'<path[^>]*\bd="([^"]+)"', src)
    # 番号の位置(StrokeNumbers の text 要素)
    nums = re.findall(r'<text transform="matrix\([^)]*?([\d.]+)\s+([\d.]+)\)"[^>]*>(\d+)</text>', src)
    numpos = {int(n): (float(x), float(y)) for x, y, n in nums}
    return strokes, numpos

CELL_BG = '''<rect x="1" y="1" width="107" height="107" rx="6" fill="#fffdf5" stroke="#e0d8c0" stroke-width="1.5"/>
<line x1="54.5" y1="4" x2="54.5" y2="105" stroke="#d8cfae" stroke-width="1" stroke-dasharray="4 4"/>
<line x1="4" y1="54.5" x2="105" y2="54.5" stroke="#d8cfae" stroke-width="1" stroke-dasharray="4 4"/>'''

def frame_svg(strokes, numpos, upto, size=110):
    """upto画目までを描く。upto画目は赤、それ以前はグレー。0なら完成形(全部黒)。"""
    parts = [f'<svg viewBox="0 0 109 109" width="{size}" height="{size}" xmlns="http://www.w3.org/2000/svg">', CELL_BG]
    if upto == 0:  # 完成形
        for d in strokes:
            parts.append(f'<path d="{d}" fill="none" stroke="#222" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>')
    else:
        for i, d in enumerate(strokes[:upto], 1):
            if i < upto:
                col, w = "#b9b3a6", 4
            else:
                col, w = "#e03131", 5
            parts.append(f'<path d="{d}" fill="none" stroke="{col}" stroke-width="{w}" stroke-linecap="round" stroke-linejoin="round"/>')
        if upto in numpos:
            x, y = numpos[upto]
            parts.append(f'<circle cx="{x+2:.1f}" cy="{y-3:.1f}" r="7.5" fill="#e03131"/>')
            parts.append(f'<text x="{x+2:.1f}" y="{y-3:.1f}" font-size="10" font-weight="bold" fill="#fff" text-anchor="middle" dominant-baseline="central" font-family="sans-serif">{upto}</text>')
    parts.append("</svg>")
    return "".join(parts)

def kanji_row(ch):
    strokes, numpos = load_kanji(ch)
    n = len(strokes)
    cells = []
    # 完成形を先頭に
    cells.append(f'<div class="cell"><div class="lbl">かんせい</div>{frame_svg(strokes, numpos, 0)}</div>')
    for i in range(1, n + 1):
        cells.append(f'<div class="cell"><div class="lbl">{i}かくめ</div>{frame_svg(strokes, numpos, i)}</div>')
    return f'''<section class="kanji">
<h2><span class="big">{html.escape(ch)}</span><span class="count">({n}画)</span></h2>
<div class="row">{"".join(cells)}</div>
</section>'''

SAMPLE = ["右", "左", "水", "空"]

body = "\n".join(kanji_row(c) for c in SAMPLE)

page = f'''<!DOCTYPE html>
<html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>書き順 見本</title>
<style>
body {{ font-family: "Hiragino Kaku Gothic ProN", "Yu Gothic", sans-serif; background: #f6f2e9; margin: 0; padding: 24px; color: #333; }}
h1 {{ font-size: 20px; margin: 0 0 4px; }}
p.note {{ font-size: 13px; color: #777; margin: 0 0 20px; }}
section.kanji {{ background: #fff; border-radius: 12px; padding: 14px 16px; margin-bottom: 18px; box-shadow: 0 1px 3px rgba(0,0,0,.08); }}
h2 {{ margin: 0 0 8px; display: flex; align-items: baseline; gap: 8px; }}
h2 .big {{ font-size: 34px; }}
h2 .count {{ font-size: 14px; color: #888; font-weight: normal; }}
.row {{ display: flex; flex-wrap: wrap; gap: 8px; }}
.cell {{ text-align: center; }}
.cell .lbl {{ font-size: 11px; color: #999; margin-bottom: 2px; }}
</style></head><body>
<h1>書き順の見本(一画ずつ分解)</h1>
<p class="note">赤が「いま書く画」、グレーが「もう書いた画」。番号は書き始めの位置。筆順データ: KanjiVG</p>
{body}
</body></html>'''

out = os.path.expanduser("~/kakijun/kakijun_sample.html")
with open(out, "w", encoding="utf-8") as f:
    f.write(page)
print("OK", out)
