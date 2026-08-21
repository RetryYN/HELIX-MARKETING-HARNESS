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

## 経緯

- 開発構造の出どころは `RetryYN/HELIX-HARNESS`（read-only 参照）。
- 単一リポ時代（L0〜L6 正本・約240ゲート・S0 設計クロージャー）は
  **tag `legacy/single-repo-final`** に全体を凍結してある。参照は read-only。
- 媒体の追加は PO 判断から始める（一括追加はしない）。

```bash
git clone --recurse-submodules git@github.com:RetryYN/HELIX-MARKETING-HARNESS.git
```
