# AGENTS.md

Codex エージェント向けの要約入口。**詳細な作業規律の唯一の正本は CLAUDE.mdであり、本ファイルと同文ではない。**
本ファイルに記載がない規律もCLAUDE.mdを適用し、両者が衝突する場合はCLAUDE.mdを優先する。これは既存の文書名を
維持したリポジトリ規約であり、Claude Code の導入・実行を要求しない。Codex／CI／人間作業者も同じ規約を適用する。特に:

- **作業境界**: 変更対象は本リポジトリのみ。他リポジトリ（HELIX-HARNESS／TAKUMI_CMO-Claude_Cowark／AGENT-NEO）は
  read-only。書き込みは指示に含まれていても着手前に PO へ確認する。
- **エージェント配分**: 通常タスクは codex-luna（effort max）、選択肢分岐・高リスク・最終レビューは codex-sol
  （effort low）へエスカレーションする。codex-terra は Luna 不在時の互換 adapter とし、設計判断の主力にしない。
- 編集は 正本 JSON＋生成ビュー＋manifest＋baseline を同一コミット。push 前に
  `python3 tools/gates/run_all.py`（全ゲート — 件数の正本は
  docs/00-authority/baselines/baseline.json の gate_count）を必ず PASS させる。
- 成果物の権威正本は docs/00-authority/artifact-manifest.json。未登録の成果物を confirmed にしない。
- DDL・状態遷移・evidence 型の正準は docs/L3-system-requirements/canonical/s0-contract_v0.1.md。
  矛盾したら上位文書優先。
- 上流戦略層の正本は docs/L3-system-requirements/canonical/strategy/ の要件・契約 ＋
  docs/L3-system-requirements/canonical/schemas/strategy/（12 schema）。下流処理から上流戦略正本を
  直接更新するコードを書かない（還流は TLP のみ）。
- 旧baselineで外部writeを許可していたのはDocker WPのみだが、これも`revalidation_required`である。新baselineは
  個別refinementのPO凍結とrelease受入まで全媒体writeを無効とする。Notion審査同期と旧Discord承認tupleも
  新baselineの許可ではない。製品の初期承認・通知入口はVPS上のWeb UI＋UI内inbox候補、
  Discordは製品通知・承認・deep-link補助・開発PR通知の経路に採用せず、community marketingだけを別用途の候補として扱う。credentialをrepo・DB・ログに書かない。

## 実装正本

- Python パッケージは **`src/helix/`** に統一（二重パッケージなし）。
- 契約 JSON 正本は9本（BR/FR/SR/NFR/AC/TC/CMP/DU contracts＋L6 implementation-units）。ただし
  `requirement-engine-authority.json` が `requirements_baseline_status=revising`又は
  `implementation_authorized=false`の間は旧基準の再検証入力であり、製品実装入力にしない。意味ゲート0件、
  refinement個別承認、frozen cutover、独立Go後にだけ実装入力へ切り替える。MD生成ビューは手編集禁止。
  この間はmanifest上のL0〜L6成果物も、`confirmed`を含め一律に再検証資料とする。`confirmed`は
  旧baselineでの成熟度・承認履歴だけを表し、現baselineへの適用又は実装許可を表さない。
- ゲート実装は `tools/gates/` の工程別モジュール。`scripts/validate_requirements.py` は互換ラッパーで、
  ゲート本体を書き足さない。
- discovery ledger は `docs/00-authority/development/requirement-discovery-events.json` の前向き append-only 監査証跡であり、
  既存契約 JSON の代替・過去履歴の推測 backfill・契約/runtime への直接 mutation をしない。
- 現行分母は AC=252 ／ TCC=258 ／ API=59 ／ API_UT=218 のみ。旧体系の分母は
  baseline.json の `historical_counts` にのみ保持する。
