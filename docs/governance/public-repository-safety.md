# 公開リポジトリ安全規約

## 目的と適用範囲

本規約は `HELIX-MARKETING-HARNESS` 統合層と、`media/`・`base/` 配下の全 submodule に適用する。
credential の漏えいだけでなく、公開する必要のない運用情報や第三者由来コンテンツが Git 履歴、
Issue、PR、CI log、ハーネスメモリへ残ることを防ぐ。

## 公開してはならない情報

- password、token、private key、Application Password、cookie、接続文字列などの credential
- 実運用サイトを特定する非公開の domain、site ID、account ID、内部 endpoint、host 名
- 個人名を含むローカル絶対パス、SSH 設定、端末固有情報
- affiliate URL、広告 click URL、追跡 query、未マスクの広告・媒体識別子
- 許諾または公開目的を確認していない記事本文、見出し一覧、顧客データ、管理画面の raw dump
- 非公開調査対象の製品名・vendor 名と、伏せ字名を結び付ける対応表

公開情報、WordPress やライブラリの一般的な製品名、再現に必要な架空 fixture は禁止対象ではない。
ただし「公開済みだから複製してよい」とは扱わず、証跡は digest、件数、schema、伏せ字例など、
目的を満たす最小表現にする。

## 必須運用

1. raw evidence はまずリポジトリ外へ保存し、公開可能な派生物だけを commit する。
2. 調査対象は `テーマA`、`サービスB` などの役割名へ置換し、対応表を commit しない。
3. commit 前に `bash scripts/check-public-safety.sh --staged` を実行する。
4. 調査・証跡・PoC artifact の変更時は `.public-safety.local.regex` または
   `PUBLIC_REDACTION_GUARD_RE` に非公開の検出正規表現を設定する。ファイルは一行一正規表現とする。
5. PR では統合層の CI が root 差分と submodule の旧 pin→新 pin 差分を検査する。
6. 検査結果を回避するための分割、難読化、無期限 allowlist、実値を含む allowlist を禁止する。

CI は標準トークンで取得できる公開 submodule を検査する。private submodule の pin を変更するPRは、
read token がない状態では検査不能としてfail-closeするため、公開前に権限付きの検査laneを用意する。

初回 clone と submodule 追加後は `bash scripts/install-public-safety-hooks.sh` を実行する。
tracked `pre-commit` / `pre-push` hook が統合層と初期化済み submodule の Git 操作へ割り込み、
commit 前の staged 差分と push 前の送信範囲を検査する。既存の `core.hooksPath` がある場合、installer は
上書きせず fail-close する。

## 例外

実値の公開が成果物の目的そのものである場合だけ、PO が対象、理由、owner、失効日を明示して
承認できる。credential、private key、認証 cookie は例外にできない。例外記録にも秘密そのものを
書かない。

## 既存履歴と事故対応

ガード導入前の既存情報は自動的に安全とはみなさない。別監査で所在、公開必要性、影響を分類し、
通常 commit での伏せ字化と履歴改変を分ける。事故時は次の順で対応する。

1. credential なら履歴操作より先に revoke / rotate する。
2. 公開 branch と PR を安全な履歴へ再構築する。
3. force-push は PO の明示承認後、固定した旧 SHA に対する `--force-with-lease` で行う。
4. branch、tag、PR、fork、旧 SHA の到達性を確認する。
5. GitHub 内部の cached view まで消す必要がある機微情報は GitHub Support へ purge を依頼する。
6. 実施結果と残余リスクをハーネスメモリへ記録する。

## ガードの責務境界

機械検査は高確度の credential、個人環境パス、追跡 URL、および非公開正規表現を検出する。
記事転載や文脈上の公開可否を完全には判定できないため、人の公開レビューを置き換えない。
