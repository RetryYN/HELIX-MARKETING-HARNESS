# media/ — 媒体別ハーネスの統合層

本リポジトリ（HELIX-MARKETING-HARNESS）は媒体別ハーネスの**統合層**であり、
媒体単位のディレクトリ = 独立リポジトリ（git submodule）として結合する。
開発構造の出どころは `RetryYN/HELIX-HARNESS`（read-only 参照）。

| ディレクトリ | リポジトリ | 状態 |
| --- | --- | --- |
| `media/wp/` | RetryYN/HELIX-WP-HARNESS | PoC 証跡から要求定義を新規に起こす段階 |

- 各媒体の要求・設計・実装は媒体リポ側で行い、統合層は submodule の commit pin で参照する。
- 媒体の追加は PO 判断（新 candidate）から始める。一括追加はせず 1〜2 媒体ずつ。
- 統合層側の L0〜L6 正本・ゲートは旧路線（単一リポ開発）の legacy であり、
  媒体リポの要求正本としては用いない（参照材料に留める）。
