#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""漢字リスト → B4印刷用PDF + iPad用「今回の課題」ページ を一括生成

使い方:
  python3 tools/make_assignment.py 右左水空 --source "○○塾 漢字ドリル p.12"

生成物:
  docs/assignments/<日付[-slug]>.pdf   B4縦の印刷用PDF(出典・日付入り)
  docs/assignments/<日付[-slug]>.html  iPad用ページ(出典は載せない)
  docs/assignments/index.html          課題一覧(再生成)
  data/assignments.json                課題マニフェスト

- 重複した漢字は1枚にまとめる(入力順は保持)
- 小1〜3配当外の漢字は警告を出し、KanjiVGから即席でSVGを取得して含める
- PDF生成はChromium headlessを使用。見つからない場合は印刷用HTMLを残すので
  ブラウザで開いて手動でPDF保存する
"""
import argparse
import datetime
import html
import json
import os
import re
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from kanjicards import DATA_DIR, DOCS_DIR, ROOT
from kanjicards.kanjivg import load_strokes, svg_path_for
from kanjicards.meta import display_readings, load_meta
from kanjicards.render import card_section

PRINT_CSS = '''
@page { size: 257mm 364mm; margin: 12mm 12mm 14mm; }
html, body { margin: 0; padding: 0; }
body { font-family: "Noto Sans CJK JP", "Hiragino Kaku Gothic ProN", "Yu Gothic", sans-serif; color: #333; }
header { display: flex; justify-content: space-between; align-items: baseline; border-bottom: 2px solid #b9b3a6; padding-bottom: 3mm; margin-bottom: 5mm; }
header .title { font-size: 15pt; font-weight: bold; }
header .fields { font-size: 11pt; display: flex; gap: 8mm; }
header .src .line { display: inline-block; min-width: 60mm; border-bottom: 1px solid #999; padding: 0 2mm; }
section.kanji { break-inside: avoid; page-break-inside: avoid; margin-bottom: 6mm; }
section.kanji h2 { margin: 0 0 2mm; display: flex; align-items: baseline; gap: 4mm; font-size: 13pt; }
.big { font-size: 26pt; }
.count { font-size: 11pt; color: #666; font-weight: normal; }
.grade { font-size: 9pt; color: #fff; background: #7aa25c; border-radius: 2mm; padding: 0.5mm 2mm; font-weight: normal; align-self: center; }
.grade.out { background: #b08650; }
.yomis { display: flex; gap: 5mm; flex-wrap: wrap; font-weight: normal; font-size: 12pt; }
.yomi .tag { font-size: 8pt; color: #fff; border-radius: 1.5mm; padding: 0.3mm 1.5mm; margin-right: 1.5mm; vertical-align: 1pt; }
.yomi.on .tag { background: #5c7aa2; }
.yomi.kun .tag { background: #a25c7a; }
.row { display: grid; grid-template-columns: repeat(5, 43mm); gap: 2.5mm; }
.cell { text-align: center; }
.cell .lbl { font-size: 8pt; color: #888; margin-bottom: 0.5mm; }
footer { font-size: 7pt; color: #999; margin-top: 4mm; }
'''

CHROMIUM_CANDIDATES = [
    os.environ.get("CHROMIUM"),
    "/opt/pw-browsers/chromium",
    shutil.which("chromium"),
    shutil.which("chromium-browser"),
    shutil.which("google-chrome"),
]


def find_chromium():
    for c in CHROMIUM_CANDIDATES:
        if c and os.path.exists(c):
            return c
    return None


def build_print_html(chars, date, source):
    meta = load_meta()
    sections = []
    for ch in chars:
        strokes, numpos = load_strokes(ch, fetch_if_missing=True)
        on, kun = display_readings(ch)
        m = meta.get(ch)
        grade = m["grade"] if m and m["grade"] <= 6 else None
        sections.append(card_section(ch, strokes, numpos, on, kun, grade=grade, size="43mm"))
    src = html.escape(source) if source else '<span class="line">&nbsp;</span>'
    return f'''<!DOCTYPE html>
<html lang="ja"><head><meta charset="utf-8"><title>漢字書き順プリント {html.escape(date)}</title>
<style>{PRINT_CSS}</style></head><body>
<header>
<span class="title">漢字書き順プリント</span>
<span class="fields"><span>日付: {html.escape(date)}</span><span class="src">出典: {src}</span></span>
</header>
{"".join(sections)}
<footer>筆順データ: KanjiVG (CC BY-SA 3.0) / 読み: KANJIDIC2 (EDRDG, CC BY-SA 4.0)</footer>
</body></html>'''


def html_to_pdf(html_path, pdf_path):
    chromium = find_chromium()
    if not chromium:
        return False, "Chromiumが見つかりません"
    cmd = [chromium, "--headless", "--disable-gpu", "--no-sandbox",
           "--no-pdf-header-footer", f"--print-to-pdf={pdf_path}",
           "file://" + os.path.abspath(html_path)]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if not os.path.exists(pdf_path):
        return False, (r.stderr or "")[-500:]
    return True, ""


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("kanji", nargs="+", help="対象の漢字(続けて書いてもスペース区切りでもよい)")
    ap.add_argument("--source", default="", help="出典メモ(PDFのヘッダにのみ印字。サイトには載せない)")
    ap.add_argument("--date", default=None, help="日付(省略時は今日、YYYY-MM-DD)")
    ap.add_argument("--slug", default="", help="同日2枚目以降などの識別子(ファイル名に付く)")
    ap.add_argument("--no-pdf", action="store_true", help="PDF生成を省略(HTMLのみ)")
    args = ap.parse_args()

    # 入力から漢字だけを重複なしで抽出(入力順を保持)
    chars = []
    for tok in args.kanji:
        for ch in tok:
            if re.match(r"[㐀-鿿豈-﫿]", ch) and ch not in chars:
                chars.append(ch)
    if not chars:
        raise SystemExit("漢字が見つかりません")

    date = args.date or datetime.date.today().isoformat()
    name = date + (f"-{args.slug}" if args.slug else "")

    meta = load_meta()
    out_of_range = [ch for ch in chars if not (meta.get(ch) and meta[ch]["grade"] <= 3)]
    if out_of_range:
        print(f"注意: 小1〜3配当外の漢字が含まれます: {''.join(out_of_range)}"
              f"(KanjiVGから取得してカードを作ります)")
    missing = [ch for ch in chars if svg_path_for(ch) is None]
    if missing:
        print(f"SVG未保持のためKanjiVGから取得します: {''.join(missing)}")

    assign_dir = os.path.join(DOCS_DIR, "assignments")
    os.makedirs(assign_dir, exist_ok=True)

    # 印刷用HTML(出典入りのためdocsには置かない)→ PDF
    cache = os.path.join(ROOT, ".cache")
    os.makedirs(cache, exist_ok=True)
    print_html = os.path.join(cache, f"print-{name}.html")
    with open(print_html, "w", encoding="utf-8") as f:
        f.write(build_print_html(chars, date, args.source))

    pdf_path = os.path.join(assign_dir, f"{name}.pdf")
    pdf_ok = False
    if not args.no_pdf:
        pdf_ok, err = html_to_pdf(print_html, pdf_path)
        if not pdf_ok:
            print(f"PDF生成に失敗: {err}\n印刷用HTML: {print_html} をブラウザで開いてPDF保存してください")

    # iPad用ページ + マニフェスト + 一覧再生成
    from tools.build_site import build_assignment_page, build_assignments_index, write
    write(os.path.join(assign_dir, f"{name}.html"),
          build_assignment_page(name, date, chars))
    manifest_path = os.path.join(DATA_DIR, "assignments.json")
    entries = []
    if os.path.exists(manifest_path):
        with open(manifest_path, encoding="utf-8") as f:
            entries = json.load(f)
    entries = [e for e in entries if e["name"] != name]
    entries.append({"name": name, "date": date, "kanji": chars, "pdf": pdf_ok})
    entries.sort(key=lambda e: e["name"])
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=1)
    write(os.path.join(assign_dir, "index.html"), build_assignments_index())

    print(f"OK: {len(chars)}字 {''.join(chars)}")
    if pdf_ok:
        print(f"  PDF : {os.path.relpath(pdf_path, ROOT)}")
    print(f"  HTML: docs/assignments/{name}.html")
    print("コミット&プッシュするとPagesの「今回の課題」からも開けます")


if __name__ == "__main__":
    main()
