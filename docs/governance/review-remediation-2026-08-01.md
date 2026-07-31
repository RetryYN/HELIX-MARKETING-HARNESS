# 外部レビュー是正台帳 2026-08-01

> status: active。2026-07-31 受領の外部レビュー（総合 76/100・S0.1 実装 NO-GO 判定）への対応記録。
> PO 指示 = /goal「レビュー対応完遂。」（2026-08-01）。P0 は本コミットで是正、P1 は出口条件つきで台帳管理。

## P0 — 本コミットで是正済み

| # | 指摘 | 対応 |
|---|---|---|
| P0-1 | 状態機械が非決定的（複合 from、同一キーで failed/escalated 分岐、validator のスラッシュ除外） | s0-contract §3 と transitions.json を 1 行 1 状態へ正規化。失敗分類をイベントで確定（non_retryable_failure→failed、escalate/fatal_failure→escalated、verify_fail_exhausted 新設）。loop_runs failed へ到達経路を追加。G-TRN-UNIQ/REACH/TERM/GUARD を新設し、G-TRN-ST の検査除外を撤廃 |
| P0-2 | 正準 DDL と詳細設計の乖離（step_key/attempt/lease なし、config トリガなし、playbooks 失敗数なし） | tasks へ step_key・attempt・lease_owner_execution_id・lease_expires_at・heartbeat_at・row_version＋`UNIQUE(loop_run_id, step_key, attempt)`。config/evidence/state_transitions に append-only トリガ。playbooks へ consecutive_failures・last_failure_at。§1 に WAL・busy_timeout・単一 writer 方針 |
| P0-3 | 外部副作用のクラッシュ窓（WP 成功→ローカル記録前クラッシュで再送リスク） | `external_operations` テーブル新設（prepared→sent→confirmed/rejected/unknown、各段コミット）。下書きと公開は別 idempotency key。WP 側 meta key 照合。§3.3・WF-WP-2・⑤DU-02/04/17・④ITC-06・⑥UT-09（最危険 kill point の拒否テスト）へ反映 |
| P0-4 | 承認・baseline が内容非束縛（digest なし、JSON/validator/CI が baseline 外） | approvals.md に digest 列（対象 MD sha256 先頭 12）を追加し G-CONFIRM-DIGEST で検査。baseline に artifacts（JSON 正本・DDL・validator・CI・CLAUDE.md/AGENTS.md・hook）を追加し G-BASE-ART で検査。`--update-baseline` は承認 receipt がないと拒否 |
| P0-5 | commit/push 阻止 hook が Claude 専用・素通り条件あり | hook を fail-close 化（JSON 解析失敗=exit 2）、`git -C` 等グローバルオプション越しの commit/push を正規表現で検出。実停止境界は GitHub branch protection（Docs CI required status — 設定状況は本台帳末尾） |
| P0-6 | エージェント分離が ID 違いだけで成立 | `agents.principal` 列＋`agent_executions` テーブル（principal／execution／lineage）。claim・verify_pass ガードと DU-03 assigner を principal 比較へ変更。lease は execution 単位 |
| 意味整合 | ゲート件数・UTC 数が文書間で乖離（51/52/60/61 が並存） | 散文から件数ハードコードを撤去し baseline.json の gate_count を単一正本化。G-COUNT-SYNC が手書き表記の乖離を fail-close 検出 |

## P1 — 出口条件つき繰延（次スライス前に解消）

| # | 指摘 | 方針・出口条件 |
|---|---|---|
| P1-1 | 戦略層の型不足（plan_json 等が自由 JSON） | S2 のスキーマ部分（segment_context / hypothesis / experiment / metric_definition 等）を S1 学習ループより前へ移す。**出口: S1 着手前に schema 定義を s1-contract として confirmed** |
| P1-2 | 上位ループの月次固定がチャーター思想と矛盾 | LP-U を「月次観測＋イベントトリガー（成長状態・仮説棄却・環境変化・証拠閾値）の戦略更新」へ改訂。**出口: charter v0.4 改版時に LP-U 要件を同時改訂** |
| P1-3 | X ブラウザ自動化の PoC 前提 | **本コミットで前倒し是正済み**: X ブラウザ書込みは事前 prohibited（BR-M-X-4・POC-01 rejected/discard・RSK-01・MR-X-3 改訂）。公式 API 採用時のみ自動化を再検討 |
| P1-4 | 媒体調査に出典正本なし（source URL・digest・claim 構造） | br-media JSON を claim/sources/expires_at 構造へ拡張し、実行直前再検証を接続レジストリの契約に含める。**出口: S0.3（接続レジストリ実装）開始前** |
| P1-5 | CI が実装開始には不足（pytest・ruff・型・migration・secret scan 等） | **出口: S0.1 最初の実装コミットより前に** pytest+coverage・ruff・pyright・import-linter・migration 試験・secret scan・shellcheck/actionlint を CI へ追加（⑥ §5・CLAUDE.md の既存約束と統合） |
| P1-6 | JSON 単一正本＋MD 自動生成への移行 | 段階導入: 本コミットで digest/artifact 束縛まで実施。MD 自動生成化は **出口: charter v0.4（authority manifest）で判断** |
| P1-7 | charter v0.4（authority manifest・ADR-006 統合・T-REVIEW 責務・Python 版統一） | Python 版は本コミットで 3.14 に統一（tech-stack 正、CI・基本設計を追随）。残りは **出口: S0.1 完遂後の charter 改版** |

## GitHub 側停止境界

- 目標: main への直 push 禁止・PR 必須・required status = Docs CI（markdownlint / requirements-gates / link check）。
- **設定済み（2026-08-01、`gh api` で適用確認）**: main に required status checks
  （Markdown lint / Requirements integrity gates / Internal link check、strict）、force-push・削除禁止。
  `enforce_admins=false` のため owner（PO・エージェント運用）は bypass 可 — 第三者・非管理経路の
  push は CI green なしでは main に入らない。
