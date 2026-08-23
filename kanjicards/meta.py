# -*- coding: utf-8 -*-
"""漢字メタデータ(学年・画数・読み)の読み込みと読みの表示整形"""
import json
import os

from . import DATA_DIR

_META = None
_GRADES = None


def load_meta():
    """data/kanji_meta.json → {漢字: {grade, strokes, on[], kun[]}}"""
    global _META
    if _META is None:
        with open(os.path.join(DATA_DIR, "kanji_meta.json"), encoding="utf-8") as f:
            _META = json.load(f)
    return _META


def load_grades():
    """data/grades.json → {"1": [80字], "2": [160字], ...} 読み順ソート済み"""
    global _GRADES
    if _GRADES is None:
        with open(os.path.join(DATA_DIR, "grades.json"), encoding="utf-8") as f:
            _GRADES = json.load(f)
    return _GRADES


def kata_to_hira(s):
    return "".join(chr(ord(c) - 0x60) if "ァ" <= c <= "ヶ" else c for c in s)


def format_kun(r):
    """KANJIDIC2の訓読み表記を子ども向けに整形: おく.る → おく-る、-がかり → がかり"""
    return r.strip("-").replace(".", "-")


def reading_sort_key(ch, meta=None):
    """読み順ソートのキー: 代表読み(音優先、ひらがな化)"""
    m = (meta or load_meta()).get(ch)
    if not m:
        return "ん" * 5 + ch
    if m["on"]:
        return kata_to_hira(m["on"][0])
    if m["kun"]:
        return m["kun"][0].strip("-").split(".")[0]
    return "ん" * 5 + ch


def display_readings(ch, max_on=3, max_kun=4):
    """カード表示用の読み: (音[カタカナ], 訓[ひらがな整形済み])"""
    m = load_meta().get(ch)
    if not m:
        return [], []
    # 接辞用の読み(-ノウ 等)は低学年向けカードでは省く
    on = [r for r in m["on"] if not (r.startswith("-") or r.endswith("-"))][:max_on]
    kun = [format_kun(r) for r in m["kun"]]
    # 同じ語幹の重複表記(例: のぼ-る / のぼ-り)はそのまま残すが、完全重複は除く
    seen, uniq = set(), []
    for r in kun:
        if r not in seen:
            seen.add(r)
            uniq.append(r)
    return on, uniq[:max_kun]
