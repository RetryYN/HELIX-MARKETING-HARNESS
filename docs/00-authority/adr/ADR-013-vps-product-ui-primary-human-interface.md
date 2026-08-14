---
artifact_id: AUTH-ADR-ADR-013-VPS-PRODUCT-UI-PRIMARY-HUMAN-INTERFACE
lifecycle_status: confirmed
slice: cross
---

# ADR-013: VPS 常駐化後は製品 Web UI を人間向け主入口とする

- status: accepted
- date: 2026-08-14
- decision_authority: PO（2026-08-14、VPS稼働実態・XServer API/CLI PoC・本対話で確定）
- 関連: ADR-007（VPS 無人車線）、ADR-010（旧 Discord 先行案）、BR-H2、BR-H3、FR-16、FR-46、FR-76

## 状況

製品runtimeをVPS常駐とする配置方針はADR-007により採用済みである。将来のVPS製品runtimeは承認待ち、
実行状態、停止理由、証跡、KPIの正本をVPS側API／永続状態へ置くため、それらを表示・操作する製品Web UIを
後付けの将来機能にする根拠は弱い。**現時点のVPSには製品runtime、service、Web UI、これらの製品状態正本は
実装・配備されていない。** 配置方針と稼働実態を混同しない。

ADR-010 は Discord App を初期承認入口、Web UI / PWA を将来入口とする。これは VPS 化を主軸に
要求を再構成する前の時系列であり、本ADRで投入順序を置換する。

## 決定

1. VPS 上の認証済み製品 Web UI を、承認・状態確認・失敗確認・運用通知の初期主入口とする。
   UI内inboxを初期通知経路に含める。
2. 通知は「状態が変化した事実」と「認証後に UI で対象を開く導線」を扱う。通知だけで承認を確定しない。
3. 投稿可否は UI 上でコンテンツプレビュー、対象媒体、操作、期限、binding を再表示し、
   許可済み principal の明示操作でのみ確定する。
4. Discord は製品の必須依存にしない。残す場合も UI への deep-link を送る任意の補助通知とし、
   Discord interaction 単体で approve / reject を確定しない。
5. 製品の投稿承認、運用通知、Discord 媒体へのコミュニティ投稿、開発 PR 通知を別の概念とし、
   policy・principal・宛先・証跡を共有しない。
6. UI は VPS DB / API を介してのみ状態を更新し、要求正本、discovery ledger、開発 memory を書き換えない。

## 現時点の非決定

本ADRは主入口と初期通知経路を決定する。次の実現方式は要求・設計としてまだ確定しない。

- UI framework、プロセス構成、配備方式、URL、port、reverse proxy
- 認証方式、session、CSRF、再認証、多要素認証、principal 管理
- Web Push / PWA pushは初期範囲外。将来追加時の到達保証・permission・失効要件
- Discord補助通知は初期範囲外。将来追加時もdeep-link通知だけに限定する
- 画面、API、状態遷移、エラー、AC、TC、運用手順

## 影響と進め方

ADR-007、010、BR-H2/H3、FR-16/46/76、機能一覧、AC/TC、S0 contract、DDL、L2 UI、L4〜L6 は
この要求の影響範囲である。本決定はADR-010の「Discord初期／Web UI将来」という投入順序を置換するが、
VPS側API／DBを正本としtransportから状態確定を分離する不変条件は継承する。現行設計を新要求の
根拠にせず、残る要求の質問・選択・承認が閉じた後にL2以降を再設計する。それまで旧Discord先行設計は
実装入力として確定済みとみなさない。
