# 漢字書き順カード & ドリル解答PDF生成

小学校低学年向けの漢字書き順教材リポジトリ。小学1〜3年の配当漢字 **440字**(1年80 / 2年160 / 3年200)について、一画ずつ分解した書き順カードを生成・管理し、漢字ドリルの課題に合わせて **B4印刷用PDF** と **iPad閲覧用ページ** を作れる。

要件は [kanji-cards-spec.md](kanji-cards-spec.md) を参照。日常運用の手順は [CLAUDE.md](CLAUDE.md) にある。

## できること

- **カード資産**: 440字ぶんのカードページ(`docs/cards/`)。完成形+1画ごとのコマ、書き始め位置の番号、読み仮名(音=カタカナ/訓=ひらがな)つき。
- **Webサイト**: GitHub Pages で公開する静的サイト(`docs/`)。学年別・読み順の索引、読み仮名検索、カードページではタップ/ボタンで一画ずつ進む・自動アニメーション。iPad Safari 対応。
- **課題PDF**: ドリル問題の解答になる漢字を指定すると、B4縦・大きめコマ(1ページ2〜3字)のPDFと、同じ漢字セットのWebページ(「今回の課題」)を一括生成。

## 使い方

Python 3(標準ライブラリのみ)。PDF生成には Chromium/Chrome が必要(無ければ印刷用HTMLが残るのでブラウザからPDF保存)。

```bash
# 課題PDF+課題ページの生成(日常はこれだけ)
python3 tools/make_assignment.py 右左水空 --source "○○塾 漢字ドリル p.12"

# サイト(索引+440カードページ)の再生成
python3 tools/build_site.py

# データの再構築(KanjiVG/KANJIDIC2を取得し直す。通常は不要)
python3 tools/build_data.py

# 受け入れチェック(全440字: コマ数=画数・番号連番・読み分け等)
python3 tools/check_cards.py
```

`make_assignment.py` の補足:

- 重複した漢字は1枚にまとめる。小1〜3配当外の字は警告のうえ KanjiVG から即席取得して含める。
- `--source` の出典メモは **PDFにのみ** 印字され、Webページには載せない(公開サイトに塾名等の個人情報を出さないため)。
- 同じ日に2枚以上作るときは `--slug` で区別する(例: `--slug drill12`)。

## リポジトリ構成

```
kanjicards/        共通モジュール(KanjiVGパース・コマSVG/カードHTML描画・メタデータ)
tools/             生成スクリプト(上記4本)
data/
  grades.json      学年別配当リスト(1〜6年、現行課程。各学年内は読み順)
  kanji_meta.json  漢字→学年・画数・読みのメタデータ(小1〜6+常用)
  kanjivg/         KanjiVG SVG(小1〜6の1026字をvendor)
  kanjivg_extra/   配当外の字を都度取得した置き場
  assignments.json 課題の一覧(マニフェスト)
docs/              GitHub Pages 公開物(索引・カード440枚・今回の課題)
```

小4以降への拡張は `tools/build_site.py` の `CARD_GRADES` に `"4"` 等を足して再生成するだけ(データは6年ぶんvendor済み)。

## GitHub Pages

`.github/workflows/pages.yml` が push のたびに `docs/` を自動デプロイする。初回のみリポジトリの **Settings → Pages → Source を「GitHub Actions」** に設定すること。

無料プランの Pages は URL を知っていれば誰でも見られるため、サイトには個人情報(塾名・名前など)を載せない運用にしている。

## データソースとライセンス

本リポジトリは以下のデータを利用・再配布している。

- **筆順**: [KanjiVG](https://github.com/KanjiVG/kanjivg) © Ulrich Apel, [CC BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0/) ライセンス。`data/kanjivg/` に SVG を同梱。
- **読み・画数**: [KANJIDIC2](https://www.edrdg.org/wiki/index.php/KANJIDIC_Project) © [EDRDG](https://www.edrdg.org/)(Electronic Dictionary Research and Development Group)、[CC BY-SA 4.0](https://www.edrdg.org/edrdg/licence.html) ライセンス。抽出結果を `data/kanji_meta.json` に収録。
- **学年配当**: 文部科学省「学年別漢字配当表」(現行課程)。KANJIDIC2 の学年フィールド経由で取得し、字数(80/160/200/202/193/191)を検証済み。

生成したカード・PDF・サイトも上記の継承ライセンス(CC BY-SA)に従う。
