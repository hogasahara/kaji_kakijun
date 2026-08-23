# -*- coding: utf-8 -*-
"""一画分解コマ(SVG)とカードHTMLのレンダリング — 見本 kakijun_sample.html 準拠

配色・線幅は承認済みの見本に合わせる。モノクロ印刷でも判別できるよう、
「いま書く画」は色(赤)に加えて太さ(5 vs 4)と濃度(#e03131は#b9b3a6より暗い)で差をつけている。
"""
import html as _html

# 見本と同じマス背景(十字リーダー入り)
CELL_BG = '''<rect x="1" y="1" width="107" height="107" rx="6" fill="#fffdf5" stroke="#e0d8c0" stroke-width="1.5"/>
<line x1="54.5" y1="4" x2="54.5" y2="105" stroke="#d8cfae" stroke-width="1" stroke-dasharray="4 4"/>
<line x1="4" y1="54.5" x2="105" y2="54.5" stroke="#d8cfae" stroke-width="1" stroke-dasharray="4 4"/>'''

COL_DONE = "#b9b3a6"   # 書き終えた画(グレー)
COL_NOW = "#e03131"    # いま書く画(赤・太)
COL_FULL = "#222"      # 完成形


def frame_svg(strokes, numpos, upto, size="110"):
    """upto画目までを描くコマSVG。uptoの画は赤、それ以前はグレー。0なら完成形。

    size は "110"(px) や "30mm" などSVGのwidth/height属性値。
    """
    parts = [f'<svg viewBox="0 0 109 109" width="{size}" height="{size}" xmlns="http://www.w3.org/2000/svg">', CELL_BG]
    if upto == 0:  # 完成形
        for d in strokes:
            parts.append(f'<path d="{d}" fill="none" stroke="{COL_FULL}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>')
    else:
        for i, d in enumerate(strokes[:upto], 1):
            if i < upto:
                col, w = COL_DONE, 4
            else:
                col, w = COL_NOW, 5
            parts.append(f'<path d="{d}" fill="none" stroke="{col}" stroke-width="{w}" stroke-linecap="round" stroke-linejoin="round"/>')
        if upto in numpos:
            x, y = numpos[upto]
            parts.append(f'<circle cx="{x+2:.1f}" cy="{y-3:.1f}" r="7.5" fill="{COL_NOW}"/>')
            parts.append(f'<text x="{x+2:.1f}" y="{y-3:.1f}" font-size="10" font-weight="bold" fill="#fff" text-anchor="middle" dominant-baseline="central" font-family="sans-serif">{upto}</text>')
    parts.append("</svg>")
    return "".join(parts)


def readings_html(on, kun):
    """読み仮名行: 音=カタカナ、訓=ひらがな"""
    parts = []
    if on:
        parts.append(f'<span class="yomi on"><span class="tag">音</span>{_html.escape("・".join(on))}</span>')
    if kun:
        parts.append(f'<span class="yomi kun"><span class="tag">訓</span>{_html.escape("・".join(kun))}</span>')
    return "".join(parts)


def frames_row(strokes, numpos, size="110", label_complete="かんせい"):
    """完成形+1画目〜n画目のコマ列HTML"""
    n = len(strokes)
    cells = [f'<div class="cell"><div class="lbl">{label_complete}</div>{frame_svg(strokes, numpos, 0, size)}</div>']
    for i in range(1, n + 1):
        cells.append(f'<div class="cell"><div class="lbl">{i}かくめ</div>{frame_svg(strokes, numpos, i, size)}</div>')
    return f'<div class="row">{"".join(cells)}</div>'


def card_section(ch, strokes, numpos, on, kun, grade=None, size="110",
                 link=None, heading_tag="h2"):
    """1字ぶんのカードセクション(見出し+読み+コマ列)"""
    n = len(strokes)
    big = _html.escape(ch)
    if link:
        big = f'<a href="{_html.escape(link)}">{big}</a>'
    grade_html = f'<span class="grade">小{grade}</span>' if grade else '<span class="grade out">配当外</span>'
    yomi = readings_html(on, kun)
    return f'''<section class="kanji">
<{heading_tag}><span class="big">{big}</span><span class="count">({n}画)</span>{grade_html}<span class="yomis">{yomi}</span></{heading_tag}>
{frames_row(strokes, numpos, size)}
</section>'''


# 見本準拠の共通スタイル(画面用)
SCREEN_CSS = '''
body { font-family: "Hiragino Kaku Gothic ProN", "Yu Gothic", "Noto Sans JP", sans-serif; background: #f6f2e9; margin: 0; padding: 16px; color: #333; }
h1 { font-size: 20px; margin: 0 0 4px; }
p.note { font-size: 13px; color: #777; margin: 0 0 16px; }
section.kanji { background: #fff; border-radius: 12px; padding: 14px 16px; margin-bottom: 18px; box-shadow: 0 1px 3px rgba(0,0,0,.08); }
section.kanji h2, section.kanji h3 { margin: 0 0 8px; display: flex; align-items: baseline; gap: 8px; flex-wrap: wrap; }
.big { font-size: 34px; }
.big a { color: inherit; text-decoration: none; }
.count { font-size: 14px; color: #888; font-weight: normal; }
.grade { font-size: 12px; color: #fff; background: #7aa25c; border-radius: 8px; padding: 2px 8px; font-weight: normal; align-self: center; }
.grade.out { background: #b08650; }
.yomis { display: flex; gap: 10px; flex-wrap: wrap; font-weight: normal; font-size: 15px; }
.yomi .tag { font-size: 11px; color: #fff; border-radius: 6px; padding: 1px 5px; margin-right: 4px; vertical-align: 1px; }
.yomi.on .tag { background: #5c7aa2; }
.yomi.kun .tag { background: #a25c7a; }
.row { display: flex; flex-wrap: wrap; gap: 8px; }
.cell { text-align: center; }
.cell .lbl { font-size: 11px; color: #999; margin-bottom: 2px; }
@media (max-width: 520px) { .cell svg { width: 86px; height: 86px; } .big { font-size: 28px; } }
'''
