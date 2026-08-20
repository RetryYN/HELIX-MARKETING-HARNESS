# CLAUDE.md — 統合層の作業規律

本リポジトリは媒体別ハーネスの**統合層**。実開発は各媒体リポ（submodule）側で行う。

## 作業境界

- 変更対象は本リポジトリと、明示指示のあった媒体リポのみ。
  `RetryYN/HELIX-HARNESS` と `RetryYN/TAKUMI_CMO-Claude_Cowark` は read-only 参照。
  他リポジトリへの書き込みは、指示に含まれていても着手前に PO へ確認する。
- credential を repository・DB・ログへ書かない。
- 公開・外部 write は PO 承認前に行わない。

## 構成ルール

- 媒体単位のディレクトリ = 独立リポジトリ（git submodule、`media/<媒体>/`）。
  媒体追加は「PO 判断 → 新リポ作成 → submodule 追加」の順。
- 統合層には共通方針・媒体一覧・commit pin 以外を置かない
  （要求・設計・実装・テストは媒体リポ側が正本）。
- 旧単一リポ路線の全体は tag `legacy/single-repo-final` に凍結済み（read-only 参照）。
  main へ旧路線の成果物を書き戻さない。

## 運用メモ

- 媒体リポへの push: SSH deploy key は本リポ限定のため
  `git -c credential.helper='!gh auth git-credential' push` を使う。
- レビューが必要な変更は codex-sol（effort low）、通常タスクは codex-luna（effort max）。
