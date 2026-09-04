# CLAUDE.md — 統合層の作業規律

本リポジトリは媒体別ハーネスの**統合層**。実開発は各媒体リポ（submodule）側で行う。

## 作業境界

- 変更対象は本リポジトリと、明示指示のあった媒体リポのみ。
  `RetryYN/HELIX-HARNESS` と `RetryYN/TAKUMI_CMO-Claude_Cowark` は read-only 参照。
  他リポジトリへの書き込みは、指示に含まれていても着手前に PO へ確認する。
- credential を repository・DB・ログへ書かない。
- 公開・外部 write は PO 承認前に行わない。

## 傘下リポ共通規律（media/・base/ の全 submodule に適用）

本節が共通規律の**正本**。傘下リポの CLAUDE.md は本節を継承し、リポ固有の追記だけを持つ
（規律のコピー増殖・独自改変をしない。矛盾時は本節が優先）。

1. PO 承認前に外部（本番 WP・公開先・第三者サービス）への write をしない。
2. credential を repository・DB・ログへ書かない。
3. 進行順序は PoC（実機証跡）→ 要求 → 設計 → 実装。証跡なしに実装へ進まない。
4. cross-repo 編集禁止。他リポへの書き込みは指示に含まれていても着手前に PO へ確認する。
5. 破壊的・不可逆な操作（削除・rename・force-push・履歴改変）は PO の明示判断を得てから行う。
6. 公開リポジトリへ、credential に限らず、実運用サイトを特定する情報、個人環境の絶対パス、
   広告・affiliate の追跡識別子、転載許諾を確認していない記事本文、非公開調査対象の固有名を
   記録しない。read-only 証跡も公開可能な最小表現へ変換し、原文・対応表はリポジトリ外で扱う。
7. commit / push / Issue・PR 起票前に `bash scripts/check-public-safety.sh --staged` 相当の
   公開情報検査を通す。調査・証跡・PoC artifact を変更する場合は、非公開の固有名対応表を
   `PUBLIC_REDACTION_GUARD_RE` または `.public-safety.local.regex` から注入する。

公開情報の分類、例外、事故対応の正本は
`docs/governance/public-repository-safety.md` とする。検査を通すために実値を allowlist へ追加しては
ならず、例外は理由・owner・期限を持つ PO 判断として扱う。

## 構成ルール

- 媒体単位のディレクトリ = 独立リポジトリ（git submodule、`media/<媒体>/`）。
  媒体追加は「PO 判断 → 新リポ作成 → submodule 追加」の順。
- 統合層には共通方針・媒体一覧・commit pin 以外を置かない
  （要求・設計・実装・テストは媒体リポ側が正本）。
- 旧単一リポ路線の全体は tag `legacy/single-repo-final` に凍結済み（read-only 参照）。
  main へ旧路線の成果物を書き戻さない。

## 運用メモ

- 媒体リポへの push: SSH deploy key は本リポ限定のため
  `git -c credential.helper='!gh auth git-credential' push` を使う。
- レビューが必要な変更は codex-astra（gpt-6-astra、effort low。PO 判断 2026-09-05、Sol の上位として採用。Astra 不可時は codex-sol）、通常タスクは codex-luna（effort max）。

## GitHub 運用ルール（HELIX 本体を継承）

正本は `RetryYN/HELIX-HARNESS` の `docs/governance/github-operation-rules.md` と
`github-issue-hierarchy-rules.md`（vendor 版: `media/wp/node_modules/helix/docs/governance/`）。
本節の「事前承認済み」範囲は PO が 2026-08-27 に承認済みで、都度の確認なしに実行してよい。

- **Issue**: root / capability / task / finding の階層。本文に
  `issue_role / parent_issue / blocks / blocked_by / duplicate_search / disposition / duplicate_of` の exact block。
  依存があれば `# helix-issue-dependency.v1` block（`depends_on` / `blocks` を双方向一致）。
  label は type（`bug|feature|enhancement|update`）+ `priority:*`（または `state:*`）を同一操作で付与、
  責務が分かれば `area:*` も付ける。起票前に duplicate search。
  公開リポでは第三者製品名・ベンダー名・ドメインを伏せ字にする。
- **Branch**: governed prefix のみ（`feature/ design/ research/ poc/ reverse/ add/ hotfix/ refactor/ docs/ chore/`、
  automation は `codex/`）。`fix/ work/ bugfix/` と未登録 prefix は使わない。
- **PR**: Draft で作り、本文に 6 項目の `## HELIX scope manifest`
  （Behavior contract / Responsibility owner / Allowed path families / Expected changed paths /
  Required companion paths / Scope expansion: none）。`src/` を触る PR は PLAN と tests companion を同 diff に含める。
  Claude 作成 PR の ready/merge は Codex lane に委譲する。
- **事前承認済み（確認不要）**: Issue の作成・編集・label、Draft PR の作成・更新、
  非 main ブランチへの push、統合層（本リポ）main への直接 push（docs・設定・pin 更新）、
  リポ内起票スクリプト（`create-issues-helix.sh` 等）の実行。
- **条件付き事前承認（PO 2026-09-02、HELIX 本体の main 運用と同等）**: 傘下リポ main への merge は、
  会話で PO が merge を指示し、codex-astra（代替時は codex-sol）の最終レビューが現 head に対して「merge 可」を返し、CI が green のとき、
  `gh pr ready` → `gh pr merge --merge`（merge commit。squash / rebase / ブランチ削除 / admin 強行は不可）で実行してよい。
- **引き続き PO 明示判断が要る**: Astra / Sol「merge 可」なしの main merge、force-push、tag/release/cutover、ブランチ・Issue の削除、
  `HELIX-HARNESS` / `TAKUMI_CMO-Claude_Cowark` への write、本番 WP・第三者サービスへの write。
