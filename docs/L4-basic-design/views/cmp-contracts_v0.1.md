<!-- GENERATED FILE — 編集禁止。正本は docs/L4-basic-design/canonical/components/cmp-contracts.json。再生成 = python3 scripts/render_views.py -->

# コンポーネント設計契約（CMP/SCM contracts）v0.1

> status: **confirmed**（2026-08-01 PO 承認 — receipt 2195391c9342）。JSON 内容正本の生成ビュー（全層再降下 §6）
> 各 CMP/SCM に 11 観点の設計契約を必須化（G-CMP-INTERFACE）。独立設計書とペアで読む。

## CMP-01 状態機械カーネル（kernel/state.py）

- **提供 interface**: transition(conn, entity_type, entity_id, event, actor_agent_id, details, clock) -> TransitionResult — 遷移表照合・guard 評価・状態 UPDATE・state_transitions INSERT を単一 transaction で実行／register_guard(event, fn) -> None — event ごとの純関数 guard の登録制配線（未登録 event の許可遷移は FatalError）／TransitionResult(entity, from_state, to_state, transition_id) — frozen dataclass の遷移結果／戦略層 start ガード（SCM-03）: loop_runs pending→start で validate_strategic_brief（CMP-02 提供）を呼び、無効 brief は GateRejected
- **要求 interface**: CMP-05 db.connect() が返す Connection（PRAGMA foreign_keys=ON 保証）／遷移表 docs/L3-system-requirements/canonical/schemas/s0/transitions.json（パッケージデータ同梱）／CMP-02 validate_strategic_brief（lower run start ガードの brief 検証実体）／Clock 注入（現在時刻の直接取得禁止）
- **責務境界**: やる: (現状態, イベント) の遷移表照合、guard 実行、loop_runs/tasks の状態 UPDATE、state_transitions への許可・拒否証跡記録、終端状態からの遷移拒否、retry_count 管理（verify_fail guard 内のみ）。やらない: タスク発行・WF 実行（CMP-02）、ゲート判定の実体（CMP-03 が guard として供給）、外部 I/O、遷移表の定義（s0-contract §3 が正準）。
- **依存方向**: ドメイン層（kernel）。cli/CMP-02 から呼ばれ、CMP-05（db）・CMP-03（guard 経由）に依存する。基盤層からは依存されない。fail-close の二極の一方（もう一方は CMP-03）。
- **データフロー**: イベント＋entity_id 入力 → 遷移表照合 → guard を DB 現在状態で評価 → 成立時 loop_runs/tasks UPDATE＋state_transitions INSERT（同一 transaction）→ TransitionResult 返却。拒否時は rejected 行を記録し DB 不変。
- **状態所有者**: loop_runs.state／tasks.state／state_transitions（業務状態遷移の唯一の書込み主体。kernel＋ストア層原則） ／ **transaction 所有者**: 本 CMP（1 状態遷移 = 1 transaction。guard・状態更新・遷移ログを単一 BEGIN/COMMIT で所有）
- **エラー分類**: TransitionRejected: 遷移表不一致・guard 不成立・終端からの遷移要求 → GateRejected 系。DB 不変で拒否行のみ記録／GateRejected: 状態・DB を変更しない拒否の正規化型（brief 検証失敗・claim 資格違反等を含む）／FatalError: 未登録 event の許可遷移（配線漏れ）・遷移表破損 → 即停止・escalate
- **degradation／復旧**: クラッシュ時は transaction ごと消え中間状態が残らない（申し送りなし — BR-A1）。再開はプロセス再起動後に loop_runs/tasks の現状態から続行。遷移表ロード不能は起動時 FatalError で fail-close。
- **セキュリティ境界**: 秘密を扱わない。構造化ログ（FN-704 二重化）には entity/event/guard_result/duration のみで本文・credential を含めない。brand/profile 隔離は guard が business_profile_id スコープで評価。
- **人間判断点**: なし（全自動。escalated への遷移後の対処は BR-H3 経由で人間）
- **trace**: FN = FN-101 FN-110 FN-704 ／ DU = DU-01 ／ 独立設計書 = state-machine-design_v0.1.md、error-taxonomy_v0.1.md

## CMP-02 オーケストレータ（kernel/orchestrator.py, assigner.py, workflow.py）

- **提供 interface**: issue_task(conn, loop_run_id, step, clock) -> int — 決定的 idempotency_key でのタスク発行・冪等再利用。playbook_repair は破損版IDをepisodeとし終端後も再発行しない／claim(conn, task_id, execution_id, clock) -> None — row_version 楽観ロックによる lease 取得（author 資格検査つき）／run_microloop(conn, task_id, executor, verifier, retry_limit_key) -> MicroloopResult — submit→verify 反復、retry_limit 到達で escalate／resume(conn, entity_type, entity_id, clock) -> ResumeAction — s0-contract §3.3 再開規則の実装（判断根拠は DB 行のみ）／assign(conn, author_role, verifier_role) -> Assignment — principal の異なる active agent 組の割当（自己審査封じ）／load(conn, workflow_key, version) -> WorkflowDef ／ run_step(conn, task_id, step, ctx) -> StepOutcome — WF 定義の schema 検証つき読込と実行／issue_strategic_brief(conn, brief, clock) -> int — 正準化 JSON の SHA-256 digest 決定計算つき brief 版発行（SCM-02）／supersede_strategic_brief(conn, old_brief_id, new_draft, clock) -> int — 新版 INSERT＋旧版 superseded を単一 transaction（SCM-02）／validate_strategic_brief(conn, brief_id, held_digest, clock) -> ValidBrief — active・digest 一致・期間内の検証（SCM-03 の実体）／generate_tactical_learning_packet(conn, loop_run_id, packet, clock) -> int — 下位終端遷移と同一 transaction での TLP 生成（SCM-04）／get_tactical_learning_packet(conn, loop_run_id) -> TlpRecord | None — 上流が読む唯一の還流読取り口
- **要求 interface**: CMP-01 transition()（すべての状態変更はここ経由）／CMP-03 ゲート API（require_pair／check_complete 等 — guard・公開前検査）／CMP-04 evidence.record()（ステップ出力の証跡化）／CMP-05 db.connect() ／ CMP-06 config.get()（retry_limit・lease_ttl_sec 等）／CMP-08 read-only DOM 取得／CMP-09 record_failure()・install_repaired_version()（repair 複合 transaction で同じ conn へ参加）／CMP-10〜13 コネクタ・制作・計測 API（呼ぶだけ — 逆依存なし）／Clock/Rng 注入
- **責務境界**: やる: タスク発行・割当・lease・マイクロループ・WF ステップ実行の進行制御、再開規則、playbook_repair子taskの一意発行と版切替の複合transaction調停、brief 発行/検証/supersede と TLP 生成（戦略層 S0 拡張）。やらない: 拒否判定の実体（CMP-01/03 に集約）、DOM読取りや版保存SQLの実装（CMP-08/09へ委譲）、証跡の直接 INSERT（CMP-04 経由）、遷移の直接 UPDATE（CMP-01 経由）。
- **依存方向**: ドメイン層（kernel）。cli から呼ばれ、CMP-01/03/04/05/06 に依存し、connectors/content/measure を呼ぶだけ（単方向 cli→kernel→gates→基盤）。
- **データフロー**: ループステップ到達 → WF 定義からtasks行生成（冪等）→割当・claim→ステップ実行→外部操作証跡化→状態遷移。playbook破損時はCMP-09のCAS結果を受け、同じtransactionで一意なrepair子taskを発行し、CMP-08のread-only DOM結果を別principalが検証した後、CMP-09の旧版retired＋新版active INSERTとverify_passを同じtransactionで確定する。戦略層はbrief/TLPを所定transactionで処理する。
- **状態所有者**: tasks の発行・lease 列（lease_owner_execution_id/lease_expires_at/heartbeat_at）、strategic_briefs／tactical_learning_packets への書込み（issue/supersede/generate の 3 API に閉域） ／ **transaction 所有者**: タスク採番・発行、playbook active→broken＋repair task発行、repair verify_pass＋旧版retired＋新版active INSERT、brief supersede、TLP生成の複合transactionを所有する。状態遷移の書込み自体はCMP-01、playbook SQLはCMP-09を同一conn/transactionへ参加させる。
- **エラー分類**: TaskIssuanceRejected: 割当不能・同一 principal のみ・workflow 不備での発行拒否 → GateRejected 系・発行しない／SelfReviewRejected: author=verifier（principal 同一）の組 → GateRejected（DB CHECK と二重防御）／GateRejected: claim 資格違反・無効 brief（status/digest/期間）・lower 以外への TLP 生成要求／SchemaVerificationFailed: brief/TLP/WF 定義の schema 不適合 → fail-close（FatalError 正規化）／RetryableError: ステップ実行の一時失敗 → retryable_failure 遷移へ還元／FatalError: WF 定義破損・照合不能な外部操作（unknown）→ escalated
- **degradation／復旧**: クラッシュ後はresume()がDB行のみから再開する。通常taskは同一(loop_run_id,step_key)の非終端行を再利用し、playbook_repairだけは破損版IDをepisodeとして終端行も再利用してattempt+1を禁止する。版切替の途中失敗はtransaction全体をrollbackし、broken旧版を現役のまま残す。
- **セキュリティ境界**: 秘密を保持しない（credential は CMP-07 経由でコネクタへ）。外部書込みはコネクタ経由のみで自らは行わない。brief/TLP は business_profile スコープで隔離。書込み系操作は NFR-7 のランダム間隔（Rng 注入）を尊重。
- **人間判断点**: escalated 後の対処と、brief シード投入（S0 受入基準 5 — シードコマンドは PO 起点）。それ以外は全自動
- **trace**: FN = FN-102 FN-103 FN-104 FN-105 FN-106 FN-107 ／ DU = DU-02 DU-03 DU-04 ／ 独立設計書 = error-taxonomy_v0.1.md

## CMP-03 ゲートエンジン（gates/）

- **提供 interface**: establish(conn, plan_id, review_task_id, review_evidence_id, clock) -> PairPass — review_pass 証跡 hash と制作 commit hash 一致時のみ pair 成立／require_pair(conn, plan_id) -> PairPass — passed 行がなければ GateRejected（PairPass は本 CMP のみ生成可能な検証済み値オブジェクト）／revoke_if_changed(conn, plan_id, current_commit_hash) -> bool — 企画/commit 変更検知で revoked／check_publishable(conn, plan_id, commit_hash) -> PairPass — require_pair＋hash 一致＋証跡完備の公開前一括ゲート／check_metric_type(metric_type) -> None — 有料指標型（cac/roas/ad_spend）の登録拒否（DB CHECK と二重）／check_domain(url_or_domain, denylist) -> None — 広告ドメイン denylist 照合（config 値）／check_complete(conn, task_id) -> None — required_evidence_json の全 kind 存在＋kind 規則再検証（done 遷移 guard）
- **要求 interface**: CMP-05 db.connect() が返す Connection（pair 状態・evidence の read）／CMP-04 の kind 別 validator（証跡完備検査の再検証で共有）／CMP-06 config.get()（denylist・閾値の動的取得）／Clock 注入（pair 成立時刻）
- **責務境界**: やる: ペア成立/失効判定、公開前ゲート、ゼロ広告費ゲート、証跡完備検査 — fail-close 拒否判定の一元集約点（CMP-01 と二極）。やらない: 状態遷移の実行（guard として CMP-01 に供給）、外部 I/O、業務状態の書込み（pair_plan_quality 行の INSERT を除き stateless）、例外的に通す分岐の保持。
- **依存方向**: ドメイン層（gates）。kernel（CMP-01/02）から呼ばれ、基盤層（db/evidence/config）にのみ依存。コネクタへは依存しない（拒否はコネクタ呼出し前に成立）。
- **データフロー**: 検査要求（plan_id/task_id/metric_type/url）→ DB 現在状態・config 値と照合 → 成立なら PairPass 等の検証済み値オブジェクト返却、不成立なら GateRejected（呼出し側はコネクタに到達しない）。
- **状態所有者**: pair_plan_quality 行（成立・revoked）のみ。それ以外は stateless（ゲートは業務状態を所有しない） ／ **transaction 所有者**: pair 成立/失効の INSERT/更新のみ所有。遷移 transaction は CMP-01（guard として同一 transaction 内で評価される）
- **エラー分類**: PairNotEstablished: 成立 pair 不在での公開系要求 → GateRejected・WP API を呼ばない／CommitHashMismatch: review_pass hash と制作 commit hash の不一致 → GateRejected（pair 不成立・revoke）／PaidMetricRejected: 有料指標型の登録・投入要求 → GateRejected（ゼロ広告費 — DB CHECK と二重）／UrlDenied: 広告ドメイン denylist 該当 → GateRejected／EvidenceIncomplete: required kind 欠落・kind 規則違反 → GateRejected（done 遷移不成立）／FatalError: PairPass 偽造検知（sentinel token 不一致）→ 即停止
- **degradation／復旧**: denylist・閾値 config 行が取得不能なら fail-close（通さない）。ゲート自体は stateless で復旧不要 — 再実行は DB 現在状態からの再判定。pair は commit 変更検知で自動 revoke され再確立を要求。
- **セキュリティ境界**: PairPass の構築独占（sentinel token＋frozen dataclass）でゲート未通過の公開経路を型・実行時の両面で封鎖。ゼロ広告費・denylist で有償経路を遮断。秘密は扱わない。
- **人間判断点**: なし（全自動。ゲート緩和は config 変更＝人間の承認経路のみ）
- **trace**: FN = FN-201 FN-202 FN-203 FN-204 FN-205 FN-206 FN-207 FN-208 ／ DU = DU-05 DU-06 DU-07 DU-08 ／ 独立設計書 = error-taxonomy_v0.1.md

## CMP-04 証跡ストア（evidence/store.py）

- **提供 interface**: record(conn, task_id, kind, value, payload, clock, *, asset_id, commit_hash, external_operation_row_id, external_operation_id, operation_log_evidence_id, file_path, file_hash, created_by_agent_id) -> int — kind型契約検証つきINSERT。provider external_operation_idは任意／for_task(conn, task_id, kind=None) -> list[Evidence] — read-only 参照／exists(conn, task_id, kind, value) -> bool — 存在照会（UPDATE/DELETE API は提供しない）／kind 別 validator 群 — s0-contract §2.1 の必須キー・列整合・追加検証（CMP-03 の証跡完備検査と共有）
- **要求 interface**: CMP-05 db.connect() が返す Connection／credential/secret 混入検査パターン集合（CMP-07 secrets と共有、config 拡張可）／Clock 注入（created_at）
- **責務境界**: やる: evidenceの型契約検証、INSERT、secret混入拒否、read-only参照。operation_logはsent external_operationsへexternal_operation_row_idで双方向1:1、task/effect/policy_category/rate_scope/service/operation/correlation/request hash/sequence/result同値を検証しtrigger final化する。published_urlはoperation_log_evidence_idで先行operation_logへ束縛しpayload local row IDを一致させる。やらない: 証跡内容生成、UPDATE/DELETE、業務状態遷移、外部I/O。 actual実外部I/Oの各operation_logはevidence.external_operation_row_idでsentに到達したexternal_operationsのlocal rowへexactly-oneに束縛し、execution_mode='actual'・effect・policy_category・rate_scope（writeはcanonical lowercase、readはSQL NULLかつpayload JSON null）・service・operation・correlation_key・request_hash・request_sequence・resultを同値にし、INSERT triggerでstatusをconfirmed/rejected/unknownへfinal化する。provider external_operation_idは任意。
- **依存方向**: 基盤層（evidence）。kernel・gates・コネクタのストア副層から呼ばれ、db にのみ依存。ドメイン層を import しない。
- **データフロー**: 証跡候補→kind型契約・混入検査→operation_logならsent外部行との1:1/属性一致を検証してINSERT＋trigger final化、published_urlなら先行operation_log自己FK/local row一致を検証→evidence_id返却。違反はGateRejectedでDB不変。
- **状態所有者**: evidence テーブル（append-only。書込みの唯一の入口） ／ **transaction 所有者**: 単発 INSERT は自トランザクション。遷移 guard・TLP 生成等の合成時は呼出し側（CMP-01/02）の transaction に参加
- **エラー分類**: SchemaVerificationFailed: kind 別必須キー欠落・列整合違反 → GateRejected・INSERT しない／CredentialLeakDetected: secret/credential パターンの混入検知 → GateRejected・記録拒否／SelfReviewRejected: review_pass の reviewer=author → GateRejected／IntegrityError: UNIQUE(task_id, kind, value) 重複・FK 不能 → GateRejected（DB 制約と二重）
- **degradation／復旧**: stateless（テーブル以外の状態なし）。INSERT 失敗は transaction ごと消え中間状態なし。再実行は同一入力の再検証・再 INSERT（重複は UNIQUE で拒否され冪等）。
- **セキュリティ境界**: secret 混入検査の実装点（CMP-07 の scan と対）。証跡は append-only で改竄不能（UPDATE/DELETE 非提供＋トリガ）。business_profile スコープは task 経由で継承。
- **人間判断点**: なし（全自動）
- **trace**: FN = FN-208 FN-701 FN-703 ／ DU = DU-09 ／ 独立設計書 = error-taxonomy_v0.1.md

## CMP-05 DB 基盤（db/）

- **提供 interface**: connect(path) -> Connection — 唯一の接続入口。PRAGMA foreign_keys=ON・row_factory・config 保護トリガ存在確認（未適用 DB は FatalError）／apply_all(conn, migrations_dir, clock, applied_by) -> list[Applied] — 連番 migration 適用・checksum/applied_at/applied_by を schema_version へ記録／verify(conn) -> None — foreign_key_check／integrity_check／25 テーブル存在／TLP 孤児検査（packet なし終端 lower run = 0 件）／戦略層 DDL（SCM-01）: strategic_briefs／tactical_learning_packets テーブル＋保護トリガ（両テーブルの append-only・brief 状態遷移／valid_until・TLP 整合）＋loop_runs.strategic_brief_id/digest 列と lower CHECK（migration 0001 に内包）
- **要求 interface**: migrations/NNNN_description.sql（不変・連番。0001 = s0-contract §2 正準 DDL と等価）／Clock 注入（applied_at）／sqlite3 標準ライブラリのみ（ORM 不採用）
- **責務境界**: やる: 正準 DDL の migration 適用・checksum 検証・接続管理・トリガによる保護（config UPDATE/DELETE 拒否、strategic_briefs/TLP の append-only 強制）・整合検査。やらない: 業務ロジック、DDL の定義（s0-contract §2 が正準 — 本 CMP は適用装置）、上位層 import。
- **依存方向**: 基盤層の最深部（db）。全層から connect() 経由で使われ、何にも依存しない（sqlite3 標準ライブラリのみ）。
- **データフロー**: migration SQL → 連番順適用＋checksum 記録 → schema_version 行。接続要求 → PRAGMA/トリガ検査済み Connection 返却。verify → 整合検査結果（違反は FatalError）。
- **状態所有者**: schema_version テーブルと DB 物理スキーマ全体（テーブル・トリガ・CHECK の存在保証）。業務行の内容は所有しない ／ **transaction 所有者**: migration 適用単位（1 migration = 1 transaction）。業務 transaction は各所有者（CMP-01/02 等）
- **エラー分類**: MigrationChecksumMismatch: 適用済み migration の checksum 不一致 → FatalError・適用停止／MigrationVerifyFailed: verify() の整合検査失敗（FK/integrity/テーブル欠落/TLP 孤児）→ FatalError・escalate／IntegrityError: FK/UNIQUE/CHECK 違反（保護トリガ発火含む）→ 呼出し側で 3 系へ正規化／FatalError: 未適用 DB での connect()・同 version 重複適用 → 即停止
- **degradation／復旧**: migration は連番・不変・checksum 記録で再実行安全（適用済みはスキップ、改変は検知停止）。DB 破損は verify() で検出し escalate（自動修復しない — fail-close）。昇格は s0-contract §5.2 の手順のみ。
- **セキュリティ境界**: credential を保存しない（秘匿は CMP-07 のファイルストア）。保護トリガで append-only 契約（config・strategic_briefs・TLP）を DB 層でも強制。DB ファイルはローカルのみ・外部書込みなし。
- **人間判断点**: migration 昇格手順（§5.2）の実施判断。適用・検証自体は全自動
- **trace**: FN = FN-105 FN-306 FN-701 FN-702 FN-703 ／ DU = DU-10 DU-11 ／ 独立設計書 = db-design_v0.1.md、error-taxonomy_v0.1.md

## CMP-06 config 管理（config/store.py）

- **提供 interface**: set(conn, key, value, value_type, reason, agent_id, clock) -> int — append-only INSERT＋supersedes_config_id 連鎖（reason 必須）／get(conn, key, default=None) — changed_at 最大行を value_type で型変換して返却
- **要求 interface**: CMP-05 db.connect() が返す Connection（config 保護トリガ適用済み）／Clock 注入（changed_at）
- **責務境界**: やる: 設定値の履歴保持（append-only・supersedes 連鎖）、reason 必須強制、最新値の型変換取得。やらない: 設定値の妥当性判断（利用側の責務）、UPDATE/DELETE（トリガと二重で拒否）、秘密の保管（CMP-07）。全コンポーネントのハードコード禁止（型×動的充填）を支える基盤。
- **依存方向**: 基盤層（config）。全層から get() で読まれ、db にのみ依存。ドメイン層を import しない。
- **データフロー**: 設定変更（key/value/reason）→ 同 key 同時刻検査 → 新行 INSERT＋supersedes 連鎖。参照は key → changed_at 最大行 → 型変換値。
- **状態所有者**: config テーブル（append-only 履歴。設定値正本） ／ **transaction 所有者**: set() の単発 INSERT（自トランザクション）
- **エラー分類**: ConfigAppendOnlyViolation: UPDATE/DELETE の試行 → トリガ＋API 非提供で拒否（FatalError 正規化）／ConfigReasonMissing: reason 欠落の set() → GateRejected・INSERT しない／GateRejected: 同一 key 同一時刻の INSERT → 拒否（履歴の全順序保証）
- **degradation／復旧**: stateless ロジック＋append-only テーブルで復旧は不要。誤設定は新行 INSERT（supersedes）でのみ是正 — 履歴は消えない。key 不在時は default 返却か呼出し側 fail-close。
- **セキュリティ境界**: credential を config に置かない（CMP-07 に分離 — 混入は CMP-04/07 の検査対象）。denylist・レート間隔・上限値等のゲート強度を決める値の変更履歴を全保持し、ブランド別値は business_profile スコープ key で隔離。
- **人間判断点**: 設定変更の reason 記入（変更は人間またはエージェントの明示操作のみ。自動書換えなし）
- **trace**: FN = FN-301 FN-302 FN-303 FN-304 FN-305 FN-306 ／ DU = DU-12 ／ 独立設計書 = brand-isolation-design_v0.1.md、error-taxonomy_v0.1.md

## CMP-07 接続レジストリ・秘匿ストア（registry/）

- **提供 interface**: resolve(conn, service, operation) -> Route — route_type 優先順（mcp → api → browser → 有償）の宣言解決。切替はデータ変更のみ（AC-41）／get_credential(name, scope: test|prod) -> Secret — Fernet 復号。Secret は repr/str 伏字 wrapper／check_endpoint(secret, endpoint_url) -> None — scope×endpoint 不正組合せ（test→本番／prod→Docker・mock）の接続前拒否／scan(targets, conn) -> list[Finding] — repo・SQLite 全行・構造化ログの平文 credential 走査（TC-047 実装点）
- **要求 interface**: cryptography（Fernet）による暗号化ファイルストア（test/prod 物理別ファイル）／CMP-05 db.connect() が返す Connection（レジストリ宣言行・scan 対象）／credential パターン集合（CMP-04 の混入検査と共有正本）
- **責務境界**: やる: サービス×操作→経路の宣言解決、credential の暗号化保管・復号・伏字化、test/prod 分離検査、平文漏えい走査。やらない: 経路の実行（コネクタ）、業務状態の書込み、有償経路の自動選択（denylist/ゲートは CMP-03）、credential のログ・DB・evidence への書込み（禁止事項そのもの）。
- **依存方向**: 基盤層（registry）。kernel・コネクタから呼ばれ、db と暗号化ファイルにのみ依存。ドメイン層を import しない。
- **データフロー**: 経路要求（service/operation）→ 宣言 JSON 照合 → 優先順で有効 Route 返却。credential 要求（name/scope）→ Fernet 復号 → Secret（メモリ内のみ）→ endpoint 突合 → コネクタへ。
- **状態所有者**: レジストリ宣言行と暗号化秘匿ファイル（test/prod 別）。業務状態は所有しない ／ **transaction 所有者**: なし（宣言行の変更は運用データ操作。業務 transaction に参加しない）
- **エラー分類**: RouteNotRegistered: 該当経路の宣言なし → FatalError（暗黙フォールバック禁止）／SecretUnavailable: credential 不在・復号失敗 → FatalError・接続しない／ProductionWriteDenied: test credential→本番 endpoint 等の scope 不正組合せ → FatalError・接続前拒否／CredentialLeakDetected: scan() での平文検知 → escalate（TC-047）／PaidRouteDenied: 有償 route_type の解決要求がゲート未通過 → GateRejected（CMP-03 と連携）
- **degradation／復旧**: 経路不在・復号失敗は fail-close（代替経路の暗黙選択なし — 切替は宣言データ変更のみ）。秘匿ファイル破損はバックアップからの手動復旧（自動再生成しない）。scan は定期・独立実行可能で本体障害と分離。
- **セキュリティ境界**: 秘密一元管理の正本。Fernet 暗号化・復号値メモリ内のみ・伏字 wrapper・test/prod 物理分離＋endpoint 突合・平文走査 — 本システムの秘密境界そのもの。外部書込み経路の宣言もここが正本で、Docker WP 以外の書込み経路は登録しない。
- **人間判断点**: credential の初期登録・ローテーション、経路宣言の変更（データ変更 = 人間承認経路）
- **trace**: FN = FN-401 FN-408 FN-411 FN-412 ／ DU = DU-13 DU-14 ／ 独立設計書 = external-if-design_v0.1.md、error-taxonomy_v0.1.md

## CMP-08 ブラウザ基盤（connectors/browser.py）

- **提供 interface**: launch(headed, storage_state_path=None) -> BrowserSession — Playwright 起動・storage_state 保存/再利用・headed/headless 切替（WSLg）／screenshot(session, url, out_path) -> Path — URL到達確認つきcapture（file_hash固定は呼出し側）／run_playbook(conn, session, playbook, intent, rng, clock) -> BrowserResult — actual外部read/writeのpolicy実行。mock/dry-runはSimulatedBrowserResult
- **要求 interface**: Playwright ランタイム／CMP-07 get_credential()／check_endpoint()（ログイン credential の供給と接続前検査）／storage_state 永続ファイル（セッション再利用）／CMP-04 evidence.record()／external_operations（actual 1要求=1行=operation_log 1行）／CMP-06 config.get()（external_write_policy・rate scope/cap・URL allow-list）
- **責務境界**: やる: ブラウザ起動・セッション永続・スクリーンショット、actual外部操作のeffect/policy_category/canonical rate_scope検証、external_operations prepared/sent管理、DU-09経由operation_log trigger final化。writeは閉集合policyだけ、note等根拠なしwriteはpreflight拒否。mock/dry-run/接続前拒否は外部両テーブル0。やらない: セレクタ・手順保持（CMP-09）、業務状態遷移、閉集合外write。 actual実外部I/Oの各operation_logはevidence.external_operation_row_idでsentに到達したexternal_operationsのlocal rowへexactly-oneに束縛し、execution_mode='actual'・effect・policy_category・rate_scope（writeはcanonical lowercase、readはSQL NULLかつpayload JSON null）・service・operation・correlation_key・request_hash・request_sequence・resultを同値にし、INSERT triggerでstatusをconfirmed/rejected/unknownへfinal化する。provider external_operation_idは任意。
- **依存方向**: コネクタ層（connectors）。kernel（CMP-02）・計測（CMP-13）から呼ばれ、CMP-07（credential）と Playwright にのみ依存。業務テーブルへ直接触れない。
- **データフロー**: 起動→Playwright session→intentのcategory/service/operation/endpoint/rate_scope preflight→actualならexternal_operations prepared→外部I/O→sent→operation_log INSERT trigger final→BrowserResult(local row/log evidence ID必須、provider ID任意)。mock/dry-runは外部参照なしSimulatedBrowserResult。
- **状態所有者**: なし（stateless — storage_state ファイルは機構上の永続だが業務状態ではない） ／ **transaction 所有者**: actual外部操作のprepared/sentを個別commitし、結果確定時のoperation_log INSERTはCMP-04 transactionでtrigger final化する。外部I/Oは業務transaction外
- **エラー分類**: RetryableError: 起動失敗・タイムアウト・ナビゲーション失敗 → retryable_failure 遷移へ還元／SecretUnavailable: ログイン credential 不在 → FatalError（CMP-07 から伝播）／FatalError: storage_state 破損で再ログイン不能・環境異常 → escalate
- **degradation／復旧**: 起動失敗はリトライ（retry_limit は config）。storage_state 失効は再ログインで再構築。ブラウザ経路自体が GA4 API の縮退経路であり、これも失敗すれば計測タスクは escalated（さらなる暗黙代替なし）。
- **セキュリティ境界**: credentialはCMP-07 Secret経由だけ。writeはpolicy_category閉集合とservice/operation/endpoint/rate_scopeの固定policyを接続前検証し、content_publishはDocker WPのみ。X・note等根拠なしwrite、unknown/偽装category、非canonical scopeは送信0。storage_stateはローカル保護。
- **人間判断点**: headed モードでの初回ログイン・CAPTCHA 等の人間介入（BR-H 系）
- **trace**: FN = FN-402 FN-403 FN-404 ／ DU = DU-15 ／ 独立設計書 = external-if-design_v0.1.md、error-taxonomy_v0.1.md

## CMP-09 攻略地図ストア（connectors/playbooks.py）

- **提供 interface**: get(conn, service, operation, route_type) -> Playbook — 同一 route の現役 active 版だけを取得（broken／retired は返さない）／record_success(conn, playbook_id, agent_id, clock) -> None — 現役 active 版の last_success_at 更新（AC-42）／record_failure(conn, playbook_id, clock) -> FailureRecord — active 版の失敗数を条件付き更新し、閾値到達時は broken episode の CAS 結果を返す／install_repaired_version(conn, broken_playbook_id, repair_task_id, procedure, selectors, agent_id, clock) -> Playbook — 検証済み repair task に束縛し、broken 旧版は retired 化＋version+1 active 版 INSERT、同taskで処理済みの retired 旧版は既存 successor のread-returnを行う
- **要求 interface**: CMP-05 db.connect() が返す Connection（playbooks テーブル）／CMP-06 config.get()（連続失敗閾値／playbook_repair_limit=1）／CMP-02 が所有する repair 複合 transaction（task 発行／verify_pass と同じ conn）／Clock 注入（last_success_at/last_failure_at）
- **責務境界**: やる: playbooks の現役版参照、active 版の成功/失敗記録、active→broken CAS、版内容を UPDATE しない append-only 新版発行。永続化はストア副層 playbooks_store に限定（生 SQL はここだけ — 基本設計 §1 規約 3）。やらない: DOM 取得・候補地図生成・検証方針（CMP-08／repair workflow）、loop_runs/tasks/evidence への直接書込み、修復試行数の決定（CMP-02）。
- **依存方向**: コネクタ層の所掌ストア副層。kernel・計測から呼ばれ、db/config にのみ依存。外部 I/O コードと分離。
- **データフロー**: route 要求→部分 UNIQUE で一意な active 版返却→実行結果で健全性を更新。閾値到達時は active→broken CAS 結果を CMP-02 へ返し、修復成功時は done repair task と旧版を照合して旧版 retired→version+1 active 版 INSERT の線形な版鎖を確定する。同一 repair task の再呼出しは retired 旧版から両束縛一致の successor を再読する。
- **状態所有者**: playbooks テーブル（route+version の版鎖、active/broken/retired、鮮度・健全性。手順・セレクタ・版束縛列は append-only） ／ **transaction 所有者**: 通常の record_success は単発 transaction。record_failure が broken 化する場合と install_repaired_version の新規版切替は独自に BEGIN/COMMIT せず、CMP-02 所有の複合 transaction に同じ conn で参加し、後続処理失敗時は版切替全体を rollback する。処理済み同taskのinstallは既存 successor をread-only再読する。
- **エラー分類**: PlaybookMissing: 該当手順書なし → FatalError（手順なしで操作を試みない — fail-close）／PlaybookBroken: broken 状態の手順書での操作要求 → 実行拒否・playbook_repair 経路へ（修復失敗後は人間の manual revision）／IntegrityError: FK・UNIQUE 違反 → GateRejected 正規化
- **degradation／復旧**: broken 版は操作参照を拒否し、CMP-02 が発行した同一 playbook_repair task を再開する。自動修復成功時は旧版を上書きせず新版で復帰し、版 INSERT 失敗は transaction 全体を rollback して broken 旧版を現役のまま残す。版切替後クラッシュは同task束縛の既存 successor を返し、自動修復失敗後は人が別の playbook_manual_revision task を明示発行する。
- **セキュリティ境界**: 手順書に credential を含めない（参照名のみ — 実値は CMP-07）。書込み系手順は S0 で登録しない。手順書は service スコープで管理されブランド横断の誤適用を防ぐ。
- **人間判断点**: 自動 repair 失敗後の別 playbook_manual_revision task 発行と候補地図の承認。自動 repair task は終端後も episode ledger として同じ ID を再読し、attempt+1 は発行しない
- **trace**: FN = FN-402 FN-403 FN-404 FN-405 ／ DU = DU-16 ／ 独立設計書 = external-if-design_v0.1.md、error-taxonomy_v0.1.md

## CMP-10 WP REST コネクタ（connectors/wp.py）

- **提供 interface**: create_draft(conn, task_id, pair_pass: PairPass, html, idempotency_key, clock) -> DraftRef — 下書き作成（idempotency 必須・事前照合）／publish(conn, task_id, pair_pass: PairPass, draft_ref, approval_evidence_id, idempotency_key, clock) -> PublishedRef — 公開（PairPass＋承認証跡必須）／register_asset(conn, task_id, published: PublishedRef, clock) -> int — 公開成功後の assets 行 INSERT（wp_media_id・canonical_url・content_hash）
- **要求 interface**: CMP-03 PairPass（require_pair/establish のみが生成 — 公開系の必須引数）／CMP-07 get_credential()（Application Password）／check_endpoint()／CMP-04 evidence.record()（operation_log／published_url 証跡の派生記録）／CMP-06 config.get()（Docker WP base URL allow-list・レート間隔）／external_operations(effect='write', policy_category='content_publish', rate_scope='wp')と1:1のoperation_log（sent行へのINSERT triggerでfinal化）
- **責務境界**: やる: WP REST外部書込み、content_publish/rate_scope='wp'/Docker WP固定policy、idempotency照合・再送抑止、external_operations prepared/sent管理、operation_log trigger final化、公開後assetsとpublished_url自己FK束縛。Ref DTOはlocal external_operation_row_id/operation_log_evidence_id必須・provider_operation_id任意。やらない: 公開可否判断、業務状態遷移、Docker WP以外へのwrite。 actual実外部I/Oの各operation_logはevidence.external_operation_row_idでsentに到達したexternal_operationsのlocal rowへexactly-oneに束縛し、execution_mode='actual'・effect・policy_category・rate_scope（writeはcanonical lowercase、readはSQL NULLかつpayload JSON null）・service・operation・correlation_key・request_hash・request_sequence・resultを同値にし、INSERT triggerでstatusをconfirmed/rejected/unknownへfinal化する。provider external_operation_idは任意。
- **依存方向**: コネクタ層（connectors）。kernel（CMP-02 の WF 実行）からのみ呼ばれ、CMP-03（型として）・04・06・07 に依存。業務状態を直接書かない（assets はストア副層 `_assets_store` 所掌）。
- **データフロー**: PairPass＋入力＋key→category/scope/endpoint preflight→actual実外部writeのexternal_operations prepared→WP送信→sent→operation_log INSERT trigger final→Ref(local row/log evidence ID)→assets INSERT→published_url(operation_log_evidence_id＋payload local row ID)→kernel遷移。
- **状態所有者**: external_operations 行（自操作分）と assets 行（ストア副層 `_assets_store` 経由）。loop_runs/tasks は書かない ／ **transaction 所有者**: external_operationsのprepared/sentを個別commit。結果確定時もsentの間にoperation_logをINSERTしtriggerでfinal化/evidence_id接続。assets INSERT後、published_urlを自己FK付きで別evidence transactionへ記録。外部操作は業務遷移transaction外
- **エラー分類**: PairNotEstablished: PairPass なしの公開系呼出し → 型レベルで不成立（GateRejected）／ApprovalRequired: 承認証跡なしの publish → GateRejected・送信しない／WpTargetDenied: Docker WP allow-list 外の base URL → FatalError・接続前拒否／ProductionWriteDenied: 本番 WP への書込み組合せ → FatalError（環境契約 §6）／RateLimitExceeded: レート節度違反の検知 → RetryableError（間隔をおいて再試行）／RetryableError: 一時的な HTTP 失敗（送信前）→ retryable_failure／FatalError: sent 後に照合不能（unknown）→ 再送禁止・escalated
- **degradation／復旧**: prepared=再送可。sentのWP照合自体を別external_read/rate_scope=NULL外部行＋payload rate_scope:nullのoperation_logとして記録し、確認結果により元writeのoperation_logをINSERTしてconfirmed/unknownへfinal化する。write再送禁止。confirmed済み同keyは結果補完のみ。
- **セキュリティ境界**: 外部書込み境界の本体 — 書込み先は Docker WP のみ（base URL allow-list を接続前検査）。credential は CMP-07 の Secret 経由・ログ不記載。書込みはレート節度（NFR-7 ランダム間隔・BR-31）に従う。公開経路は PairPass＋承認証跡の二重ゲート後のみ。
- **人間判断点**: 公開は承認（CMP-11 binding 承認）を経た後のみ実行（本 CMP 自身は判断しない）
- **trace**: FN = FN-406 FN-407 ／ DU = DU-17 ／ 独立設計書 = external-if-design_v0.1.md、error-taxonomy_v0.1.md

## CMP-11 承認通知（connectors/approval.py）

- **提供 interface**: request(conn, task_id, binding: Binding, transport, clock) -> int — binding 3 項目（subject/operation/at）提示の承認要求送出＋approvals 行 INSERT／receive_interaction(conn, raw_body, signature, timestamp, transport, clock) -> Decision — Discord署名・identity・replay・期限検証後にpendingをCAS確定／Binding(subject, operation, at) — frozen dataclass の束縛 3 項目
- **要求 interface**: ApprovalTransport interface（初期: Discord App、将来: Web UI / PWA、テスト: test double — actual/mock execution modeを明示）／CMP-04 evidence.record()（approval 証跡）／CMP-01 transition()（waiting／failed／escalated 遷移は kernel 経由）／CMP-06 config.get()（approval_retry_limit・有効期限）／approvals テーブル（ストア副層 approvals_store 経由）／external_operations（初期Discord通知approval_notification/rate_scope='discord' writeのみ）＋CMP-04 operation_log。inbound interactionは外部2表へ記録しない
- **責務境界**: やる: binding 3項目束縛の承認要求、実通知approval_notification writeの外部行/operation_log、署名検証済みDiscord interaction受領、approvalsのpending限定CAS＋approval証跡整合、binding不一致無効化。通知成立前のApprovalPassは循環するため要求しない。inbound interactionとmock/dry-runは外部両テーブル0。やらない: 承認判断、承認対象操作、状態遷移直接実行。 execution_mode='actual'でsentに到達した通知external_operations行だけがoperation_logを生成し、external_operation_row_id・effect='write'・policy_category='approval_notification'・rate_scope='discord'・correlation_key・request_hash・request_sequenceを同値束縛する。
- **依存方向**: コネクタ層（connectors）。kernel から呼ばれ、transport・evidence・config に依存。業務状態は kernel 経由でのみ動かす。
- **データフロー**: binding→approvals pending＋Discord通知write prepared/sent→operation_log trigger final→署名済みinteraction受領→identity・binding・expiry照合→pending限定CAS→approved証跡/evidence_id transaction、又はrejected/expired分類。inbound・preflight拒否・mockはprocess logのみ。
- **状態所有者**: approvals テーブル（ストア副層 approvals_store 所有）。loop_runs/tasks の状態は所有しない（kernel 経由） ／ **transaction 所有者**: 通知writeのprepared/sentを個別commitし、sent行へのoperation_log INSERT triggerでfinal化。`receive_interaction`はpending限定CASと、approved時のapproval証跡INSERT＋approvals.evidence_id更新を単一transaction。遷移transactionはCMP-01
- **エラー分類**: ApprovalBindingMismatch: 応答の binding 1 項目でも不一致 → 応答無効・pending 継続（GateRejected 系）／ApprovalRequired: 承認証跡なしでの後続操作要求 → GateRejected（CMP-10 側と対）／NonRetryableFailure: rejected 応答 → task failed（non_retryable_failure 遷移）／RetryableError: transport 送出の一時失敗 → 再送／FatalError: approval_retry_limit 到達（expired 反復）→ escalated
- **degradation／復旧**: Discord通知不通は再送（承認要求は冪等 — 同一 binding の重複要求は既存 pending を再利用）。expired は新しいbinding_atで再要求し、retry_limit 到達で escalated。interaction再送はnonce/idempotencyとpending限定CASで無害化し、クラッシュ後は approvals 行の状態から再開する。
- **セキュリティ境界**: 承認は binding 3 項目で対象を一意束縛し、すり替え・再利用を排除（外部書込みの人間ゲート）。通知本文に credential・記事本文全文を含めない。transport は差替 interface で本番/テストを分離。
- **人間判断点**: 承認・却下の判断そのもの（本 CMP の存在理由 — BR-H 系の実装点）
- **trace**: FN = FN-207 FN-409 FN-410 ／ DU = DU-18 ／ 独立設計書 = external-if-design_v0.1.md、approval-design_v0.1.md、error-taxonomy_v0.1.md

## CMP-12 制作・版管理（content/）

- **提供 interface**: generate(plan: PlanInput, workspace: Path, rng_seed: int) -> GeneratedSource — テンプレート＋種固定の決定的原稿生成（同一入力→同一 SHA-256 — AC-51）／commit_workspace(workspace, repo, message) -> str — commit 実行・hash 返却（40/64 桁検証）／link(conn, task_id, repository, commit_hash, paths, clock) -> int — commit_hash 証跡化（DU-09 経由）／restore(repo, commit_hash, dest) -> Path — 審査記録からの成果物ソース復元（AC-54）
- **要求 interface**: git（workspace の commit・restore）／CMP-04 evidence.record()（commit_hash 証跡）／Rng 注入（rng_seed — 乱数直呼び禁止）
- **責務境界**: やる: 企画入力からの決定的原稿生成（外部 I/O なし・純関数＋ファイル書出しのみ）、workspace の commit・hash 取得・証跡紐づけ・復元。やらない: 企画の生成（上流）、審査（CMP-03 ペアゲート）、公開（CMP-10）、業務状態の書込み。
- **依存方向**: 制作層（content）。kernel（WF 実行）から呼ばれ、git・evidence API にのみ依存。コネクタ・ゲートへ依存しない。
- **データフロー**: PlanInput＋rng_seed → テンプレート展開 → workspace へ記事ソース生成（決定的 hash）→ commit → hash 40/64 桁検証 → commit_hash 証跡（repository/paths 必須キー）→ 審査・公開は後続 WF ステップへ。
- **状態所有者**: なし（stateless — workspace/git は版管理正本であり業務状態ではない。証跡は CMP-04 所有） ／ **transaction 所有者**: なし（link の証跡 INSERT は CMP-04 の transaction。git 操作は DB transaction 外）
- **エラー分類**: RenderFailed: テンプレート展開・生成失敗 → RetryableError 正規化／CommitHashMismatch: hash 桁数・形式不正、復元時の hash 不一致 → GateRejected（証跡化しない）／UnversionedSourceRejected: commit されていないソースの証跡化・公開要求 → GateRejected／FatalError: git repo 破損・restore 不能 → escalate
- **degradation／復旧**: 生成は決定的（同一入力＋同一 seed → 同一 hash）なので再実行が常に安全。commit 失敗は workspace 再生成からやり直し可能。復元は commit hash があれば任意時点で再現可能（審査記録の再現性保証）。
- **セキュリティ境界**: 生成物・テンプレートに credential を含めない（CMP-04 混入検査が最終防衛）。外部送信なし（ローカル workspace・ローカル git のみ）。ブランドテンプレートは business_profile スコープで分離。
- **人間判断点**: なし（全自動。品質判断は後続のペア審査 — 人間/verifier 側）
- **trace**: FN = FN-501 FN-502 FN-503 FN-504 FN-505 FN-506 FN-507 FN-508 FN-511 FN-512 ／ DU = DU-19 DU-20 ／ 独立設計書 = error-taxonomy_v0.1.md

## CMP-13 計測（measure/）

- **提供 interface**: create_node(conn, node: KpiNodeInput) -> int — 階層・媒体タグ・集計式検証つき KPI ノード登録（metric_type は CMP-03 check_metric_type を必ず通す）／tree(conn, business_profile_id) -> list[KpiNode] — 親子解決済み KPI ツリー／fetch(conn, task_id, route: Route, property_id, period, out_dir, clock) -> FetchResult — GA4 Data API 第一経路取得（ADR-006）・阻害時ブラウザフォールバック・取得物即 SHA-256 固定＋証跡／parse(raw: Path, schema: SourceSchema) -> ParseResult(rows, quarantined) — schema/type 検証・壊れ行の隔離ファイル分離／ingest(conn, rows, raw, expected_hash, kpi_node_id, task_id, evidence_id, clock) -> int — hash 再計算照合つき単一 transaction 投入
- **要求 interface**: CMP-03 check_metric_type()（有料指標の登録拒否 — DB CHECK と二重）／CMP-07 resolve()／get_credential()（GA4 経路解決・API credential）／CMP-08 launch()／screenshot()（ブラウザフォールバックとスクショ証跡）／CMP-04 evidence.record()（実外部取得のoperation_log・screenshot・取得hash証跡）／external_operations(effect='read', policy_category='external_read', rate_scope=NULL)（実取得1要求=1行=operation_log 1行、payloadはrate_scope:null。mock/dry-runは両方0）／Clock 注入（imported_at）
- **責務境界**: やる: KPI ツリー管理、GA4 データの read-only 取得・hash 固定・パース・隔離つき投入。やらない: 有料指標の受理（CMP-03 で拒否）、書込み系 GA4 操作（組み立て時点で拒否 — read-only 保証）、壊れ行の黙殺（隔離ファイル＋件数証跡化 — AC-62）、戦略判断（KPI は観測のみで戦略正本ではない — SR-12）。 actual実外部I/Oの各operation_logはevidence.external_operation_row_idでsentに到達したexternal_operationsのlocal rowへexactly-oneに束縛し、execution_mode='actual'・effect・policy_category・rate_scope（writeはcanonical lowercase、readはSQL NULLかつpayload JSON null）・service・operation・correlation_key・request_hash・request_sequence・resultを同値にし、INSERT triggerでstatusをconfirmed/rejected/unknownへfinal化する。provider external_operation_idは任意。
- **依存方向**: 計測層（measure）。kernel（WF-MEAS-1）から呼ばれ、gates・registry・connectors・evidence・db に依存。業務状態遷移は kernel 経由。
- **データフロー**: 経路解決→actual取得要求ごとにexternal_read/rate_scope=NULLとrequest_sequence/correlation式を固定→prepared/sent→payload rate_scope:nullのoperation_log INSERT trigger final→SHA-256/スクショ→parse/隔離→hash再照合→正常行投入。mock/dry-runは外部両テーブル0。
- **状態所有者**: kpi_nodes・計測値テーブル（投入行）。取得・隔離ファイルはローカル成果物 ／ **transaction 所有者**: ingest の単一 transaction（FK 不能は投入前拒否・途中失敗は全 rollback）。取得・証跡化は各所有者の単位
- **エラー分類**: PaidMetricRejected: 有料指標型ノード登録 → GateRejected（CMP-03 経由・DB CHECK と二重）／KpiNodeInvalid: 階層・媒体タグ・集計式の不正 → GateRejected・登録しない／ImportSourceInvalid: raw hash 不一致（expected_hash と再計算の相違）→ GateRejected・投入拒否／SchemaVerificationFailed: パース schema/type 違反 → 該当行を隔離（全体は継続、件数証跡化）／StaleSourceRejected: 期限切れ・鮮度不足ソースの投入要求 → GateRejected／RetryableError: GA4 API 一時失敗 → ブラウザフォールバックまたは再試行／FatalError: 全経路取得不能 → escalated
- **degradation／復旧**: API 阻害時はブラウザエクスポートへ縮退（レジストリ優先順どおり・それ以上の暗黙代替なし）。投入は hash 照合＋単一 transaction で再実行安全（部分投入が残らない）。隔離行は人間レビュー後に再投入可能。
- **セキュリティ境界**: GA4 へは read-only のみ（書込み operation は組み立て時点で拒否 — 実 GA4 書込み禁止・環境契約 §6）。credential は CMP-07 経由。計測データは business_profile スコープの kpi_node に紐づけブランド隔離。
- **人間判断点**: 隔離行の処遇判断（再投入・破棄）。取得・投入は全自動
- **trace**: FN = FN-601 FN-602 FN-603 FN-604 FN-605 FN-606 ／ DU = DU-21 DU-22 DU-23 ／ 独立設計書 = error-taxonomy_v0.1.md

## SCM-01 strategy-store（戦略正本の append-only 永続化 — CMP-05 拡張）

- **提供 interface**: strategic_briefs／tactical_learning_packets テーブル（migration 0001 内包の正準 DDL — s0-contract §2）／保護トリガ — 両テーブルの UPDATE/DELETE 拒否（append-only の DB 層強制。総数の正準は s0-contract §2）／loop_runs.strategic_brief_id/strategic_brief_digest 列＋lower CHECK（lower run の brief 保持を DDL で強制）／verify() の TLP 孤児検査 — packet を持たない終端 lower run = 0 件（違反は FatalError → escalate）
- **要求 interface**: CMP-05 migrate.apply_all()／verify()（DDL 適用・整合検査の実行装置）／s0-contract §2 正準 DDL（テーブル・トリガ定義の正本）
- **責務境界**: やる: 戦略正本 2 テーブルのスキーマ・保護トリガ・整合検査の提供（ストア副層）。やらない: brief/TLP の内容生成（SCM-02/04）、検証ロジック（SCM-03）、上流モデル 12 schema の格納（S1 の SCM-05〜07）。上流正本の変更 = supersedes_id 付き新版 INSERT のみという不変条件を DB 層で担保。
- **依存方向**: 基盤層（db）内の拡張。CMP-05 の migration・verify 範囲に内包され、上位層（CMP-01/02 の戦略 API）から書込み・読取りされる。
- **データフロー**: migration 0001 適用 → 2 テーブル＋保護トリガ＋loop_runs 列/CHECK 成立 → CMP-02 の issue/supersede/generate API のみが行を INSERT → verify() が孤児・整合を常時検査。
- **状態所有者**: strategic_briefs／tactical_learning_packets テーブル（スキーマと保護。行の書込み主体は CMP-02 の閉域 API） ／ **transaction 所有者**: なし（migration transaction は CMP-05、業務 INSERT の transaction は CMP-02 が所有）
- **エラー分類**: IntegrityError: 保護トリガ発火（UPDATE/DELETE 試行）・FK/CHECK 違反 → FatalError 正規化・変更されない／MigrationVerifyFailed: TLP 孤児検査違反（packet なし終端 lower run）→ FatalError・escalate／MigrationChecksumMismatch: 戦略 DDL を含む migration の改変検知 → FatalError・適用停止
- **degradation／復旧**: append-only＋トリガ保護で破壊的変更は構造的に不可能。誤登録は supersedes 付き新版でのみ是正（履歴保持）。verify() の孤児検出は escalate し、原因遷移の修復（TLP 補完）は人間判断下で実施。
- **セキュリティ境界**: 戦略正本の改竄防止（トリガによる append-only 強制）。brief/TLP は business_profile スコープでブランド隔離。credential を含む値の混入は CMP-04 検査経路で防止。
- **人間判断点**: なし（全自動。schema 変更は migration 昇格手順 — 人間承認経路）
- **trace**: FN = FN-701 FN-702 ／ DU = DU-10 DU-11 ／ 独立設計書 = db-design_v0.1.md、error-taxonomy_v0.1.md

## SCM-02 brief-issuer（brief 版発行・digest 計算 — CMP-02 拡張）

- **提供 interface**: issue_strategic_brief(conn, brief: StrategicBriefDraft, clock) -> int — schema 適合検証 → 正準化 JSON（キー昇順・区切り (",",":")・UTF-8・digest/status/created_at 除外）の SHA-256 digest 決定計算 → INSERT／supersede_strategic_brief(conn, old_brief_id, new_draft, clock) -> int — 新版 INSERT（supersedes_id・version+1）＋旧版 status=superseded を単一 transaction／S0 シードコマンド — versioned brief の初期投入（S0 受入基準 5）
- **要求 interface**: SCM-01 strategic_briefs テーブル（保護トリガつき）／brief schema（json/strategy/ 正本）による適合検証／Clock 注入（created_at — digest 計算からは除外）
- **責務境界**: やる: brief の版発行・digest の決定的計算・supersedes 連鎖・シード投入。書込みは issue/supersede の 2 API に閉域（下流実行経路・コネクタ層へ非公開 — SR-09）。やらない: brief 内容の戦略的生成（S1 の SCM-07 — S0 はシード）、検証（SCM-03）、TLP（SCM-04）。
- **依存方向**: ドメイン層（kernel — CMP-02 内）。cli（シードコマンド）から呼ばれ、db（SCM-01 テーブル）に依存。下流実行経路から呼ばれない（書込み閉域）。
- **データフロー**: StrategicBriefDraft → schema 検証 → 正準化 JSON 直列化 → SHA-256 digest（同一入力→同一 digest — STC-I-04）→ INSERT。改版は新版 INSERT＋旧版 superseded の単一 transaction。
- **状態所有者**: strategic_briefs 行の書込み主体（テーブル自体の所有は SCM-01/CMP-05） ／ **transaction 所有者**: issue の単発 INSERT と supersede の複合更新（新版＋旧版 — 単一 transaction）
- **エラー分類**: SchemaVerificationFailed: brief draft の schema 不適合 → GateRejected・発行しない／IntegrityError: 保護トリガ・UNIQUE/FK 違反 → FatalError 正規化／GateRejected: superseded/期限切れ版への supersede 要求等の不正連鎖 → 拒否
- **degradation／復旧**: digest は内容から決定的に再計算可能（クラッシュ後の照合・再発行が常に安全）。supersede は単一 transaction で中間状態（新旧とも active 等）が残らない。誤発行は次版 supersede でのみ是正。
- **セキュリティ境界**: 書込み API の閉域化（下流・コネクタへ非公開）で戦略正本の改変経路を構造的に限定。brief は business_profile スコープ。digest により内容すり替えを検出可能。
- **人間判断点**: S0 シード brief の内容決定と投入（PO 起点）。digest 計算・版管理は全自動
- **trace**: FN = FN-102 ／ DU = DU-02 ／ 独立設計書 = error-taxonomy_v0.1.md

## SCM-03 brief-gate（下流 loop_run 開始時の brief 検証 — CMP-01 拡張）

- **提供 interface**: validate_strategic_brief(conn, brief_id, held_digest, clock) -> ValidBrief — status=active・digest 一致・有効期間内の検査（違反は GateRejected — STC-I-03）／loop_runs pending→start ガードへの組込み — 有効 brief なしの下流 loop_run 開始を fail-close で拒否（AC-SR-02）
- **要求 interface**: SCM-01 strategic_briefs テーブル（read）／CMP-01 register_guard()（start ガードとしての配線）／Clock 注入（有効期間判定）
- **責務境界**: やる: 下流 loop_run start 時の brief 有効性検証（active・digest 一致・期間内）の guard 提供。やらない: brief の発行・改版（SCM-02）、状態遷移の実行（CMP-01 本体）、brief 内容の妥当性判断。stateless な検証のみ（ゲートは状態を所有しない）。
- **依存方向**: ドメイン層（kernel の guard — CMP-01 内）。CMP-01 の遷移 transaction 内で評価され、db（strategic_briefs read）にのみ依存。
- **データフロー**: start イベント → run 保持の brief_id/digest → strategic_briefs 現在行と照合（status/digest/期間）→ 成立で遷移続行・不成立で GateRejected（run は pending のまま・DB 不変）。
- **状態所有者**: なし（stateless — 検証のみ。run の brief 保持列は DDL/CMP-01 側） ／ **transaction 所有者**: なし（CMP-01 の遷移 transaction 内で guard として評価される）
- **エラー分類**: GateRejected: brief 不在・status 非 active・digest 不一致・期間外 → start 拒否・状態不変（fail-close）／TransitionRejected: guard 不成立としての遷移拒否記録（state_transitions rejected 行）
- **degradation／復旧**: stateless で復旧不要。brief が superseded された場合、進行中 run は保持 digest で完走し、新規 start のみ新版を要求（版切替の安全境界）。有効 brief 不在時は下流全体が開始不能 — 上流の brief 発行が唯一の復帰経路。
- **セキュリティ境界**: digest 照合により brief 内容のすり替え・改竄を start 時点で検出。ブランド隔離は brief の business_profile スコープ照合で担保。
- **人間判断点**: なし（全自動。拒否解消は brief の再発行 = 人間/上流の判断）
- **trace**: FN = FN-101 ／ DU = DU-01 ／ 独立設計書 = state-machine-design_v0.1.md、error-taxonomy_v0.1.md

## SCM-04 tlp-generator（下流終端到達時の TLP 生成 — CMP-02 拡張）

- **提供 interface**: generate_tactical_learning_packet(conn, loop_run_id, packet: TlpDraft, clock) -> int — lower かつ終端状態の run に対し brief_id/digest を写して INSERT（観測/解釈/因果/判定/推奨の分離充填 — STC-I-05）／get_tactical_learning_packet(conn, loop_run_id) -> TlpRecord | None — 上流（WF-STRAT-REVISE）が読む唯一の還流読取り口／packet_kind 分岐 — completed は learning、failed/escalated/cancelled は failure（kind 別必須フィールド検証）
- **要求 interface**: SCM-01 tactical_learning_packets テーブル（整合トリガが最終防衛）／CMP-01 transition()（下位 run の終端遷移と同一 transaction で呼ばれる — 原子性）／CMP-04 evidence（観測フィールドは計測 evidence 参照）／TLP schema（json/strategy/ 正本）
- **責務境界**: やる: 下位 run 終端時の TLP 組立・検証・INSERT（終端遷移との原子性保証）、上流への還流読取り口の提供。観測（計測 evidence 参照）と解釈・判定を分離フィールドで充填。やらない: TLP の集約・revision 提案（S1 の SCM-08）、上流正本テーブルへの書込み（TLP INSERT のみが下流→上流の唯一の書込み — 不変条件）。
- **依存方向**: ドメイン層（kernel — CMP-02 内）。CMP-01 の終端遷移から同一 transaction で呼ばれ、db・evidence（read）に依存。上流正本テーブルへは書かない。
- **データフロー**: 下位 run 終端遷移 → run が lower・終端であることを検査 → run 保持の brief_id/digest を写す → packet_kind 別必須フィールド検証 → 終端遷移と同一 transaction で INSERT → 上流は get API で読取り。
- **状態所有者**: tactical_learning_packets 行の書込み主体（テーブル所有は SCM-01/CMP-05） ／ **transaction 所有者**: なし（下位 run の終端遷移 transaction — CMP-01 所有 — に参加。単独 transaction を張らない）
- **エラー分類**: GateRejected: lower 以外・非終端 run への生成要求、brief_id/digest 欠落 → INSERT しない／SchemaVerificationFailed: packet_kind 別必須フィールド欠落・観測/解釈の混在 → GateRejected／IntegrityError: DDL 整合トリガ違反（run/brief/digest 不整合 — STC-I-06 の最終防衛）→ transaction ごと rollback（終端遷移も成立しない）
- **degradation／復旧**: 終端遷移との原子性により「終端なのに packet なし」の中間状態はクラッシュでも残らない（両方成立か両方不成立）。万一の孤児は verify() の孤児検査（SCM-01）が検出し escalate。再生成は終端遷移の再実行経路でのみ行う。
- **セキュリティ境界**: 下流→上流の書込みを TLP INSERT のみに限定（上流正本への書込み API を下流・コネクタに公開しない — SR-09 の実装点）。TLP は business_profile スコープで隔離。
- **人間判断点**: なし（全自動。TLP を受けた戦略改訂の判断は S1 SCM-08＋人間）
- **trace**: FN = FN-102 ／ DU = DU-02 ／ 独立設計書 = error-taxonomy_v0.1.md

## SCM-05 observation-store（market_observation 取込・鮮度管理 — S1 新規）

- **提供 interface**: ingest_observation(conn, observation, clock) -> int — market_observation schema 適合検証つき取込（出所・観測日時・expires_at 必須）／list_fresh(conn, business_profile_id, as_of) -> list[Observation] — expires_at 内の有効観測のみ返却（期限切れは分析入力から除外）
- **要求 interface**: market_observation schema（json/strategy/ 12 schema の一部 — S0 で確定済み）／CMP-05 db.connect()（観測テーブル — S1 migration で追加）／CMP-07 resolve()（取得経路 — リサーチ系コネクタ利用時）／Clock 注入（鮮度判定）
- **責務境界**: やる: 上流リサーチ工程の観測データ取込・schema 検証・鮮度（expires_at）管理・期限切れ除外。やらない: 観測の解釈・モデル化（SCM-06）、観測の自動収集実行（コネクタ＋WF 側）、鮮度切れデータの黙示利用（fail-close で除外）。
- **依存方向**: 上流戦略層のストア副層（基盤寄り）。上流 WF（SCM-06 以降）から読み書きされ、db・schema 正本に依存。下流戦術ループからは参照されない。
- **データフロー**: リサーチ取得物 → schema 検証（出所・日時・expires_at 必須）→ INSERT → 分析要求時に as_of で鮮度フィルタ → 有効観測のみ SCM-06 へ供給。
- **状態所有者**: market_observation テーブル（観測正本。append-only 前提 — 上流正本の変更規約を継承） ／ **transaction 所有者**: 取込の単発 INSERT（自トランザクション）
- **エラー分類**: SchemaVerificationFailed: observation schema 不適合・出所欠落 → GateRejected・取込まない／StaleSourceRejected: 期限切れ観測の分析利用要求 → GateRejected（鮮度 fail-close）／ImportSourceInvalid: 出所検証不能・hash 不整合の取得物 → GateRejected
- **degradation／復旧**: 観測が全て期限切れの場合は分析を開始せず「観測不足」を明示（古いデータでの黙示分析をしない）。取込は冪等（同一出所・同一内容の再取込は重複拒否）。復旧はリサーチ再実行のみ。
- **セキュリティ境界**: 観測データは business_profile スコープで隔離。取得系コネクタの credential は CMP-07 経由。外部書込みなし（read/取込のみ）。
- **人間判断点**: 観測ソースの選定・信頼度の初期設定（取込・鮮度管理は自動）
- **trace**: FN = — ／ DU = — ／ 独立設計書 = error-taxonomy_v0.1.md

## SCM-06 market-analyzer（市場モデル生成・版管理 — S1 新規）

- **提供 interface**: build_market_model(conn, observations, clock) -> int — market_model の生成・schema 検証・版 INSERT（根拠観測の参照必須）／build_segment_context(conn, market_model_id, clock) -> int — segment_context 生成・版管理／build_problem_model(conn, segment_context_id, clock) -> int — problem_model 生成・版管理（各モデルは supersedes 連鎖）
- **要求 interface**: SCM-05 list_fresh()（有効観測のみを入力とする）／market_model／segment_context／problem_model schema（json/strategy/ 正本）／CMP-05 db.connect()（上流モデルテーブル — S1 migration）／Clock/Rng 注入
- **責務境界**: やる: 観測→市場モデル→セグメント文脈→課題モデルの生成と append-only 版管理（各版は根拠観測を参照保持）。やらない: 鮮度管理（SCM-05）、価値仮説以降の戦略構成（SCM-07）、根拠なしモデルの生成（出所なし値は拒否 — UnsourcedValueRejected 系統）。
- **依存方向**: 上流戦略層のドメイン。上流 WF から呼ばれ、SCM-05（観測）・db・schema 正本に依存。下流には依存しない。
- **データフロー**: 有効観測群 → 分析・モデル組立 → schema 検証＋根拠参照検証 → 新版 INSERT（supersedes 連鎖）→ SCM-07 の入力へ。
- **状態所有者**: market_model／segment_context／problem_model テーブル（上流意味モデル正本の書込み主体） ／ **transaction 所有者**: 各モデル版の INSERT（supersede を伴う場合は新旧を単一 transaction — SCM-02 と同型）
- **エラー分類**: UnsourcedValueRejected: 根拠観測参照のないモデル値 → GateRejected・生成しない／SchemaVerificationFailed: モデル schema 不適合 → GateRejected／StaleSourceRejected: 期限切れ観測を根拠とするモデル生成要求 → GateRejected（SCM-05 と二重）／IntegrityError: 保護トリガ・supersedes 連鎖違反 → FatalError 正規化
- **degradation／復旧**: 観測不足時はモデル生成を保留し不足を明示（推測で埋めない）。モデルは決定的に再生成可能な入力参照を保持し、誤りは新版 supersede でのみ是正（履歴保持）。
- **セキュリティ境界**: モデルは business_profile スコープで隔離（他ブランドの観測・モデルを参照しない）。外部書込みなし。credential 非関与。
- **人間判断点**: モデルの妥当性レビュー（生成は自動、正本昇格は人間確認を推奨経路とする）
- **trace**: FN = — ／ DU = — ／ 独立設計書 = brand-isolation-design_v0.1.md、error-taxonomy_v0.1.md

## SCM-07 strategy-composer（価値仮説〜戦略選択の生成 — S1 新規）

- **提供 interface**: compose_value_hypothesis(conn, problem_model_id, clock) -> int — value_hypothesis 生成（反証条件必須）／compose_strategic_choice(conn, candidates, clock) -> int — strategic_choice 確定（棄却案も rejected として全件保持）／issue_brief_from_choice(conn, strategic_choice_id, clock) -> int — 確定戦略からの brief draft 組立（発行は SCM-02 の issue API へ委譲）
- **要求 interface**: SCM-06 の各モデル版（market_model/segment_context/problem_model）／value_hypothesis〜strategic_choice schema（json/strategy/ 正本 — 反証条件フィールド必須）／SCM-02 issue_strategic_brief()（brief 発行の唯一の書込み口）／SCM-09 媒体役割語彙台帳（brief 内の媒体役割語彙の正当性）
- **責務境界**: やる: 価値仮説→戦略候補→戦略選択の生成、棄却案の保持（なぜ選ばなかったかの正本化）、反証条件の必須充填、brief draft の組立。やらない: brief の直接 INSERT（SCM-02 委譲 — 書込み閉域維持）、下流実行、KPI を戦略正本と混同すること（SR-12）。
- **依存方向**: 上流戦略層のドメイン。上流 WF から呼ばれ、SCM-06/09（read）・SCM-02（発行委譲）に依存。下流・コネクタへ依存しない。
- **データフロー**: problem_model → 価値仮説（反証条件つき）→ 戦略候補群 → 選択＋棄却理由の全件保持 → strategic_choice 版 INSERT → brief draft 組立 → SCM-02 issue へ委譲。
- **状態所有者**: value_hypothesis／strategic_choice テーブル（棄却案含む全候補の版管理） ／ **transaction 所有者**: 候補・選択の版 INSERT（choice 確定と棄却案記録は単一 transaction）
- **エラー分類**: SchemaVerificationFailed: 反証条件欠落・schema 不適合 → GateRejected・確定しない／UnsourcedValueRejected: モデル根拠のない仮説値 → GateRejected／GateRejected: 棄却理由なしの候補破棄・媒体役割語彙台帳外の語彙使用 → 拒否
- **degradation／復旧**: 上流モデル不在・旧版のみの場合は組成を保留（欠けたまま brief を出さない — fail-close）。選択の誤りは revision（SCM-08）→ 新版 choice → 新 brief の正規経路でのみ是正。棄却案保持により再検討時の再現性を保証。
- **セキュリティ境界**: business_profile スコープでの戦略隔離（ブランド間で仮説・選択を混用しない）。外部書込み・credential 非関与。brief への反映は SCM-02 の閉域 API 経由のみ。
- **人間判断点**: strategic_choice の最終確定（AI 起草・人間承認を正規経路とする — 戦略の最終責任は人間）
- **trace**: FN = — ／ DU = — ／ 独立設計書 = error-taxonomy_v0.1.md

## SCM-08 revision-engine（TLP 集約→戦略改訂評価 — S1 新規）

- **提供 interface**: aggregate_tlp(conn, strategic_brief_id, period) -> TlpAggregate — 対象 brief 配下の TLP 集約（learning/failure 別）／propose_revision(conn, aggregate, clock) -> int — strategy_revision 提案の生成（支持根拠の列挙必須）／evaluate_revision(conn, revision_id, clock) -> RevisionDecision — 複数根拠・反証・時間差の評価。支持根拠 2 件以上ない accept は拒否（単一 KPI 変動の自動反映禁止）
- **要求 interface**: SCM-04 get_tactical_learning_packet()（還流読取りの唯一の口）／SCM-07 の strategic_choice（反証条件の照合先）／strategy_revision schema（json/strategy/ 正本）／SCM-02 supersede_strategic_brief()（accept 時の brief 改版委譲）
- **責務境界**: やる: TLP の集約・revision 提案・複数根拠/反証/時間差の評価・自動 accept の制限（根拠 2 件未満は不可）。やらない: brief の直接改版（SCM-02 委譲）、TLP の生成（SCM-04）、単一 KPI 変動での自動戦略変更（明示禁止 — 不変条件）。
- **依存方向**: 上流戦略層のドメイン（改善工程）。上流 WF から呼ばれ、SCM-04（read）・SCM-07（read）・SCM-02（改版委譲）に依存。
- **データフロー**: brief 配下 TLP 群 → 集約（観測/解釈/判定の分離を保ったまま）→ revision 提案生成 → 反証条件・複数根拠・時間差評価 → accept は根拠 2 件以上のみ → SCM-02 supersede へ委譲／reject は理由つき保持。
- **状態所有者**: strategy_revision テーブル（提案・評価・採否の版管理） ／ **transaction 所有者**: revision 提案・評価結果の INSERT（accept 時の brief 改版 transaction は SCM-02 所有）
- **エラー分類**: GateRejected: 支持根拠 2 件未満の accept 要求・単一 KPI 変動由来の自動反映 → 拒否（SR-16）／SchemaVerificationFailed: revision schema 不適合・根拠参照欠落 → GateRejected／StaleSourceRejected: 評価対象期間外・鮮度切れ TLP のみでの提案 → GateRejected
- **degradation／復旧**: TLP 不足時は提案を保留し「観測不足」を明示（推測改訂しない）。評価は入力参照から決定的に再実行可能。誤 accept の是正は次の revision サイクルの正規経路のみ（履歴は消えない）。
- **セキュリティ境界**: brief 改版は SCM-02 閉域 API 経由のみ（本 SCM も直接 UPDATE 不可 — トリガと二重）。business_profile スコープ隔離。外部書込み・credential 非関与。
- **人間判断点**: revision の最終採否（自動 accept は根拠 2 件以上の制限内でも重要変更は人間承認へエスカレート）
- **trace**: FN = — ／ DU = — ／ 独立設計書 = error-taxonomy_v0.1.md

## SCM-09 media-role-ledger（媒体役割語彙台帳 — S1 新規）

- **提供 interface**: get_roles(conn, business_profile_id) -> list[MediaRole] — 有効な媒体役割語彙の取得（brief・コンテンツ企画の語彙検証先）／add_role(conn, role, reason, agent_id, clock) -> int — config 経由の追加（append-only・reason 必須）／validate_role(conn, media, role) -> None — 台帳外語彙の使用を GateRejected（SCM-07/10 から呼ばれる）
- **要求 interface**: CMP-06 config.set()/get()（台帳の永続化は config 経由 — append-only 履歴を継承）／媒体役割台帳 JSON 正本（json/strategy/ — S0 で確定済み）
- **責務境界**: やる: 媒体役割語彙（認知・回遊・指名・変換等）の台帳管理・語彙検証・config 経由の履歴つき変更。やらない: 語彙の意味づけの自動変更（追加・変更は reason 必須の明示操作のみ）、媒体運用そのもの（下流ループ）、glossary の代替（ドメイン語彙正本は glossary — 本台帳は媒体役割に限定）。
- **依存方向**: 上流戦略層の台帳（config 寄り基盤）。SCM-07（brief 組成）・SCM-10（企画検証）から読まれ、CMP-06 にのみ依存。
- **データフロー**: 台帳 JSON 正本＋config 追加分 → 有効語彙集合 → brief/企画の役割語彙を validate → 台帳外は GateRejected。変更は config append-only 行として履歴保持。
- **状態所有者**: 媒体役割台帳（config 行として — 物理所有は CMP-06 の config テーブル） ／ **transaction 所有者**: なし（config INSERT の transaction は CMP-06 所有）
- **エラー分類**: GateRejected: 台帳外語彙の brief/企画への使用 → 拒否（語彙の勝手な発明を封じる）／ConfigReasonMissing: reason なしの語彙追加 → GateRejected（CMP-06 から伝播）／SchemaVerificationFailed: 台帳 JSON 正本の schema 不適合 → FatalError
- **degradation／復旧**: 台帳は JSON 正本＋config 履歴から常に再構成可能。語彙の誤追加は supersedes での是正のみ（履歴保持）。台帳読込不能時は語彙検証を fail-close（通さない）。
- **セキュリティ境界**: business_profile スコープの役割定義を分離（ブランド毎に媒体役割が異なりうる）。credential・外部書込み非関与。
- **人間判断点**: 語彙の追加・意味変更の判断（reason 記入必須 — 台帳は人間の統制下）
- **trace**: FN = — ／ DU = — ／ 独立設計書 = brand-isolation-design_v0.1.md、error-taxonomy_v0.1.md

## SCM-10 recognition-content-gate（コンテンツ企画 5 宣言の実行時強制 — S1 新規）

- **提供 interface**: check_content_plan(conn, plan) -> ContentPlanPass — content-plan-contract の 5 宣言（対象読者・課題・提供価値・媒体役割・計測点）の全充足検証。欠落は GateRejected／require_plan_pass(conn, plan_id) -> ContentPlanPass — 制作 WF 開始前の必須ゲート（未通過企画は generate に到達しない）
- **要求 interface**: content-plan-contract schema（json/strategy/ 正本 — S0 で確定済み）／SCM-09 validate_role()（媒体役割宣言の語彙検証）／SCM-03 と同系の brief 参照（企画が有効 brief に紐づくこと）／CMP-05 db.connect()（企画行 read）
- **責務境界**: やる: コンテンツ企画の 5 宣言充足の実行時強制（ゲート層 — 制作開始前の fail-close）、brief 紐づき検証、媒体役割語彙検証。やらない: 企画の生成（上流/制作側）、宣言内容の質的判断（充足の形式検証に限定 — 質はペア審査）、状態所有（stateless ゲート）。
- **依存方向**: ゲート層（gates — CMP-03 と同格の追加ゲート）。kernel の制作 WF から呼ばれ、db・schema 正本・SCM-09 に依存。コネクタへ依存しない。
- **データフロー**: コンテンツ企画 → 5 宣言の存在・schema 検証 → 媒体役割語彙の台帳照合 → 有効 brief 紐づき確認 → 全充足で ContentPlanPass 返却（CMP-03 PairPass と同じ構築独占方式）→ 不成立は GateRejected で制作 WF が開始されない。
- **状態所有者**: なし（stateless — ゲートは業務状態を所有しない） ／ **transaction 所有者**: なし（検証のみ。呼出し側 guard として遷移 transaction に参加）
- **エラー分類**: GateRejected: 5 宣言のいずれか欠落・brief 紐づきなし・台帳外役割語彙 → 制作開始拒否（fail-close）／SchemaVerificationFailed: content-plan-contract schema 不適合 → GateRejected／FatalError: ContentPlanPass 偽造検知（sentinel token 不一致 — CMP-03 と同方式）
- **degradation／復旧**: stateless で復旧不要。schema・台帳の読込不能は fail-close（企画を通さない）。拒否された企画は宣言を補完して再検証（履歴は企画側の版管理が保持）。
- **セキュリティ境界**: ContentPlanPass の構築独占でゲート未通過の制作経路を型・実行時の両面で封鎖（CMP-03 PairPass と同型）。企画・brief の business_profile スコープ整合を検証しブランド混線を遮断。
- **人間判断点**: なし（形式検証は全自動。宣言内容の質はペア審査＝人間/verifier 側）
- **trace**: FN = — ／ DU = — ／ 独立設計書 = brand-isolation-design_v0.1.md、error-taxonomy_v0.1.md
