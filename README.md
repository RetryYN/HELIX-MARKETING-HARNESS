# HELIX-MARKETING-HARNESS — 媒体別ハーネスの統合層

本リポジトリは媒体別マーケティングハーネスの**統合層**である。
媒体単位のディレクトリ = 独立リポジトリ（git submodule）として結合し、
各媒体の要求・設計・実装は媒体リポ側で行う。統合層は共通方針と commit pin だけを持つ。

## 媒体一覧

| ディレクトリ | リポジトリ | 状態 |
| --- | --- | --- |
| `media/wp/` | RetryYN/HELIX-WP-HARNESS | PoC完了・R6詳細要求策定済み。最初のL2 PLANを開始し、S1下書き投稿要求を起草済み。Claude/Codex実往復はconsumer authority解決待ち |

## 開発ベース

| ディレクトリ | リポジトリ | 役割 |
| --- | --- | --- |
| `base/wp-theme/` | RetryYN/HELIX-WP-THEME | WP テーマの開発ベース |
| `base/graphix-neo/` | RetryYN/GRAPHIX-NEO（**private**） | 次世代型 WP テーマ Graphix NEO。Context Page 構造の企画・要求・PoC。PO 判断（2026-08-26）により白紙から出発 |

## 経緯

- 開発構造の出どころは `RetryYN/HELIX-HARNESS`（read-only 参照）。
- 単一リポ時代（L0〜L6 正本・約240ゲート・S0 設計クロージャー）は
  **tag `legacy/single-repo-final`** に全体を凍結してある。参照は read-only。
- 媒体の追加は PO 判断から始める（一括追加はしない）。

```bash
git clone --recurse-submodules git@github.com:RetryYN/HELIX-MARKETING-HARNESS.git
```

`base/graphix-neo/` は private リポジトリのため、submodule の取得には
対象リポジトリへのアクセス権が必要（権限がない場合はそのサブモジュールだけ取得に失敗する）。

## Claude へのテーマ PR レビュー通知

統合層で開いた Claude Code は `.claude/settings.json` の Stop hook から
`base/wp-theme` の package-local HELIX を実行し、テーマの Git common dir にある
harness-memory inbox を待機する（依存パッケージのインストールが必要）。
テーマの作業 worktree で `npm run helix -- github pr-notify --pr <番号> --json` を実行すると、
GitHub の current HEAD と CI を確認した PR レビュー依頼が同じ inbox に入る。
独立したリポジトリの inbox は共有されないため、統合層直下への投入で代用しない。

送信結果の queued は受領を意味しない。Claude の応答終了後に Stop hook が起動し、
claim / delivery が記録されたことを確認する。レビュー完了は
`helix github pr-review-receipt` の receipt で別途確認する。
