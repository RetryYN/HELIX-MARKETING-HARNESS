---
artifact_id: L6-S0-CONFIG-STORE
lifecycle_status: confirmed
slice: S0
traces: [FR-33]
forward_refs: [FR-34]
dus: [DU-12]
---

# 機能設計: 設定管理（config の append-only 履歴・安全側既定値）

> status: **confirmed**（2026-08-01 意味トレース是正で新設 — DU-12 の機能設計が不在だったため）
> 正準参照: 要求 = FR-33（設定管理 — config 履歴保持）。DDL（`config`）と保護トリガの正準は
> [s0-contract_v0.1.md §2](../../L3-system-requirements/canonical/s0-contract_v0.1.md)、append-only 規約は同 §6。
> API 署名の正本は [detailed-design_v0.1.md DU-12](../../L5-detailed-design/canonical/detailed-design_v0.1.md)
> （`docs/L5-detailed-design/canonical/apis/du-contracts.json` の DU-12）。
> 兄弟文書: [migration.md](migration.md)（DDL 適用と保護トリガの存在検査）／
> [brand-isolation-foundation.md](brand-isolation-foundation.md)（`<profile_key>.` 接頭は S0 では運用規約）
> 位置づけ: 「設定値をハードコードしない」規律の受け皿を、履歴が消えない形で降下させる。
> 変更は上書きではなく新行 INSERT であり、理由（`reason`）のない変更行は存在しない。

---

## §0 位置づけ・動機

運転条件（retry 上限・予算上限・待機秒数など）を後から変えられることと、**いつ・誰が・なぜ
変えたかが消えないこと**は同じ強さで必要になる。config を可変テーブルにすると、事故のあとで
「その時どの値だったか」が失われる。そこで config は append-only とし、有効値は key ごとの
最新行として解決する。

## §1 実装単位と責務

| 実装単位 | 責務 | 失敗方針 |
|---|---|---|
| `set(conn, key, value, value_type, reason, agent_id, clock)` | 旧行を残したまま新行を INSERT し、`supersedes_config_id` に直前の有効行を指定する。`reason` は必須 | `reason` 空は `ConfigReasonMissing`／同一 (key, changed_at) は `IntegrityError`（UNIQUE）／直接 UPDATE・DELETE は保護トリガが `ConfigAppendOnlyViolation` |
| `get(conn, key, default)` | key ごとに `changed_at` 最大の行を有効値として返し、`value_type` に従って型変換する | 不在 key は既定値表にあれば保守的既定値、なければ拒否側へ倒す（暗黙の fail-open 値を返さない） |

## §2 検査順序と不変条件

1. `set` の検査順は **reason → 型 → 一意性**: `reason` が非空であることを最初に見る
   （理由のない変更行を DB へ到達させない）。次に `value_type` と `value` の整合、最後に
   `UNIQUE(key, changed_at)`。いずれも先に評価が終わるまで INSERT しない。
2. **上書き経路を持たない**: 本モジュールは `config` への UPDATE／DELETE 文を持たない。
   仮に持っても保護トリガ（s0-contract §2）が ABORT するため、DB 層とアプリ層の二重で
   append-only が成立する。
3. **fail-open を作らない**: `get` の既定値は「安全側（保守的）」の値だけを持つ表から引く。
   表にない key を要求されたときに 0・空・無制限のような値を作って返さない。
4. `<profile_key>.` 接頭は S0 では**運用規約**であり、`set`／`get` は名前空間を検査しない
   （機械的強制は FR-34 の S1 — [brand-isolation-foundation.md](brand-isolation-foundation.md) §1）。

## §3 テスト実装方針

⑥の割当（`du-contracts.json` の DU-12 `apis[].ut`）が正本。実装は test-first で赤→緑にする。

| # | テスト | 方針 |
|---|---|---|
| 1 | 履歴 | 変更後に旧行が残り `supersedes_config_id` が連鎖することを assert |
| 2 | reason 必須 | `reason` 空の `set` が `ConfigReasonMissing`＋行数不変 |
| 3 | 同時刻衝突 | 同一 (key, changed_at) の INSERT が `IntegrityError`・値不変 |
| 4 | 直接改変 | 生 SQL の UPDATE／DELETE が保護トリガで ABORT |
| 5 | 有効値解決 | 最新行が型変換つきで返る |
| 6 | 不在 key | 既定値ありは既定値、なしは fail-close |

## §4 trace 表

実装単位ごとの API・AC・TC・UT の対応は
[implementation-units.json](implementation-units.json)（機械可読の正本）が持つ。

| 実装単位 | DU | AC | TCC |
|---|---|---|---|
| `set`（append-only 履歴・reason 必須・同時刻拒否） | DU-12 | AC-33-1・AC-33-2・AC-33-4・AC-33-5・AC-33-6 | TCC-33-1・TCC-33-2・TCC-33-4・TCC-33-5・TCC-33-6 |
| `get`（有効値解決・安全側既定値） | DU-12 | AC-33-3 | TCC-33-3 |

## 5. 実装単位（implementation_units）

責務は DU の **API 1 本**へ接続する。API・AC・TC・UT の対応の機械可読な正本は
[implementation-units.json](implementation-units.json)（`G-L6-IMPLEMENTATION-TRACE` が
DU／API の実在・pre/post への責務の明記・AC／TC／UT の実在と対応を fail-close 検査する）。

| unit_id | DU | API | 責務 | AC |
|---|---|---|---|---|
| IU-CONFIGSTORE-01 | DU-12 | `get` | key ごとに changed_at 最大の行を有効値とし、value_type に従って型変換して返す（read-only） | AC-33-3 |
| IU-CONFIGSTORE-02 | DU-12 | `set` | 旧行を UPDATE/DELETE せず新行を INSERT し、supersedes_config_id に直前の有効行を連鎖… | AC-33-1, AC-33-2, AC-33-4, AC-33-5, AC-33-6 |
