# 事故記録: 画像コーディングの自由記述 note に実サイト名・製品名・個人名が混入（base/wp-theme PR #140、非 main ブランチ）

- 発生日: 2026-09-05
- 対象: `RetryYN/HELIX-WP-THEME`（公開）ブランチ `research/2026-09-05-parts-taxonomy-recapture`、commit 6c2cc9c
  `docs/research/2026-09-05-parts-pattern-taxonomy/recapture-v2/coded/g04.jsonl` ほか g09 / g11
- 検出: codex-astra の Draft PR レビュー（merge 不可、重大 1）
- 内容: 12 並列の画像コーディング agent が `note`（任意・20 字以内の自由記述）に、実サイトの媒体名・第三者 SaaS / ベンダー名・個人名を書いた。
  Claude 側の commit 前検査（`check-public-safety.sh --staged` + ローカル伏せ字 regex）は、これらの名が regex に無かったため通過した。
- 是正（済、commit aa9552d）: 全 coded 行から `note` フィールドを削除（tags は語彙値のみ）。CODING-BRIEF に「自由記述フィールドを置かない」を明記。検出した名をローカル regex（リポ外）へ追加。
- 未是正: ブランチ履歴 6c2cc9c に実名が残る。main には未 merge。

## 原因

1. 自由記述フィールドを公開成果物に許した（語彙値だけなら混入経路がない）。
2. 伏せ字 regex は「PO 指定の参照サイト・テーマ A/B」中心で、調査対象 278 サイトの名を網羅していない。
3. コーディング agent への禁止指示はあったが、出力の機械検査（大文字始まりの語・カタカナ固有名の抽出）を commit 前に行わなかった。

## 対応案（Claude 案、PO 判断待ち）

- A: ブランチを 1 commit に squash して force-push し（非 main・Claude 作成ブランチ）、履歴から実名を除いてから merge。共通規律 5（force-push は PO 明示判断）に該当するため PO の判断を要する。
- B: 現状のまま merge（main の履歴に実名が永続する）。推奨しない。
- 再発防止（PO 判断不要・次回から適用）: 公開成果物の自由記述フィールドを廃止。agent 出力を commit 前に「固有名らしい語の抽出」で機械検査。調査対象サイトの名をローカル regex へ一括投入する手順を `redaction-map` 運用に加える。
