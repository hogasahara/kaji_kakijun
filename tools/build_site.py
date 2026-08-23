#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GitHub Pages用の静的サイトを docs/ に生成する

  docs/index.html          索引(学年別・読み順、読み仮名検索つき)
  docs/cards/<code>.html   カードページ(一画分解+タップ/自動再生プレイヤー)
  docs/assignments/        「今回の課題」ページ(make_assignment.py が追加、
                           一覧 index.html はここで再生成)

iPad Safari / スマホで見られるようレスポンシブ。個人情報(塾名等)は載せない。
"""
import html
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from kanjicards import DATA_DIR, DOCS_DIR
from kanjicards.kanjivg import code_of, load_strokes
from kanjicards.meta import (display_readings, kata_to_hira, load_grades,
                             load_meta, reading_sort_key)
from kanjicards.render import SCREEN_CSS, card_section, frames_row, readings_html

CARD_GRADES = ["1", "2", "3", "4", "5", "6"]  # カードページを作る学年(小学校全配当)

ATTRIBUTION = (
    '筆順データ: <a href="https://github.com/KanjiVG/kanjivg">KanjiVG</a> (CC BY-SA 3.0) / '
    '読み・画数: <a href="https://www.edrdg.org/wiki/index.php/KANJIDIC_Project">KANJIDIC2</a> (EDRDG, CC BY-SA 4.0)'
)

PLAYER_JS = r'''
(function(){
  var S = window.CARD_DATA.strokes, N = window.CARD_DATA.numpos;
  var svg = document.getElementById('player-svg');
  var NS = 'http://www.w3.org/2000/svg';
  var paths = [], overlay = null;
  S.forEach(function(d){
    var p = document.createElementNS(NS, 'path');
    p.setAttribute('d', d);
    p.setAttribute('fill', 'none');
    p.setAttribute('stroke-linecap', 'round');
    p.setAttribute('stroke-linejoin', 'round');
    svg.appendChild(p);
    paths.push(p);
  });
  var step = 0; // 0=完成形, 1..n=その画まで
  var n = S.length, timer = null;
  var label = document.getElementById('player-label');
  function clearOverlay(){ if (overlay) { overlay.remove(); overlay = null; } }
  function mark(i){
    clearOverlay();
    var pos = N[String(i)];
    if (!pos) return;
    overlay = document.createElementNS(NS, 'g');
    var c = document.createElementNS(NS, 'circle');
    c.setAttribute('cx', pos[0]+2); c.setAttribute('cy', pos[1]-3);
    c.setAttribute('r', 7.5); c.setAttribute('fill', '#e03131');
    var t = document.createElementNS(NS, 'text');
    t.setAttribute('x', pos[0]+2); t.setAttribute('y', pos[1]-3);
    t.setAttribute('font-size', 10); t.setAttribute('font-weight', 'bold');
    t.setAttribute('fill', '#fff'); t.setAttribute('text-anchor', 'middle');
    t.setAttribute('dominant-baseline', 'central'); t.setAttribute('font-family', 'sans-serif');
    t.textContent = i;
    overlay.appendChild(c); overlay.appendChild(t);
    svg.appendChild(overlay);
  }
  function render(animate){
    paths.forEach(function(p, idx){
      var i = idx + 1;
      p.style.transition = '';
      p.style.strokeDasharray = '';
      p.style.strokeDashoffset = '';
      if (step === 0) {
        p.setAttribute('stroke', '#222'); p.setAttribute('stroke-width', 4);
        p.style.visibility = 'visible';
      } else if (i < step) {
        p.setAttribute('stroke', '#b9b3a6'); p.setAttribute('stroke-width', 4);
        p.style.visibility = 'visible';
      } else if (i === step) {
        p.setAttribute('stroke', '#e03131'); p.setAttribute('stroke-width', 5);
        p.style.visibility = 'visible';
        if (animate) {
          var L = p.getTotalLength();
          p.style.strokeDasharray = L;
          p.style.strokeDashoffset = L;
          p.getBoundingClientRect();
          p.style.transition = 'stroke-dashoffset .6s ease';
          p.style.strokeDashoffset = '0';
        }
      } else {
        p.style.visibility = 'hidden';
      }
    });
    if (step === 0) { clearOverlay(); label.textContent = 'かんせい(' + n + 'かく)'; }
    else { mark(step); label.textContent = step + 'かくめ / ' + n + 'かく'; }
  }
  function stopAuto(){ if (timer) { clearInterval(timer); timer = null;
    document.getElementById('btn-auto').textContent = '▶ じどう'; } }
  document.getElementById('btn-next').addEventListener('click', function(){
    stopAuto(); step = (step >= n) ? 0 : step + 1; render(true);
  });
  document.getElementById('btn-prev').addEventListener('click', function(){
    stopAuto(); step = (step <= 0) ? n : step - 1; render(false);
  });
  document.getElementById('btn-reset').addEventListener('click', function(){
    stopAuto(); step = 0; render(false);
  });
  document.getElementById('btn-auto').addEventListener('click', function(){
    if (timer) { stopAuto(); return; }
    this.textContent = '⏸ とめる';
    step = 1; render(true);
    timer = setInterval(function(){
      if (step >= n) { stopAuto(); return; }
      step += 1; render(true);
    }, 900);
  });
  svg.addEventListener('click', function(){
    stopAuto(); step = (step >= n) ? 0 : step + 1; render(true);
  });
  render(false);
})();
'''

PLAYER_CSS = '''
.player { background: #fff; border-radius: 12px; padding: 14px 16px; margin-bottom: 18px; box-shadow: 0 1px 3px rgba(0,0,0,.08); text-align: center; }
.player svg { max-width: min(70vw, 340px); height: auto; touch-action: manipulation; }
.player .ctrl { display: flex; gap: 8px; justify-content: center; flex-wrap: wrap; margin-top: 8px; }
.player button { font-size: 16px; padding: 10px 16px; border-radius: 10px; border: 1px solid #d8cfae; background: #fffdf5; color: #333; cursor: pointer; }
.player button:active { background: #f0e8d0; }
#player-label { font-size: 14px; color: #777; margin-top: 6px; }
.player .hint { font-size: 12px; color: #999; margin-top: 4px; }
'''

CELL_BG_PLAYER = '''<rect x="1" y="1" width="107" height="107" rx="6" fill="#fffdf5" stroke="#e0d8c0" stroke-width="1.5"/><line x1="54.5" y1="4" x2="54.5" y2="105" stroke="#d8cfae" stroke-width="1" stroke-dasharray="4 4"/><line x1="4" y1="54.5" x2="105" y2="54.5" stroke="#d8cfae" stroke-width="1" stroke-dasharray="4 4"/>'''


def page(title, body, css_extra="", head_extra="", depth=0):
    return f'''<!DOCTYPE html>
<html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<style>{SCREEN_CSS}{css_extra}</style>{head_extra}</head><body>
{body}
<footer style="font-size:11px;color:#999;margin-top:24px;">{ATTRIBUTION}</footer>
</body></html>'''


def build_card_page(ch, grade):
    strokes, numpos = load_strokes(ch)
    on, kun = display_readings(ch)
    n = len(strokes)
    data = json.dumps({"strokes": strokes,
                       "numpos": {str(k): v for k, v in numpos.items()}},
                      ensure_ascii=False)
    yomi = readings_html(on, kun)
    body = f'''<p style="margin:0 0 10px;"><a href="../index.html">← いちらんへ</a></p>
<section class="kanji" style="margin-bottom:12px;">
<h1 style="display:flex;align-items:baseline;gap:10px;flex-wrap:wrap;margin:0;">
<span class="big" style="font-size:44px;">{html.escape(ch)}</span>
<span class="count">({n}画)</span><span class="grade">小{grade}</span>
<span class="yomis">{yomi}</span></h1>
</section>
<div class="player">
<svg id="player-svg" viewBox="0 0 109 109" width="340" height="340" xmlns="http://www.w3.org/2000/svg">{CELL_BG_PLAYER}</svg>
<div id="player-label"></div>
<div class="ctrl">
<button id="btn-prev">◀ まえへ</button>
<button id="btn-next">つぎへ ▶</button>
<button id="btn-auto">▶ じどう</button>
<button id="btn-reset">はじめから</button>
</div>
<div class="hint">マスをタップしても つぎの画にすすむよ</div>
</div>
<h2 style="font-size:16px;">一画ずつ</h2>
<section class="kanji">
{frames_row(strokes, numpos)}
</section>
<script>window.CARD_DATA = {data};</script>
<script>{PLAYER_JS}</script>'''
    return page(f"{ch} の書き順", body, css_extra=PLAYER_CSS)


def build_index(grades, meta):
    """索引: 大きな検索窓+全学年フラットな読み順グリッド(学年チップは絞り込みのみ)"""
    all_chars = []
    for g in CARD_GRADES:
        all_chars.extend((ch, g) for ch in grades[g])
    all_chars.sort(key=lambda t: reading_sort_key(t[0], meta))
    cells = []
    for ch, g in all_chars:
        on, kun = display_readings(ch, max_on=2, max_kun=2)
        yomi_disp = "・".join((on + kun)[:2])
        # 検索用: 全読みをひらがなで(音はカタカナのまま+ひらがな化の両方)
        m = meta[ch]
        keys = set()
        for r in m["on"]:
            r = r.strip("-")
            keys.add(r)
            keys.add(kata_to_hira(r))
        for r in m["kun"]:
            r = r.strip("-")
            keys.add(r.replace(".", ""))
            keys.add(r.split(".")[0])
        keys.add(ch)
        cells.append(
            f'<a class="tile" href="cards/{code_of(ch)}.html" data-g="{g}" data-k="{html.escape(" ".join(sorted(keys)))}">'
            f'<span class="tg">小{g}</span>'
            f'<span class="tch">{html.escape(ch)}</span><span class="tyo">{html.escape(yomi_disp)}</span></a>')
    chips = '<button class="chip on" data-g="">すべて</button>' + "".join(
        f'<button class="chip" data-g="{g}">小{g}</button>' for g in CARD_GRADES)
    body = f'''<div class="head">
<h1>漢字書き順カード <a class="alink" href="assignments/index.html">今回の課題 →</a></h1>
<input id="q" type="search" placeholder="よみがな か 漢字で さがす(例: うん、運)" autocomplete="off" autofocus>
<div class="chips">{chips}</div>
</div>
<div class="grid">{"".join(cells)}</div>
<p class="note" id="nohit" style="display:none;">みつかりませんでした</p>
<script>
var q = document.getElementById('q');
var tiles = Array.prototype.slice.call(document.querySelectorAll('.tile'));
var chips = Array.prototype.slice.call(document.querySelectorAll('.chip'));
var gsel = '';
function h2h(s){{ return s.replace(/[\\u30a1-\\u30f6]/g, function(c){{ return String.fromCharCode(c.charCodeAt(0)-0x60); }}); }}
function apply(){{
  var v = h2h(q.value.trim());
  var hit = 0;
  tiles.forEach(function(t){{
    var ok = (!v || h2h(t.dataset.k).indexOf(v) !== -1) && (!gsel || t.dataset.g === gsel);
    t.style.display = ok ? '' : 'none';
    if (ok) hit++;
  }});
  document.getElementById('nohit').style.display = hit ? 'none' : '';
}}
q.addEventListener('input', apply);
q.addEventListener('keydown', function(e){{
  if (e.key !== 'Enter') return;
  var first = tiles.filter(function(t){{ return t.style.display !== 'none'; }})[0];
  if (first && q.value.trim()) location.href = first.getAttribute('href');
}});
chips.forEach(function(c){{
  c.addEventListener('click', function(){{
    gsel = c.dataset.g;
    chips.forEach(function(x){{ x.className = 'chip' + (x === c ? ' on' : ''); }});
    apply();
  }});
}});
</script>'''
    css = '''
.head { position: sticky; top: 0; background: #f6f2e9; padding: 4px 0 10px; z-index: 5; }
h1 { font-size: 18px; margin: 0 0 8px; display: flex; align-items: baseline; justify-content: space-between; }
.alink { font-size: 13px; color: #5c7aa2; text-decoration: none; font-weight: normal; }
#q { display: block; width: 100%; font-size: 22px; padding: 14px 16px; border-radius: 14px; border: 2px solid #d8cfae; box-sizing: border-box; background: #fff; box-shadow: 0 1px 4px rgba(0,0,0,.08); }
#q:focus { outline: none; border-color: #a25c7a; }
.chips { display: flex; gap: 6px; margin-top: 8px; flex-wrap: wrap; }
.chip { font-size: 13px; padding: 5px 12px; border-radius: 999px; border: 1px solid #d8cfae; background: #fff; color: #555; cursor: pointer; }
.chip.on { background: #7aa25c; border-color: #7aa25c; color: #fff; }
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(76px, 1fr)); gap: 8px; margin-top: 10px; }
.tile { position: relative; background: #fff; border-radius: 10px; padding: 8px 4px; text-align: center; text-decoration: none; color: #333; box-shadow: 0 1px 3px rgba(0,0,0,.08); }
.tile .tg { position: absolute; top: 3px; right: 5px; font-size: 9px; color: #b0a890; }
.tile .tch { display: block; font-size: 30px; }
.tile .tyo { display: block; font-size: 10px; color: #888; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
'''
    return page("漢字書き順カード", body, css_extra=css)


def build_assignments_index():
    """data/assignments.json → docs/assignments/index.html"""
    manifest_path = os.path.join(DATA_DIR, "assignments.json")
    entries = []
    if os.path.exists(manifest_path):
        with open(manifest_path, encoding="utf-8") as f:
            entries = json.load(f)
    items = []
    for e in sorted(entries, key=lambda e: e["name"], reverse=True):
        kanji = html.escape("".join(e["kanji"]))
        pdf = f' / <a href="{html.escape(e["name"])}.pdf">PDF</a>' if e.get("pdf") else ""
        items.append(
            f'<li><a href="{html.escape(e["name"])}.html">{html.escape(e["date"])}</a>'
            f' — {kanji}({len(e["kanji"])}字){pdf}</li>')
    listing = f'<ul class="alist">{"".join(items)}</ul>' if items else '<p class="note">まだ課題がありません。</p>'
    body = f'''<p style="margin:0 0 10px;"><a href="../index.html">← いちらんへ</a></p>
<h1>今回の課題</h1>
<p class="note">ドリルの写真から作った漢字セット。新しい順。</p>
{listing}'''
    css = '.alist { padding-left: 20px; } .alist li { margin-bottom: 8px; background: #fff; border-radius: 8px; padding: 10px 14px; list-style-position: inside; box-shadow: 0 1px 3px rgba(0,0,0,.08); }'
    return page("今回の課題", body, css_extra=css)


def build_assignment_page(name, date, chars):
    """課題1件のiPad用ページ(出典などの個人情報は載せない)"""
    meta = load_meta()
    sections = []
    for ch in chars:
        strokes, numpos = load_strokes(ch, fetch_if_missing=True)
        on, kun = display_readings(ch)
        m = meta.get(ch)
        grade = m["grade"] if m and m["grade"] <= 6 else None
        link = f"../cards/{code_of(ch)}.html" if m and str(m["grade"]) in CARD_GRADES else None
        sections.append(card_section(ch, strokes, numpos, on, kun, grade=grade, link=link))
    body = f'''<p style="margin:0 0 10px;"><a href="index.html">← 課題いちらんへ</a></p>
<h1>{html.escape(date)} の課題({len(chars)}字)</h1>
<p class="note">字をタップするとカードページ(アニメーションつき)が開きます。<a href="{html.escape(name)}.pdf">印刷用PDF</a></p>
{"".join(sections)}'''
    return page(f"{date} の課題", body)


def write(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def main():
    grades = load_grades()
    meta = load_meta()

    cards_dir = os.path.join(DOCS_DIR, "cards")
    os.makedirs(cards_dir, exist_ok=True)
    count = 0
    for g in CARD_GRADES:
        for ch in grades[g]:
            write(os.path.join(cards_dir, code_of(ch) + ".html"), build_card_page(ch, g))
            count += 1

    write(os.path.join(DOCS_DIR, "index.html"), build_index(grades, meta))
    write(os.path.join(DOCS_DIR, "assignments", "index.html"), build_assignments_index())
    # Jekyll処理を無効化(_で始まるファイル対策・高速化)
    open(os.path.join(DOCS_DIR, ".nojekyll"), "w").close()
    print(f"OK: docs/ カード{count}枚 + 索引 + 課題一覧")


if __name__ == "__main__":
    main()
