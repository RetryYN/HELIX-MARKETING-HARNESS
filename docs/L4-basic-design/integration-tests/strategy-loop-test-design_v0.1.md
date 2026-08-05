---
artifact_id: L4-STRATEGY-LOOP-TEST-DESIGN
lifecycle_status: confirmed
slice: S0
---

# 戦略層テスト設計 v0.1

> status: **confirmed**（2026-08-01 PO 承認 — 上流戦略インフィニティループ再強化指示。AI 起草）
> pair: [strategy-loop-design_v0.1.md](../canonical/components/strategy-loop-design_v0.1.md)／
> [strategy-loop-requirements_v0.1.md](../../L3-system-requirements/canonical/strategy/strategy-loop-requirements_v0.1.md)（要件・設計の両対）
> 機械可読正本: [json/strategy-tests.json](strategy-tests.json)（STC 台帳）
> 位置づけ: 戦略層の検証。**docs 層の検証（STC-G: ゲート×fixture の negative test）は
> validate_requirements.py が毎 push 実行済み**。実装層の検証（STC-I）は S0.1／S1 の pytest で実装する。
> 既存の ITC 16 と TC／UT 契約の分母は変更しない。

---

## 1. ゲート検証（STC-G — 常設。invalid fixture の拒否 = negative test）

| STC | 対象ゲート | fixture（json/strategy/fixtures/） | 期待 |
|---|---|---|---|
| STC-G-01 | G-STRAT-BRIEF | strategic-brief.valid.json | schema 適合で受理 |
| STC-G-02 | G-STRAT-BRIEF | strategic-brief.no-trace.invalid.json（value_hypothesis_id 欠落） | **拒否** |
| STC-G-03 | G-STRAT-TRACE | strategic-brief.no-trace.invalid.json ＋ required から value_hypothesis_id を落とした変異 schema の検出自己検査 | **拒否**・変異検出 |
| STC-G-04 | G-SEGMENT-CONTEXT | segment-context.valid.json | 受理 |
| STC-G-05 | G-SEGMENT-CONTEXT | segment-context.demographic-only.invalid.json（人口統計のみ） | **拒否** |
| STC-G-06 | G-OBS-INTERPRETATION | market-observation.valid.json | 受理 |
| STC-G-07 | G-OBS-INTERPRETATION | market-observation.mixed-interpretation.invalid.json（interpretation 混在） | **拒否** |
| STC-G-08 | G-LEARNING-TRACE | tactical-learning-packet.valid.json | 受理 |
| STC-G-09 | G-LEARNING-TRACE | tactical-learning-packet.unlinked.invalid.json（loop_run/evidence 欠落） | **拒否** |
| STC-G-10 | G-NO-DIRECT-STRATEGY-MUTATION | validator が DDL 適用済み DB へ UPDATE/DELETE 4 系を実行（実 DML） | 全系 **ABORT**（1 件でも通過で FAIL） |
| STC-G-11 | G-REVISION-EVIDENCE | strategy-revision.valid.json | 受理 |
| STC-G-12 | G-REVISION-EVIDENCE | strategy-revision.single-metric-accept.invalid.json（単一根拠 accepted） | **拒否** |
| STC-G-13 | G-STRATEGY-VERSION | version を落とした変異 schema の検出自己検査＋DDL append-only の実 DML 実証 | 変異検出・**ABORT** |
| STC-G-14 | G-MEDIA-ROLE | strategic-brief.valid.json（media_role ∈ 台帳） | 受理 |
| STC-G-15 | G-MEDIA-ROLE | strategic-brief.bad-media-role.invalid.json（媒体名を役割に使用） | **拒否** |
| STC-G-16 | G-CONTENT-VALUE-DEFINITION | content-plan.valid.json | 受理 |
| STC-G-17 | G-CONTENT-VALUE-DEFINITION | content-plan.missing-recognition.invalid.json（認識変化宣言欠落） | **拒否** |
| STC-G-18 | G-STRAT-PAIR | 4 文書相互 pair＋SR/SCM/STC 双方向カバー＋SR カバレッジを落とした変異台帳の検出自己検査 | 欠落・変異で FAIL |

## 2. 実装検証（STC-I — S0.1／S1 の pytest。tests/unit/test_strategy_store.py 等）

| STC | 対象 | 検証 | S |
|---|---|---|---|
| STC-I-01 | SCM-01／SR-11 | strategic_briefs 内容列 UPDATE・DELETE が SQLite トリガで拒否される（拒否系） | S0.1 |
| STC-I-02 | SCM-01／SR-08 | tactical_learning_packets の UPDATE・DELETE が拒否される（拒否系） | S0.1 |
| STC-I-03 | SCM-03／SR-07 | brief なし（NULL／digest 不一致／superseded／期間外）の下位 loop_run 開始が拒否される（拒否系） | S0.1 |
| STC-I-04 | SCM-02／SR-06 | brief シード → digest 決定的計算 → supersedes 新版発行で旧版 superseded | S0.1 |
| STC-I-05 | SCM-04／SR-08 | 下流終端到達で TLP が 1 件生成され、観測・解釈・判定・推奨が別カラムに入る | S0.1 |
| STC-I-06 | SR-09 | 下流 kernel・コネクタの公開 API に上流正本への書込みが存在しない（経路テスト） | S0.1 |
| STC-I-07 | SCM-08／SR-10 | 支持根拠 1 件の revision accept が拒否される（拒否系） | S1 |
| STC-I-08 | SCM-05〜07／SR-02..05 | 上流モデル生成の schema 適合・棄却案保持・反証条件必須 | S1 |
| STC-I-09 | SCM-10／SR-13 | 5 宣言を欠くコンテンツ企画の実行時拒否（拒否系） | S1 |
| STC-I-10 | SR-16 | revision 経由の意味モデル更新のみが「一周」と計上される | S1 |
| STC-I-11 | SR-17 | 語彙外 node_kind・trace 欠落・循環を持つ logic_tree の拒否（8 軸語彙のみ受理・拒否系） | S2 |
| STC-I-12 | SR-18 | 証跡参照なしの node_verdict・既存判定の UPDATE/DELETE の拒否（append-only・拒否系） | S2 |
| STC-I-13 | SR-19 | claim_level 未宣言・不確実性欠落・入力系列 digest なし・correlation のみ根拠の supported 宣言の拒否（拒否系） | S2 |

拒否系（fail-close）は STC-G 8 本＋STC-I 5 本。STC-I の S0.1 分は S0.1 実装の完了条件に含める
（既存 UT とは独立の追加テストであり、既存分母を変更しない）。
