# 要件定義ギャップ監査 — HELIX 品質バー突合（2026-07-30）

- status: reported
- 監査対象: README + docs/ 全 9 文書（HEAD 0074937 相当）
- 比較基準: ~/HELIX-HARNESS の要件定義完了バー（gates.md / gate-design.md / L00-L06-design-phase.md / 各 ledger・監査文書）
- 監査方法: HELIX 側基準抽出と本リポジトリ棚卸しを独立エージェント 2 レーンで並列実施し、ID 件数・トレース断絶は grep 全件突合で裏取り
- スコープ分離: 本監査は「要件定義までの不足」のみを判定する。実装可否・S0 着手可否の最終判断は PO に帰属する

## 0. 判定

**「HELIX 基準で要件定義完了」とは判定しない。** ただし致命欠陥の多くは軽量修正で閉じられる。区分: Critical 3 / Important 6 / Minor 4。

HELIX の判定規約（gate-design §3: Critical=0 → CONDITIONAL PASS）に照らすと、現状は **FAIL（Critical 3）**。下記 C-1〜C-3 を閉じれば CONDITIONAL PASS（Important/Minor は carry 可）。

## 1. 分母（自己申告 vs 実測）

| ID 系 | 公称 | 実測 | 判定 |
|---|---|---|---|
| BR | 27 | **30** | 不一致 |
| REQ | 45 | 45 | 一致 |
| FR | — | 33 | — |
| FN | 67 | **61** | 不一致（スライス配分表も公称 67 に合わせてあり二重に不正確） |
| MR | — | 31 | — |
| 媒体 | 19 | 19 | 一致 |

HELIX は「分母の明示と一致」を完了監査の第一条件にする（l12-scrum-requirements-completion-audit 方式）。公称値の不一致は completion claim の信頼を直接毀損する。

## 2. Critical（G3 相当を fail させる欠陥）

### C-1. 受入基準（AC）が S0 の 5 項目しかない — AP-4 相当

HELIX では **AC 不在の FR は G3 即 fail**（各 FR に exactly one の AC）。本リポジトリは FR 33 本に対し、受入基準は requirements_v0.1 §4 の S0 用 5 項目のみ。FR-31〜34（ヒアリング）、FR-41〜47（実行系）等は検証可能条件を一切持たない。
→ 最低限: S0 スコープの FR（FN 配分で S0=25 に対応する FR 群）に AC を 1:1 で付ける。S1+ の FR は「AC はスライス着手時に確定」と明示的に deferred 宣言する（黙って欠落させない）。

### C-2. REQ 層が下流（FR/FN）と ID レベルで断絶

requirement-list の REQ-001〜045 を FR/FN から参照しているのは REQ-045 の 1 箇所のみ（grep 全件突合で確認）。BR→REQ は健全だが、公称の BR→REQ→FR→FN 連鎖は REQ で切れており、BR 経由の間接推移に依存。さらに requirements §5 のトレース表は「A1-A4 → FR-11..15」「evidence 全般」といったカテゴリ粒度で、HELIX の trace-bidir / upstream-coverage（孤児 0）基準を満たさない。
FN 側にも層飛ばしがある: FN-110/208/512/703 は FR を経ず BR を直接参照、FN-109/704/705 は NFR を直接参照、FN-413/509/510 の FR 列は「媒体要件」という文字列で MR-* ID を指さない。
→ REQ↔FR 対応列の追加、または REQ 層を「BR の優先度ビュー」と再定義してトレース義務を BR→FR→FN に一本化するか、どちらかを決めて明文化する。

### C-3. 分母の自己申告が実体と不一致（§1 のとおり）

README・コミットメッセージ・function-list の集計行が実測とずれている。HELIX ではヘッダ宣言件数 vs 実数の照合（count-matches）が機械ゲート対象。
→ 件数修正は機械的作業。あわせて docs-ci に ID 件数照合の簡易チェックを足せば再発を防げる。

## 3. Important（carry 可だが要件フェーズで立項すべき）

1. **リスク登録簿なし**。本構想の中核リスク——ブラウザ自動化の媒体規約違反・アカウント BAN、anti-bot 対策破損、無人自走の暴走——が FR-43/NFR-7 の技術記述に埋没しており、影響度・緩和策・撤退条件を持つリスクとして立項されていない。tech-stack §7 の再検討トリガー 7 条件が唯一の近似。
2. **ADR なし**。charter §8 構成案に governance/（方針・ADR）があるが実体未作成。決定は charter §10 と tech-stack の表に散在し、supersede・撤回手順がない。HELIX では大局判断（言語・runtime 境界・接続原則 MCP→ブラウザ→有償API 等）は ADR 起票対象。tech-stack §1 が HELIX 本体の ADR-010 を参照しているのに自リポジトリに対応 ADR がないのは authority の宙吊り。
3. **法規・コンプラの扱いが景表法ステマ規制のみ**。HubSpot/LINE に入るリード情報の個人情報保護（APPI）、特定電子メール法（オプトイン・配信停止導線）、各媒体利用規約とブラウザ自動化の適合性判断が要件化されていない。無人でメール/LINE 配信まで行う設計なので、これは媒体別 MR の「安全」観点に含めるべき要求。
4. **NFR に測定可能な数値がゼロ**。fail-close/決定性/再開性等 8 本すべて定性記述。「config 充填後」と後送り宣言はあるが、支出上限（NFR-6）とレート節度（NFR-7）は安全側の暫定値だけでも数値がないと S0 のゲート実装がテスト不能。
5. **evidence スキーマ未定義**。ペアゲート・自己審査禁止・公開証跡という本ハーネスの中核機構がすべて evidence テーブルに依存するのに、カラム定義がどこにもない。S0 受入基準①④が参照する以上、最小スキーマは要件段階の成果物。
6. **media-requirements のテンプレート不適合**。§0 が 7 観点必須と宣言しつつ、Canva/GenAI/Seedance/Notion/Claude Design/GA4 に「ワークフロー」「ゲート」欄がなく、stand.fm/Play に「ゲート」欄、PWA に「安全」欄がない。N/A なら N/A と書く（HELIX の「明示 N/A disposition」方式）。

## 4. Minor

1. 用語集なし（「ペア成立」「片肺 PASS」「攻略地図」「束縛承認」「ブラウザ突破」等の独自語多数。H/R/C 凡例が 2 文書に重複記載）。
2. 承認プロセスが「人の承認で confirmed」の一文のみ。承認ログ・レビュー記録の置き場未定義（HELIX は .helix/audit/ 相当の receipt を要求）。
3. テスト戦略が S0 受入テスト 3 本のみ。決定性（NFR-2）・再開性（NFR-3）の検証方法未定義。
4. バックアップ・復旧（SQLite/WP/ブラウザセッション）が未言及。

## 5. HELIX 基準のうち本プロジェクトに適用しないと判断してよいもの（過剰適用の防止）

HELIX 本体の全 apparatus（153 要件 ledger、SHA-256 statement digest、authority binding 24 set、canonical L1-L12 pair 等）をこの規模のプロジェクトに要求するのは過剰。以下は**意識的に不採用**と記録すれば足りる:

- statement digest / authority binding ledger（1 人 PO・同日起草のため drift リスクが小さい）
- 5 sub-doc 分割（現行の 6 文書構成で代替可能）
- 画面 prototype ゲート(ダッシュボードは S2 スライス送りで N/A receipt 相当が charter に既にある)
- 独立 runtime レビュー（ただし承認前に subagent adversarial review 1 回は推奨 — 本監査がその代替）

## 6. 反証条件

次のいずれかが真なら本監査の判定を撤回する: ① REQ→FR の対応が別文書に存在する ② AC が FR 帯ごとに別途定義済み ③ 公称件数が意図的な「確定分のみ」集計であると凡例に明記されている。監査時点でいずれも発見されていない。

## 7. 推奨クローズ順

1. C-3（件数修正、機械的・10分）→ 2. C-2（トレース方針決定＋対応列、1文書修正）→ 3. C-1（S0 FR への AC 付与＋S1+ deferred 宣言）→ 4. Important-5（evidence 最小スキーマ）→ 5. Important-1〜4（リスク登録簿・ADR 化・法規要求・NFR 暫定値）→ 承認 → S0 着手。
