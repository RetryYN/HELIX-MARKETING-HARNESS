# AGENTS.md — Codex 向け統合層ルール

このファイルは Codex の入口である。Claude Code の入口は `CLAUDE.md`。
作業開始時にルートの `CLAUDE.md` を全文読み、その「統合層の作業規律」を本ファイルと一体の指示として適用する。
共通規律の正本は `CLAUDE.md` とし、本ファイルへ規律本文を複製しない。

## リポジトリの位置づけ

- このリポジトリは媒体別マーケティングハーネスの**統合層**である。
- 実開発の正本は各 submodule にあり、統合層は共通方針・媒体一覧・commit pin を管理する。
- `media/<媒体>/` は媒体別ハーネス、`base/<基盤>/` は開発ベースであり、両者を同じ進捗として扱わない。
- 旧単一リポ路線は tag `legacy/single-repo-final` の read-only 参照であり、現行 `main` の進捗と混同しない。

## 指示の適用順

1. system / developer / user の指示
2. ルート `CLAUDE.md` の統合層共通規律
3. 本ファイル
4. 作業対象 submodule 内の `AGENTS.md` / `CLAUDE.md` にあるリポ固有の追記

submodule の指示が統合層の共通規律と矛盾する場合は、ルート `CLAUDE.md` を優先する。

## セッション開始時の確認

1. ルート `CLAUDE.md` と `README.md` を読む。
2. `git status --short --branch` と `git submodule status` で統合層と pin を確認する。
3. 対象媒体が指定されている場合だけ、その submodule の指示・handover・進捗正本を読む。
4. 対象媒体が未指定なら、統合層全体の状況を答え、特定 submodule のフェーズを全体進捗として代用しない。

## 進捗回答のルール

- 「現在の進捗」は、原則として現行統合層 `main` と `media/` の状態を基準に答える。
- `base/` は開発ベースなので、ユーザーが明示しない限り、その L0〜L8 フェーズを現行媒体の進捗として報告しない。
- 進捗の正本は対象 submodule が定める handover / phase / 要求文書。コミットメッセージだけでフェーズを推定しない。
- 正本同士が矛盾している場合は、勝手に一つを採用せず、矛盾と各記録の更新時点を示す。
- ローカルで確認した事実と、GitHub・CI・本番など未確認の外部状態を明確に分ける。

## 変更境界

- ユーザーが対象を指定していない場合、submodule 内を変更しない。
- submodule を変更した場合、統合層での pin 更新は別変更として明示する。
- cross-repo write、公開、外部サービスへの write、破壊的操作は、ルート `CLAUDE.md` の承認条件に従う。
- credential を repository、DB、ログ、応答へ書かない。
- 公開情報の最小化と検査は `CLAUDE.md` および
  `docs/governance/public-repository-safety.md` を継承する。調査証跡も無加工で公開しない。

## モデル運用

- Claude 側の `.claude/agents/` は Claude Code 用ラッパー設定であり、Codex の直接指示ではない。
- Codex では実行環境から与えられたモデル・権限・ツール設定を優先する。
- レビューや通常タスクのモデル選択を外部エージェントへ委譲する場合だけ、ルート `CLAUDE.md` の運用メモを参照する。
