#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""受け入れ基準の機械チェック

- 学年配当の字数(1年80 / 2年160 / 3年200)
- 全440字: KanjiVG SVGが存在し、コマ数=画数、番号が1..nの連番
- メタデータの画数とKanjiVGの画数が一致
- 読み仮名: 音=カタカナ / 訓=ひらがな に正しく分かれている
- docs/cards/ に全カードページが存在し、コマ数(完成+n)が一致

失敗があれば一覧を出して終了コード1。
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from kanjicards import DOCS_DIR
from kanjicards.kanjivg import code_of, load_strokes, svg_path_for
from kanjicards.meta import load_grades, load_meta

KATAKANA = re.compile(r"^[ァ-ヶー]+$")
HIRAGANA = re.compile(r"^[ぁ-んー]+([.-][ぁ-んー]+)*$")

errors = []


def err(msg):
    errors.append(msg)


def main():
    grades = load_grades()
    meta = load_meta()

    for g, want in (("1", 80), ("2", 160), ("3", 200)):
        if len(grades[g]) != want:
            err(f"学年{g}: 字数 {len(grades[g])} != {want}")

    total = 0
    for g in ("1", "2", "3"):
        for ch in grades[g]:
            total += 1
            if svg_path_for(ch) is None:
                err(f"{ch}: KanjiVG SVGなし")
                continue
            strokes, numpos = load_strokes(ch)
            n = len(strokes)
            m = meta.get(ch)
            if not m:
                err(f"{ch}: メタデータなし")
                continue
            if m["strokes"] != n:
                err(f"{ch}: 画数不一致 meta={m['strokes']} kanjivg={n}")
            if set(numpos.keys()) != set(range(1, n + 1)):
                err(f"{ch}: 番号が連番でない: {sorted(numpos.keys())} (画数{n})")
            if int(m["grade"]) != int(g):
                err(f"{ch}: 学年不一致 {m['grade']} != {g}")
            for r in m["on"]:
                if not KATAKANA.match(r.strip("-")):
                    err(f"{ch}: 音読みがカタカナでない: {r}")
            for r in m["kun"]:
                if not HIRAGANA.match(r.strip("-")):
                    err(f"{ch}: 訓読みがひらがなでない: {r}")
            page = os.path.join(DOCS_DIR, "cards", code_of(ch) + ".html")
            if not os.path.exists(page):
                err(f"{ch}: カードページなし ({page})")
                continue
            with open(page, encoding="utf-8") as f:
                html_src = f.read()
            cells = html_src.count('<div class="cell">')
            if cells != n + 1:
                err(f"{ch}: カードページのコマ数 {cells} != {n + 1} (完成+{n}画)")
            if "CARD_DATA" not in html_src:
                err(f"{ch}: カードページにプレイヤーデータなし")

    print(f"チェック対象: {total}字")
    if errors:
        print(f"NG: {len(errors)}件")
        for e in errors:
            print(" ", e)
        sys.exit(1)
    print("OK: 全カード コマ数=画数・連番・読み分け・ページ生成 いずれも問題なし")


if __name__ == "__main__":
    main()
