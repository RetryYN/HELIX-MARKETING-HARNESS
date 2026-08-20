---
artifact_id: AUTH-DEVELOPMENT-MEDIA-HARNESS-THREADS-CANDIDATE
lifecycle_status: draft
slice: cross
---

# Threads ハーネス要求候補

本ディレクトリは Threads 専用ハーネス（1媒体=1ハーネス）の要求候補領域である。
正本は refinement registry の `RRF-MEDIA-HARNESS-THREADS`（draft・PO未承認）と discovery ledger の RDE-000212 であり、
本ディレクトリは候補階層の物理的な置き場に過ぎない。実装入力ではない。

- subject: `MEDIA-HARNESS-THREADS` ／ 親: `MEDIA-PER-MEDIUM-HARNESS`（PRC-36）
- scope assignment: `deferred_candidate`
- 将来この媒体ハーネスは独立リポジトリへ分離する前提で自己完結に設計する。
  外部リポジトリの実作成は PO の明示指示があるまで行わない。
- 承認境界・write境界・共有基盤との分離線は PO 確定待ち（pending 1件）。
