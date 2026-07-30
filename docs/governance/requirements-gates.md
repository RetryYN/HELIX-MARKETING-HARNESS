# 要件整合ゲート台帳 v0.1

> status: **active**（2026-07-31 導入）。実体は [scripts/validate_requirements.py](../../scripts/validate_requirements.py)、
> CI（Docs CI / requirements-gates ジョブ）で push/PR ごとに fail-close 実行。1 件でも FAIL = CI 赤。
> ゲートの追加・変更はスクリプトと本台帳を同時に更新すること。

| ゲート | 検証内容 | 違反の意味 |
|---|---|---|
| G-JSON | json/ 配下の全ファイルが構文的に妥当 | 壊れた正本 |
| G-CNT-BR/REQ/FR/NFR/AC/ACDEF/FN/BRM/MR/WF | JSON 件数 = MD の分母（BR31・REQ45・FR36・NFR10・AC19+deferred17・FN61・BR-M70・MR54・WF44） | MD↔JSON の同期漏れ、分母のサイレント変更 |
| G-UNIQ-* | BR/REQ/FR・NFR/AC/FN の ID 重複ゼロ | ID 衝突 |
| G-TRC-BR | s0/trace.json が全 31 BR をカバー | トレース断絶（BR が要件へ降りていない） |
| G-TRC-AC | AC の target が実在する FR | 宙に浮いた受入条件 |
| G-GWT | AC 全件に非空の Given/When/Then | 機械検証できない AC（AP-4 相当） |
| G-S0-CNT / G-S0-SET | S0.1〜S0.3 の fn_ids が 25 件・重複なし・function-list の slice=S0 集合と完全一致 | スコープのサイレント増減 |
| G-DDL-SYNC | json/s0/ddl.sql が s0-contract の DDL ブロックと一致 | 正準 DDL の二重化・乖離 |
| G-DDL-APPLY | DDL が空 SQLite へ適用でき FK/integrity 検査が通り 21 テーブル | 実行不能なスキーマ |
| G-EVK | evidence kind 10 種が JSON 契約と DDL の CHECK で同一集合 | 証跡語彙の乖離 |
| G-TRN-ENT / G-TRN-ST | 遷移表の entity が loop_runs/tasks、from/to 状態が DDL enum 内 | 実装不能な状態機械定義 |
| G-CONFIRM | status: confirmed を名乗る文書が approvals.md に承認行を持つ | freeze 偽装（HELIX gate-confirm 相当） |
| G-SRC-FRESH | br-media 各媒体の structure_checked が 90 日以内 | 出典腐敗（媒体規約・上限は変わる。HELIX source-ledger-freshness 相当） |
| G-POC-EXIT | PoC が出口 2 軸 schema（decision_outcome × promotion_strategy）に適合、confirmed には strategy 必須 | PoC の独り歩き（HELIX poc 規律相当） |
| G-SUBSTANCE | 全エンティティに 8 文字以上の本文実体 | 空・スタブ本文の完了僭称（HELIX AP-13 相当） |
| G-WIRING | スクリプトの全ゲート ID が本台帳に掲載され、CI がスクリプトを呼ぶ | ルールの配線漏れ・死蔵（HELIX lint-wiring 相当） |

## 運用

- 分母を意図的に変える場合（BR 追加等）は、MD・JSON・本スクリプトの期待値を **同一コミット**で更新する
  （ゲートが赤のままの main を作らない）
- S1 以降で AC・WF・FN が増えたら、対応するゲート期待値の更新もそのスライスの完了条件に含める
- 導入時の実績: 初回実行で遷移表 `to` への注記混入 1 件を検出・是正（ゲートの有効性確認済み）
