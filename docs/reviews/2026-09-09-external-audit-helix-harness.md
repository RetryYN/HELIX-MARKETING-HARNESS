# 外部監査レビュー: HELIX-HARNESS の開発速度と証拠収束コスト（2026-09-09）

- 種別: **外部監査レビュー**（PO が 2026-09-09 に受領し、codex への共有を指示）。PO の決定でも HELIX の正式判定でもない。
- 対象: 上流 `RetryYN/HELIX-HARNESS`（本統合層からは read-only 参照）。言及される PR / Issue 番号・SHA はすべて上流のもの。
- 取り扱い: 本統合層は上流へ write しない。ここに置くのは共有と参照のため。上流への反映は PO が上流側で判断する。
- 原文は PO から受領したテキストをそのまま収録（見出し・表の整形のみ）。本統合層側の検証は行っていない。

---

## 総括

前回の「品質・統制が先行し、速度が弱い」という評価は維持。今回はさらに原因が明確になった。

**いま HELIX の開発速度を支配しているのは、実装能力ではなく "証拠を収束させるコスト" である。**

main 自体は壊れていない。むしろかなり健全。問題は、その堅牢さを維持したまま複数 PR を main へ流し込むところにある。

## 現在地

最新 main は `f2695861e228…`。#1672 `fix(runtime): converge project hook authority consumers` が 10:15 JST ごろにマージされた HEAD。main は protected で、required check は引き続き `harness-check`。この HEAD の main push harness-check も green。

#1672 の中身も大きい。Control Plane transport envelope を project-hook authority の基準にし、execution / loader / session / current authority の HEAD・source を個別観測しながら、SessionStart・doctor・status・native dispatch を同じ receipt / failure projection へ収束させている。明示的な envelope が壊れていれば provider dispatch 前に fail-close するところまで入った。

「HELIX が設計だけ増えている」という状態ではない。Control Plane 系も実経路へかなり降りている。

## ただし `src/cli.ts` はさらに悪化した

#1687 を起票したとき Claude が測った `src/cli.ts` は 704,434 bytes。今の main では 714,418 bytes。

すでに `src/cli/` は存在し、`commands/`、`full-regression-shards.ts`、`helpers.ts`、`lite-canary-selector.ts` などへの分離は始まっている。ただし commands 側に現時点で見えるのは `rename.ts` / `review-fallback.ts` / `route.ts` / `workflow.ts` 程度。

**多少分割しているのに、中央 root の成長速度の方が速い。** #1687 を入れた判断は正しかった。

## #1687 リファクタリング

Claude 側の着手条件は当初「#1668 + #1672 + #1679 が全部 `src/cli.ts` から退場したら開始」。#1672 はマージ済み、残りは #1668 と #1679。

#1672 をマージした直後、#1679 が中央 pin 系の 3 ファイルで衝突した。つまり、`src/cli.ts` を分割するだけでは不十分で、digest / line / count / semantic pin の中央集約も merge 直列化を発生させている。

#1687 の本当の成功条件は「巨大 CLI を小さくする」ではなく、**shared authority / shared pin / shared root による PR 間結合を減らす**こと。

## #1668 — exact HEAD CI binding

かなり完成に近い。HEAD `ea569cac…`、base は最新 main。mergeable=true、15 ファイル、+536/-78。

CI status を単なる branch window ではなく **candidate exact HEAD × target workflow** へ束縛する。Claude レビューで exact HEAD 判定 / workflow binding / window_miss fail-close / CLI exit code / expected HEAD 伝播 / mutation oracle / pin chain まで独立実測済み。PLAN 上の所有宣言と実 diff の矛盾まで踏み抜いた。

最新 HEAD の run 6859 は red。Lite と Windows は green だが `full-regression-preflight` の repo-wide guard preflight で止まり、先の重い工程は skip。**fail-fast が機能している red**。ただし base-sync のたびにこの binding を再成立させる必要があること自体が速度問題でもある。

## #1679 — pin-chain derivation

いま最重要の PR の一つ。open / draft、HEAD `69c8731…`、mergeable=false。

changed paths → 必要な digest / count / semantic pin → 重い CI を走らせる前に「何を追従しないといけないか」を列挙する。高速化に直接効く。

初回 Claude レビューで「登録済み path が 1 個でも混ざると未登録 path が silent success になる」穴と、重複 count 値で location を別 binding へ誤帰属する問題を発見。修正後の再レビューで blockers 0。

その後、**review evidence の session 帰属を誤って転記**する事故。実際にはその review をしていない Claude session を reviewer として記録していたため、作成側が自分で正本から撤回し、PLAN を draft へ戻した。HELIX が「approve と書いてある」ではなく「その session が本当にその HEAD を review したのか」まで問題にできるところまで来ている。

さらに #1672 merge 後、#1679 は中央 pin 3 ファイルで実際に conflict。**pin 高速化 PR 自身が pin 衝突で止まる。**

## #1681 — Oracle registration fail-close

未登録 oracle や「宣言していないのに複数箇所に出る oracle」を fail-close する。

初期実装は本文中に ID が書いてあるだけで registered 扱いできる穴を Codex に踏まれた（「本文に U-XXX と書けば登録済みに偽装できる」）。canonical structure 基準へ修正、現在は starting debt として 547 IDs を provenance 付きで capture。Claude も exact HEAD `158dc2eab` で実測。required CI はまだ red（repo-wide guard preflight で停止）。

**547 を「正常値」にしてはいけない。** starting debt の凍結値 + new debt ratchet として使うなら正しい。永久 baseline として神格化するとダメ。

## #1683 — outstanding fail-close

Cursor 実装 → Codex が schema-invalid plan_id の fail-open を発見 → Claude が修正後を独立検証 → さらに Codex が別の穴を発見、という流れ。

残 blocker: declared ID も filename も invalid → 全部 `invalid-plan-id` という同じ identity へ落としているため、悪意ある PLAN が 2 件以上存在すると同一 entity へ潰れて outstanding blocker を dedupe で消せる可能性。Codex 要求は「invalid PLAN 自体は消さない / raw invalid bytes は command へ出さない / path・content digest などから安全な distinct identity を作る / invalid PLAN を 2 件以上置く negative fixture を追加」。正しい。

Claude 自身も一度「harness-check green / independent review receipt」というまだ成立していない事実を closure receipt 例へ書き、自分で訂正した。HELIX は「AI が嘘をつく」だけでなく、**善意の AI が「形式上正しいが事実として間違った証拠」を作る**ケースまで実運用で踏み始めている。

## CI について

main の harness-check は green だが完走まで約 23 分。red PR は repo-wide guard preflight だけで約 3 分使ってから fail-fast。

「テストをもっと並列化」ではない。workflow には Lite closure selector / typed authorized skip / Windows lane 分離 / preflight / full regression / shard / aggregate まである。**次に削るべきなのは CPU 時間ではなく、無駄な証明の再生成。**

## 最大ボトルネック #538

strict up-to-date と current-HEAD receipt の組み合わせで、

PR A merge → PR B base stale → update branch → HEAD 変更 → CI 全再実行 → review receipt 失効 → Claude 再 review → その間に main 変更 → また最初から

が発生する。PR が N 本並ぶと O(N²) の CI + receipt 往復。#1672 → #1679 で実物を見ている。

#538 はもう backlog ではなく、**HELIX のスループット上限を決めている設計課題**。候補は (1) merge queue、(2) pure base-sync だけ機械証明して receipt を carry、(3) 現在の完全直列。長期的には 2 か 1。

## #1336 も優先度を上げるべき

main workflow は今も `group: harness-check-${{ github.ref }}` / `cancel-in-progress: true`。main push と schedule / manual が同じ ref なら、証明責務が違うのに同じ concurrency generation へ畳まれる。#1336（P1）は PR / main push / schedule / workflow_dispatch を typed event class として分ける。次に CI workflow へ手を入れる前にやるべき。

## マルチエージェント

評価上がった。構想段階ではなく、Cursor が作る → Codex が logic fail-open を踏む → Claude が exact HEAD で独立再測定 → Codex が別角度の collision を踏む → Claude 自身の誤った evidence も訂正する、というクロスレビューが回っている。

一方でインフラは alpha 感。#563: Claude review request が PR 単位 key で全 Claude session へ broadcast され、lease / claim / ACK がない。#1616: nested `claude --print` が 30 分 budget を超えて 42 分走り手動 kill。#1661: freeform material-review 通知が存在しない 40 桁 SHA を 2 件生成。

**multi-provider operation = 実動済み、24h unattended = hardening 不足。**

## 自己監査系

#1682 は「Issue 数や PR 数を進捗率にしない」と明示し、CANDIDATE / CONFIRMED / IMPLEMENTED / INTEGRATED / OPERATIONAL / PROVEN / HARDENING という capability maturity で全体を投影する。#1686 Internal Audit Crawler は既存監査を provider registry 化し incremental / deep を分離、PR critical path へ repo-wide full audit を毎回入れないと明記。高速化思想と矛盾しない。

## 現在の評価（公式進捗率ではなく監査側の現状評価）

| 領域 | 評価 | 状態 |
|---|---|---|
| Requirement / V-model | 9/10 | HARDENING |
| fail-close / evidence | 9/10 | HARDENING |
| CI correctness | 8.5/10 | 強い |
| Cross-agent review | 9/10 | 実戦投入済み |
| Control Plane authority | 8/10 | 統合進行 |
| Multi-provider execution | 7.5/10 | 実動 |
| 24h unattended robustness | 5.5/10 | timeout / lease 等が残る |
| CI throughput | 5/10 | 最大課題 |
| Merge convergence | 4/10 | 現在の最弱点 |
| Self-audit / inventory | 設計 7/10、統合 4〜5/10 | これから |
| Maintainability | 5/10 | cli.ts 714KB |
| Product distribution | pre-release | 今は主戦場ではない |

## これからの順序（監査側の提案）

**第一列: 中央競合を掃く** — #1668 → #1679 → #1687。#1668 を先に main へ収束。#1679 を最新 main へ同期し中央 pin の 3 conflict を処理して current-HEAD review まで通す。2 本が抜けた瞬間に #1687 の R00 baseline を取り直してリファクタ開始（baseline は 704KB でなく 714KB へ更新）。

**第二列: 並行して correctness を閉じる** — #1683 の invalid-plan-id collision、#1681 の oracle trace。中央 CLI リファクタと独立度が高い。

**第三列: 速度そのものを直す** — #1336 を先に、#538 を backlog から引き上げる。#538 は #1687 より長期インパクトが大きい可能性がある（#1687 は 1 PR あたりの衝突確率、#538 は PR が複数並んだときの O(N²) 再証明構造そのもの）。

その後 #1684 → #1685 → #1682 → #1686 で自己可視化を完成させる。

## 総評

評価が上がったのは「機能が増えた」からではなく、**HELIX 自身の厳格さが HELIX 自身の欠陥を現実の運用で踏み抜いている**から。reviewer provenance 誤帰属 / nonexistent SHA / format-valid・fact-invalid evidence / exact-HEAD 失効 / central pin conflict / PLAN ownership drift / invalid entity identity collision / CI・review bootstrap deadlock — 普通の個人開発ハーネスでは観測できない種類の問題。

一方で、このまま gate を増やし続けると品質システムが自分自身を DDoS するところまで来ている。

> **Proof weakening ではなく Proof-cost compression。** 「証拠を減らさず、同じ証拠へ到達する仕事量を減らす」。

#1679、#1687、#1336、#538 をこの一本のテーマで収束させるのが、今の HELIX に一番効く。

---

## 本統合層での位置づけ（Claude 追記）

- 上流の課題として WP-THEME 側で直接観測しているもの: #563 相当の broadcast / claim 問題は WP-THEME PR #174 の claude-inbox で `.superseded` / `.claim` が機能していることを確認済み。Claude → Codex の wake 非対称（上流 #532 / #854）は WP-THEME PR #182 `codex-inbox` で consumer 側の橋を実装済み。
- 上流への反映（#538 の格上げ、#1687 の baseline 更新、#1336 の先行）は PO が上流側で判断する。本統合層からは上流に write しない。
