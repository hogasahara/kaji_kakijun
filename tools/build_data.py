#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""データ整備: KanjiVG + KANJIDIC2 → data/

生成物:
  data/grades.json      学年別配当リスト(1〜6年、各学年内は読み順)
  data/kanji_meta.json  漢字→{grade, strokes, on, kun}(小1〜6+常用)
  data/kanjivg/*.svg    小1〜6配当 1026字の KanjiVG SVG(vendor)

ソースが未指定ならネットワークから取得して .cache/ に保存する。
  KanjiVG:   https://github.com/KanjiVG/kanjivg (CC BY-SA 3.0)
  KANJIDIC2: https://www.edrdg.org/ (EDRDG licence / CC BY-SA 4.0)
"""
import argparse
import gzip
import io
import json
import os
import shutil
import sys
import urllib.request
import xml.etree.ElementTree as ET
import zipfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from kanjicards import DATA_DIR, ROOT
from kanjicards.kanjivg import parse_svg
from kanjicards.meta import kata_to_hira

CACHE_DIR = os.path.join(ROOT, ".cache")
KANJIVG_RELEASE = "https://github.com/KanjiVG/kanjivg/releases/download/r20250816/kanjivg-20250816-all.zip"
KANJIDIC2_URL = "https://www.edrdg.org/kanjidic/kanjidic2.xml.gz"

VENDOR_GRADES = ["1", "2", "3", "4", "5", "6"]  # SVGをvendorする学年
META_GRADES = VENDOR_GRADES + ["8"]             # メタデータを持つ学年(8=その他の常用漢字)


def _download(url, dest):
    print(f"download: {url}")
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with urllib.request.urlopen(url, timeout=120) as r, open(dest, "wb") as f:
        shutil.copyfileobj(r, f)
    return dest


def get_kanjidic(path=None):
    if path:
        return path
    dest = os.path.join(CACHE_DIR, "kanjidic2.xml.gz")
    if not os.path.exists(dest):
        _download(KANJIDIC2_URL, dest)
    return dest


def get_kanjivg_zip(path=None):
    if path:
        return path
    dest = os.path.join(CACHE_DIR, os.path.basename(KANJIVG_RELEASE))
    if not os.path.exists(dest):
        _download(KANJIVG_RELEASE, dest)
    return dest


def parse_kanjidic(path):
    """KANJIDIC2 → {漢字: {grade, strokes, on, kun}}(対象学年のみ)"""
    if path.endswith(".gz"):
        with gzip.open(path, "rb") as f:
            data = f.read()
    else:
        with open(path, "rb") as f:
            data = f.read()
    root = ET.parse(io.BytesIO(data)).getroot()
    meta = {}
    for c in root.iter("character"):
        grade = c.findtext("misc/grade")
        if grade not in META_GRADES:
            continue
        lit = c.findtext("literal")
        strokes = int(c.findtext("misc/stroke_count"))
        on, kun = [], []
        for r in c.iter("reading"):
            t = r.get("r_type")
            if t == "ja_on":
                on.append(r.text)
            elif t == "ja_kun":
                # 単位の当て字など、カタカナ表記の訓(例: 志=シリング)は除外
                if not any("ァ" <= c <= "ヶ" for c in r.text):
                    kun.append(r.text)
        meta[lit] = {"grade": int(grade), "strokes": strokes, "on": on, "kun": kun}
    return meta


def sort_key(ch, meta):
    m = meta[ch]
    if m["on"]:
        k = kata_to_hira(m["on"][0])
    elif m["kun"]:
        k = m["kun"][0].strip("-").split(".")[0]
    else:
        k = "ん" * 5
    return (k, ch)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--kanjivg-zip", help="KanjiVGリリースzipのパス(省略時はダウンロード)")
    ap.add_argument("--kanjidic", help="kanjidic2.xml(.gz)のパス(省略時はダウンロード)")
    args = ap.parse_args()

    meta = parse_kanjidic(get_kanjidic(args.kanjidic))

    # 学年配当リスト(読み順)
    grades = {}
    for g in VENDOR_GRADES:
        chars = [ch for ch, m in meta.items() if m["grade"] == int(g)]
        chars.sort(key=lambda ch: sort_key(ch, meta))
        grades[g] = chars
    expected = {"1": 80, "2": 160, "3": 200, "4": 202, "5": 193, "6": 191}
    for g, n in expected.items():
        if len(grades[g]) != n:
            raise SystemExit(f"学年{g}の字数が配当表と不一致: {len(grades[g])} != {n}")

    # KanjiVG SVGのvendor(小1〜6)+画数クロスチェック
    zf = zipfile.ZipFile(get_kanjivg_zip(args.kanjivg_zip))
    names = {os.path.basename(n): n for n in zf.namelist() if n.endswith(".svg")}
    outdir = os.path.join(DATA_DIR, "kanjivg")
    os.makedirs(outdir, exist_ok=True)
    mismatches = []
    for g in VENDOR_GRADES:
        for ch in grades[g]:
            fname = format(ord(ch), "05x") + ".svg"
            if fname not in names:
                raise SystemExit(f"KanjiVGにSVGがありません: {ch} ({fname})")
            src = zf.read(names[fname]).decode("utf-8")
            with open(os.path.join(outdir, fname), "w", encoding="utf-8") as f:
                f.write(src)
            strokes, numpos = parse_svg(src)
            if len(strokes) != meta[ch]["strokes"]:
                mismatches.append((ch, len(strokes), meta[ch]["strokes"]))
                # コマ生成はKanjiVGが正なので画数もKanjiVGに合わせる
                meta[ch]["strokes"] = len(strokes)

    os.makedirs(DATA_DIR, exist_ok=True)
    with open(os.path.join(DATA_DIR, "grades.json"), "w", encoding="utf-8") as f:
        json.dump(grades, f, ensure_ascii=False, indent=1)
    meta_sorted = {ch: meta[ch] for ch in sorted(meta, key=ord)}
    with open(os.path.join(DATA_DIR, "kanji_meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta_sorted, f, ensure_ascii=False, indent=1)

    total = sum(len(grades[g]) for g in VENDOR_GRADES)
    print(f"OK: grades.json({total}字) / kanji_meta.json({len(meta)}字) / kanjivg SVG {total}枚")
    if mismatches:
        print("画数がKANJIDIC2とKanjiVGで異なる字(KanjiVGを採用):")
        for ch, kv, kd in mismatches:
            print(f"  {ch}: KanjiVG={kv} KANJIDIC2={kd}")


if __name__ == "__main__":
    main()
