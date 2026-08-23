# CLAUDE.md — 日常運用の手順

このリポジトリは小学校全学年(1〜6年・1026字)の漢字書き順カード教材。親がドリル問題の写真を渡したら、以下の手順で **B4印刷用PDF** と **iPad用の課題ページ** を作るのが日常タスク。

## 写真 → PDF の手順

1. **写真を読む**: 渡されたドリル問題の写真(1〜複数枚)から問題文を読み取り、**解答として書くことになる漢字**を列挙する。
   - 「よみがな→漢字」の書き取り問題が多い。読みから答えの漢字を特定する(`data/kanji_meta.json` の読みで確認できる)。
   - 読み取りや答えに **自信がない問題は勝手に確定せず、候補を挙げて親に確認する**(AskUserQuestion)。
2. **生成コマンドを1回実行**:
   ```bash
   python3 tools/make_assignment.py <漢字をつなげた文字列> --source "<出典メモ(例: ○○塾 漢字ドリル p.12)>"
   ```
   - 重複は自動で1枚にまとまる。同日2回目以降は `--slug` を付ける(例: `--slug 2`)。
   - 小学校配当外の漢字が答えに含まれる場合は **その旨を親に伝える**。コマンドが警告を出しつつ KanjiVG から即席カードを作る(読み仮名は無い場合がある)。
3. **確認**: 生成された `docs/assignments/<日付>.pdf` を開き、字と枚数が合っているか確認する。
4. **コミット & プッシュ**: `docs/assignments/` と `data/assignments.json`(配当外を取得した場合は `data/kanjivg_extra/` も)をコミットしてプッシュする。Pages が自動更新され、iPad から「今回の課題」ページとPDFが開ける。

## 守ること

- **公開サイトに個人情報を載せない**: 塾名・子どもの名前などは `--source`(PDFのみに印字)に入れるのは可。Webページ・コミットメッセージには入れない。
- カードの見た目は承認済みの見本(`kakijun_sample.html`)準拠。配色・レイアウトを変える変更は親に確認してから。
- 生成物を手で編集しない(`docs/` は `tools/build_site.py` と `tools/make_assignment.py` の出力)。

## その他のコマンド

```bash
python3 tools/build_site.py    # 索引+カード1026枚の再生成(カードの見た目を変えたとき)
python3 tools/check_cards.py   # 受け入れチェック(コマ数=画数・連番・読み分け)
python3 tools/build_data.py    # KanjiVG/KANJIDIC2からdata/を再構築(通常は不要)
```

サイトやカードの生成ロジックを変更したら `build_site.py` → `check_cards.py` を通してからコミットすること。

## 構成の要点

- `kanjicards/` — KanjiVGパース(`kanjivg.py`)、読みメタ(`meta.py`)、コマSVG・カードHTML描画(`render.py`)
- `data/kanjivg/` — 小1〜6の1026字のKanjiVG SVGをvendor済み(オフラインで生成可能)
- カードページは `docs/cards/<unicode16進5桁>.html`(例: 右=`053f3.html`)
- カード化対象の学年は `tools/build_site.py` の `CARD_GRADES`(現在は小1〜6すべて)
