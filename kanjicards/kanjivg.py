# -*- coding: utf-8 -*-
"""KanjiVG SVGの探索・取得・パース

パース方法は gen_sample.py(動作確認済み)を踏襲:
StrokePaths グループ内の path 要素は文書順=筆順、
StrokeNumbers グループの text 要素が各画の番号位置を持つ。
"""
import os
import re
import urllib.request

from . import DATA_DIR

KANJIVG_DIR = os.path.join(DATA_DIR, "kanjivg")        # vendor済み(小1〜6)
KANJIVG_EXTRA_DIR = os.path.join(DATA_DIR, "kanjivg_extra")  # 配当外を都度取得
RAW_URL = "https://raw.githubusercontent.com/KanjiVG/kanjivg/master/kanji/{code}.svg"


def code_of(ch):
    """漢字→KanjiVGファイル名の16進コード(例: 右→053f3)"""
    return format(ord(ch), "05x")


def svg_path_for(ch):
    """漢字のKanjiVG SVGパスを返す。無ければNone。"""
    code = code_of(ch)
    for d in (KANJIVG_DIR, KANJIVG_EXTRA_DIR):
        p = os.path.join(d, code + ".svg")
        if os.path.exists(p):
            return p
    return None


def fetch_svg(ch, timeout=30):
    """配当外の漢字のSVGをKanjiVG(GitHub)から取得してdata/kanjivg_extra/に保存"""
    code = code_of(ch)
    os.makedirs(KANJIVG_EXTRA_DIR, exist_ok=True)
    dest = os.path.join(KANJIVG_EXTRA_DIR, code + ".svg")
    url = RAW_URL.format(code=code)
    with urllib.request.urlopen(url, timeout=timeout) as r:
        data = r.read()
    with open(dest, "wb") as f:
        f.write(data)
    return dest


def parse_svg(src):
    """SVG文字列 → (strokes: [d属性], numpos: {番号: (x, y)})"""
    strokes = re.findall(r'<path[^>]*\bd="([^"]+)"', src)
    nums = re.findall(
        r'<text transform="matrix\([^)]*?(-?[\d.]+)\s+(-?[\d.]+)\)"[^>]*>(\d+)</text>', src)
    numpos = {int(n): (float(x), float(y)) for x, y, n in nums}
    return strokes, numpos


def load_strokes(ch, fetch_if_missing=False):
    """漢字 → (strokes, numpos)。SVGが無ければ FileNotFoundError。

    fetch_if_missing=True なら KanjiVG からの取得を試みる(要ネットワーク)。
    """
    path = svg_path_for(ch)
    if path is None and fetch_if_missing:
        path = fetch_svg(ch)
    if path is None:
        raise FileNotFoundError(
            f"KanjiVG SVGがありません: {ch} (U+{ord(ch):04X}) — "
            f"tools/build_data.py で再構築するか fetch_if_missing=True で取得してください")
    with open(path, encoding="utf-8") as f:
        return parse_svg(f.read())
