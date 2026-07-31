# 要件整合ゲート台帳 v0.1

> status: **active**（2026-07-31 導入）。実体は [scripts/validate_requirements.py](../../scripts/validate_requirements.py)、
> CI（Docs CI / requirements-gates ジョブ）で push/PR ごとに fail-close 実行。1 件でも FAIL = CI 赤。
> ゲートの追加・変更はスクリプトと本台帳を同時に更新すること。

| ゲート | 検証内容 | 違反の意味 |
|---|---|---|
| G-JSON | json/ 配下の全ファイルが構文的に妥当 | 壊れた正本 |
| G-CNT-BR/REQ/FR/NFR/AC/ACDEF/FN/BRM/MR/WF | JSON 件数 = MD の分母（BR38・REQ52・FR36・NFR10・AC19+deferred17・FN61・BR-M70・MR54・WF49） | MD↔JSON の同期漏れ、分母のサイレント変更 |
| G-REQ-CONTRACT | BR 構造化契約（br-contracts.json）が schema 適合（12 観点必須・additionalProperties: false）で全 38 BR を被覆し、12 独立要求群がすべて担当 BR を持ち、REQ 参照が実在し、生成ビュー（br-contracts_v0.1.md）が正本と同期 | 1 行要求の温存・要求群の宙吊り・手編集ビューの乖離（全層再降下 §2） |
| G-UNIQ-* | BR/REQ/FR・NFR/AC/FN の ID 重複ゼロ | ID 衝突 |
| G-TRC-BR | s0/trace.json が全 38 BR をカバー | トレース断絶（BR が要件へ降りていない） |
| G-TRC-AC | AC の target が実在する FR | 宙に浮いた受入条件 |
| G-GWT | AC 全件に非空の Given/When/Then | 機械検証できない AC（AP-4 相当） |
| G-S0-CNT / G-S0-SET | S0.1〜S0.3 の fn_ids が 25 件・重複なし・function-list の slice=S0 集合と完全一致 | スコープのサイレント増減 |
| G-DDL-SYNC | json/s0/ddl.sql が s0-contract の DDL ブロックと一致 | 正準 DDL の二重化・乖離 |
| G-DDL-APPLY | DDL が空 SQLite へ適用でき FK/integrity 検査が通り 25 テーブル＋append-only／整合トリガ 14 | 実行不能なスキーマ |
| G-EVK | evidence kind 10 種が JSON 契約と DDL の CHECK で同一集合 | 証跡語彙の乖離 |
| G-TRN-ENT / G-TRN-ST | 遷移表の entity が loop_runs/tasks、from/to 状態が DDL enum 内（複合表記の検査除外なし） | 実装不能な状態機械定義 |
| G-TRN-UNIQ/REACH/TERM/GUARD | (entity, from, event) の一意性・enum 全非初期状態の到達可能性・終端状態からの遷移不在・全遷移の非空ガード | 非決定的な状態機械（レビュー P0-1） |
| G-CONFIRM | status: confirmed を名乗る文書が approvals.md に承認行を持つ | freeze 偽装（HELIX gate-confirm 相当） |
| G-CONFIRM-DIGEST | confirmed 文書の現内容 sha256（先頭 12 桁）が承認行の digest 列に存在する | 内容に束縛されない空承認（レビュー P0-4） |
| G-SRC-FRESH | br-media 各媒体の structure_checked が 90 日以内 | 出典腐敗（媒体規約・上限は変わる。HELIX source-ledger-freshness 相当） |
| G-POC-EXIT | PoC が出口 2 軸 schema（decision_outcome × promotion_strategy）に適合、confirmed には strategy 必須 | PoC の独り歩き（HELIX poc 規律相当） |
| G-SUBSTANCE | 全エンティティに 8 文字以上の本文実体 | 空・スタブ本文の完了僭称（HELIX AP-13 相当） |
| G-PAIR-EXIST/UNIQ/AC/TC/REJ/UPD/DOC | 対の検証設計（verification.json）が存在し、全 AC ↔ TC の双方向カバー・拒否系 ≥7・全 TC の S0.x 割当・ペア台帳の文書実在 | 片肺（検証対のない設計 = HELIX pair gate 違反） |
| G-PAIR-HDR | 設計 5 文書のヘッダに pair 行（③参照）、検証設計側にも対象列挙（①↔③ 対称） | 片方向ペア（HELIX pair_artifact/trace-bidir 相当） |
| G-CMP-CNT/UNIQ/FN | 基本設計②のコンポーネント台帳（components.json）が CMP 13・ID 重複ゼロ・S0 25 FN を重複なく完全被覆 | 設計漏れ・二重責務（FN の宙吊り） |
| G-ITC-CNT/UNIQ/CMP/AC/REJ/UPD | 総合テスト設計④（itest.json）が ITC 16・ID 重複ゼロ・全 CMP と全 AC を双方向カバー・拒否系 ≥7・全件 S0.x 割当 | 片肺（総合テスト対のない設計 = HELIX pair gate 違反） |
| G-PAIR2-EXIST/HDR | ②↔④ の JSON 正本が存在し、両文書ヘッダが相互 pair 参照、ペア台帳の文書実在 | 片方向ペア（②↔④ 非対称） |
| G-DU-CNT/UNIQ/CMP/FN | 詳細設計⑤の DU 台帳（detailed.json）が DU 23・重複ゼロ・全 CMP を被覆・S0 25 FN を重複なく完全被覆 | モジュール分解の漏れ・二重責務 |
| G-UTC-TC/DU/CNT/FILE | 単体テスト設計⑥（utest.json）が TC 59 全件を重複なく実在 DU へ割当・全 DU にテストあり・UTC 69（割当 59＋UT 10）・test_file が DU と 1 対 1 衝突なし | テストの届かないモジュール（TDD の空白）・テストファイル混線 |
| G-UTC-FILE-EXIST | ⑥と戦略層 STC-I（S0.1）が宣言する全 test_file がディスク上に実在（未実装分は**関数単位** skip（理由付き）として存在し、pytest が個別に skipped と報告 — module-level skip は全層再降下 §8 で廃止） | 宣言だけのテストファイル（実行されない検証の PASS 僭称） |
| G-PAIR3-EXIST/HDR | ⑤↔⑥ の JSON 正本が存在し、両文書ヘッダが相互 pair 参照、ペア台帳の文書実在 | 片方向ペア（⑤↔⑥ 非対称） |
| G-BASE-EXIST/HASH/STATUS/RATCHET | baseline.json に対し confirmed 文書のハッシュ一致・降格なし・分母縮小/ゲート削減なし・**pytest skip 上限（tests/skip-budget.json の max_skipped）の引き上げなし（比較元は **親コミット（HEAD^）** の baseline — CI では検査対象コミット自身が HEAD になるため。引き上げには approvals.md の**構造化 PO 承認行**（`日付／skip-budget／N→M／approved／PO／理由` の 6 列テーブル行。散文記述・判定 rejected では成立しない）が必要で、作業ツリー同時改変・引き上げのコミットのいずれでも回避できない）**。意図的変更は `--update-baseline` を同一コミットで実行（承認 receipt = digest 行がないと baseline 更新を拒否） | **デグレ**: confirmed のサイレント改変・後退・こっそりスコープ縮小（HELIX 日付 ratchet 相当） |
| G-BASE-ART | 実装入力（JSON 正本・DDL・validator・CI・CLAUDE.md/AGENTS.md・hook）のハッシュが baseline と一致・未登録なし | 実装入力のサイレント改変（レビュー P0-4: MD だけの束縛では不足） |
| G-COUNT-SYNC | README・CLAUDE.md・AGENTS.md・設計/ガバナンス文書中の手書きゲート件数表記が実数と一致 | 散在する件数のドリフト（意味整合の欠如） |
| G-STRAT-BRIEF | strategic_brief 契約が完全（必須フィールド・digest）で、DDL が下位 loop_run に brief id/digest の保持を強制し、開始ガードが有効 brief を要求する | brief なしの下流開始（上流→下流契約の欠落） |
| G-STRAT-TRACE | 下流 run→brief→strategic_choice→value_hypothesis→segment_context→evidence の trace が schema 必須フィールドで双方向追跡可能。trace 欠落 fixture を拒否 | 宙に浮いた戦術（戦略仮説へ還元できない実行） |
| G-SEGMENT-CONTEXT | segment_context に時間・空間・制約・進行状態・代替行動が必須（非空）。人口統計のみの fixture を拒否 | ペルソナ型セグメントの正本化（SR-04 違反） |
| G-OBS-INTERPRETATION | market_observation は解釈フィールドを持てず（additionalProperties: false）、解釈は TLP の分離フィールドのみ。learning/failure の packet_kind 二分で failure への因果解釈捏造も拒否 | 観測事実と AI 解釈の混濁（反証不能化） |
| G-LEARNING-TRACE | 全 TLP が loop run・brief digest・evidence へ接続し、UNIQUE(loop_run_id)＋整合トリガ（lower・終端・digest 三者一致）を DDL が強制。最低 1 件は「終端遷移と TLP INSERT の同一 transaction」kernel 契約＋孤児検査（packet なし終端 lower run = 0 件）の宣言を s0-contract に要求。未接続 fixture を拒否 | 接続のない学習（存在しない扱いにすべき還流） |
| G-NO-DIRECT-STRATEGY-MUTATION | 上流正本の保護トリガ（strategic_briefs/TLP の no_update/no_delete）が DDL に実在し、s0-contract が下流・コネクタ・計測からの直接更新禁止を宣言 | 下流からの戦略正本の直接書換え |
| G-REVISION-EVIDENCE | strategy_revision に根拠・反証・信頼度・対象版が必須。単一計測値・重複根拠の accepted を拒否し、accepted（maintain 以外）には new_version_id（原子的新版生成）を要求 | KPI 値の直接戦略変換（意味モデルを迂回した自動変更） |
| G-STRATEGY-VERSION | 全上流モデル schema が version 必須＋supersedes_id を定義し、DDL が上書き・削除を拒否（append-only 版管理） | 上流正本の上書き（履歴・棄却理由の喪失） |
| G-MEDIA-ROLE | 媒体役割台帳（media-roles.json）が 12 語彙以上で、brief が戦略役割と認識変化を必須で持つ。台帳外役割（媒体名等）の fixture を拒否 | 媒体名の役割僭称（戦術の戦略化） |
| G-CONTENT-VALUE-DEFINITION | コンテンツ企画契約が 5 宣言（定義する問題・変化させる認識・比較軸・価値・対象戦略仮説）を必須とし、宣言欠落 fixture を拒否 | 認識変化を宣言しない投稿物量産 |
| G-STRAT-PAIR | 戦略層 4 文書（要件・契約・設計・テスト設計）が相互 pair 参照を持ち、SR 16／SCM 10／AC-SR 6 が STC で双方向カバーされ、全戦略ゲートに拒否系 STC（negative test）が存在 | 片肺の戦略層（検証なき意味モデル） |
| G-FRSR-CONTRACT | 全 FR（36）／SR（16）に 18 観点の実行契約が schema 適合で存在し、tables が DDL 実在テーブル（`r:/w:/rw:` 表記か `参照:` 明示）、state_transitions が正準遷移表の状態か `テーブル列: <実在表>.<列>:` 表記であること（表記不正・未知 entity も欠陥として検出 — fail-open なし） | 責務 1 行要件の温存・DDL/遷移正本との乖離（全層再降下 §3） |
| G-NFR-MEASURABLE | 全 NFR（10）に計測契約（測定対象・方法・閾値・環境・違反時動作・証跡）が schema 適合で存在 | 測定方法のない閾値（検証不能な NFR — 全層再降下 §3） |
| G-AC-COVERAGE | AC 検証契約（ac-contracts.json）が schema 適合（GWT＋fixture・観測点・DB 差分・証跡・禁止副作用・エラー型・対象更新）・target 実在・ID 一意で、S0 の全 FR/SR に AC ≥1 | AC なし実装対象・「行が存在する」検証（全層再降下 §4） |
| G-AC-POLARITY | S0 の各 FR/SR が正常／拒否／境界復旧の 3 極性を AC または理由付き N/A（ac_na）で被覆（AC と N/A の重複宣言は矛盾として拒否） | 正常系だけの受入（拒否・境界の空白 — 全層再降下 §4） |
| G-HUMAN-JUDGE | 全 FR/SR 契約に人間判断点の明示（「なし（全自動）」宣言 or 主体特定 — PO/人間/運用者/承認） | 人間判断点の暗黙化（HELIX 人間判断点列必須 相当） |
| G-INVARIANT-TRACE | S0 の各 FR/SR で invariant_ac_map が invariants と同数の行を持ち、各行に**その不変条件固有の**負方向 AC（具体エラー型つき reject または boundary-recovery）が ≥1。**契約内で同一の負方向 AC を 2 つ以上の不変条件へ割り当てることを禁止**（併記による回避も不可） | 破られても検出されない不変条件・1 件の AC による見かけの被覆（全層再降下 §3/§9） |
| G-TRACE-BIDIR | TC 検証契約（tc-contracts.json）が schema 適合（状態・DB 差分・証跡・禁止副作用・外部呼出回数を検証、kill/conflict/resume 種別を含む）で、全 AC と TC が双方向に接続（AC 無 TC・宙吊り参照・非対称参照 = 0） | 検証の届かない AC・「行が存在する」だけの TC（全層再降下 §5） |
| G-CMP-INTERFACE | 全 CMP（13）／SCM（10）に 11 観点の設計契約（cmp-contracts.json — 提供/要求 interface・責務境界・依存方向・データフロー・状態/tx 所有者・エラー分類・degradation・セキュリティ境界・人間判断点）が schema 適合で存在し、参照する独立設計書がディスク上に実在 | interface なきコンポーネント・宙に浮いた独立設計書参照（全層再降下 §6） |
| G-DU-API | 全 DU（23）に実装契約（du-contracts.json — 公開 API 署名 `def name(...) -> 型`・DTO/値オブジェクト・状態遷移・tx 境界・冪等性・競合制御・AC/TC/UT 対応）が schema 適合で存在し、module が⑤台帳と一致 | API なき DU（実装が無契約で始まる — 全層再降下 §7） |
| G-DU-DBC | 全公開 API に precondition／postcondition（DbC）が非空で存在 | 契約なき API（pre/post の暗黙化 — 全層再降下 §7） |
| G-DU-ERROR | 全 API の raises 型がエラー分類正本（error-taxonomy_v0.1.md）に掲載 | 台帳外エラー型の発明・分類の分裂（全層再降下 §7） |
| G-DU-DATA | 全 DU の DB read/write が DDL の実在テーブルのみ | 存在しないテーブルへの設計参照（全層再降下 §7） |
| G-API-UT | **全 23 DU** の各公開 API に UT ≥1（apis[].ut）が割当てられ、api.ut ⊆ trace.ut・宙吊り UT ゼロ・参照テスト関数が def として実在し、test-first スタブは skip 理由に「対象 DU＋**その UT を所有する API 名**（apis[].ut から逆引き）」を宣言している（**実行検証は S0.1 以降で red→green** — 本ゲートは設計フェーズの割当・リンクを保証するもので、テストの実行結果を保証しない） | UT なき API・匿名スタブ（どの API を検証するか不明なテスト）（全層再降下 §8） |
| G-NO-HOLLOW-DESIGN | 全契約正本（BR/FR/SR/AC/NFR/TC/CMP/DU）に TBD・TODO・仮置き等のプレースホルダが存在しない | 空洞設計の温存（全層再降下 §9） |
| G-CHAIN-BIDIR | **BR→REQ→FR/SR→AC→TC→CMP→DU→API→UT の全区間**を突合: BR↔REQ・REQ↔FR/SR は相互参照、FR/SR↔AC と CMP↔DU は厳密等号（DU は cmp＋also_implements で所属宣言）、FR/SR→CMP は実在＋FN 被覆、**全 FR/SR に CMP 接続 ≥1**、S0 の全 AC・全 TC が最低 1 DU に割当、DU.trace.ut = ∪ apis[].ut（末端一致）。**直接 edge** = BR↔REQ／REQ↔FR/SR／FR/SR↔AC／FR/SR→CMP／CMP↔DU／DU↔TC／DU↔API-UT、**導出 edge** = AC→TC（G-TRACE-BIDIR が担保）を経由する TC→CMP（S1 以降を再降下済みとする際は TC→DU 検査の対象スライス拡張が必要） | 鎖の片方向化・区間の抜け（trace があるように見えて逆から辿れない — 全層再降下 完了条件 4） |
| G-DESIGN-SUBSTANCE | 独立設計書 6 本と機能別設計 11 本が実体を持つ（各 ≥50 行・≥3 節、機能別は trace 表つき） | 参照だけ存在する空設計書（存在検査のすり抜け） |
| G-DESCENT-SELFTEST | 再降下ゲート群（polarity／DbC／DATA／BIDIR／CHAIN）へ欠陥を注入した**変異データを実際の検出ロジックへ投入**し、検出されることを毎回証明する mutation 自己検査 | 名目だけの粒度ゲート（検出能力の喪失に気づけない） |
| G-SEMANTIC-REF | 全 FR/SR/AC/TC/CMP/DU の `semantic_refs`（table/column/state/event/evidence_kind/error_type/api）が正本語彙に実在（ddl.sql・transitions.json・evidence-kinds.json・error-taxonomy・du-contracts と突合） | 自由文に埋もれた意味矛盾（存在しない列・状態・証跡種別・エラー型・API の参照） |
| G-COLUMN-REF | `table_refs`／`column_refs` が ddl.sql の実在テーブル・実在列であること | 列名のドリフト（loop_runs.status 等の実在しない列参照） |
| G-STATE-EVIDENCE-CONSISTENCY | 状態遷移に触れる AC/TC の証跡が state_transitions・構造化ログで表現され、`operation_log`（evidence kind）は外部操作・業務操作の証跡に限定される | 証跡種別の混同（内部遷移の拒否を外部操作証跡で表現する） |
| G-CANON-CONFIRMED | 契約 JSON 正本 8 本（br/fr/sr/nfr/ac/tc/cmp/du-contracts）が `status: confirmed`＋`approved_at`／`authority`／`approval_digest` を持ち、digest が内容（approval_digest 列を除く正準化 JSON の sha256[:12]）と一致し、approvals.md に同 digest の承認行が実在 | 内容に束縛されない正本確定・status 僭称（クロージャー §2） |
| G-LEGACY-SUPERSEDED | 旧正本（ac.json／verification.json／utest.json）が `status: superseded`（または historical）で、実装入力から除外されている | 旧 AC19／TC59／UTC69 体系の二重正本化（クロージャー §3） |
| G-S0-TEST-REALITY | `tests/skip-budget.json` の `s0_impl_started` が true のとき、DU-01〜12 の全 API に対応する UT が skip されていない（実 red→green を要求）。着手前は false で猶予され、着手時に true へ切替える | skip を「red」と称する test-first の形骸化（クロージャー §7） |
| G-WIRING | スクリプトの全ゲート ID が本台帳に掲載され、CI がスクリプトを呼ぶ | ルールの配線漏れ・死蔵（HELIX lint-wiring 相当） |

## 運用

- 分母を意図的に変える場合（BR 追加等）は、MD・JSON・本スクリプトの期待値を **同一コミット**で更新する
  （ゲートが赤のままの main を作らない）
- S1 以降で AC・WF・FN が増えたら、対応するゲート期待値の更新もそのスライスの完了条件に含める
- 導入時の実績: 初回実行で遷移表 `to` への注記混入 1 件を検出・是正（ゲートの有効性確認済み）
