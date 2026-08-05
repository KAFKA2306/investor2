# GitHub Pages検証境界

このリポジトリでは、Pull Requestの候補成果物と、mainへデプロイされた本番成果物を別の検証対象として扱う。

## Pull Request候補

`Validate and deploy AAARTS evidence dashboard` workflowが、そのcommitから `_site` を生成する。候補サイトをローカルHTTPサーバーで配信し、同じworkflow内でHTMLとmanifestを取得する。

検証内容は固定件数ではなく、次の意味契約である。

- `summary.tested_hypotheses` と実レコード数が一致する
- 判定別集計がレコード集合から再計算した値と一致する
- 仮説ID、外部主張ID、証拠参照が空でなく重複しない
- buildのcommit SHAとrun IDが存在する
- `CONFIRMED` は必須の時系列OOS、統計、安定性、コスト、Point-in-Time、売買可能性ゲートがすべてPASSである
- HTMLに主要landmark、結果表、manifest取得処理が存在する

検証ログと取得済みHTML・manifestは `pages-candidate-validation-<commit SHA>` artifactへ保存する。Pull Requestでは公開中の本番URLを合否判定に使わない。

## mainデプロイ後の本番

`Verify deployed GitHub Pages` workflowは、Pages build/deploy workflowがmainで成功した後にだけ `workflow_run` から起動する。公開URLを上限20回、6秒間隔でpollingし、manifest内の `build.code_sha` がデプロイ対象commitと一致するまで待つ。

上限内に一致しない場合は、期待commit、各試行、取得済みファイルを残して失敗する。固定sleepだけで成功扱いにはしない。本番検証ログは `pages-production-validation-<commit SHA>` artifactへ保存する。

## 変更時の原則

仮説数や判定数そのものは恒久契約ではない。正当な追加・削除・判定変更は、レコード、集計、証拠ゲート、来歴が相互整合していれば受け入れる。集計値だけの変更、重複ID、根拠不足の強判定、候補HTMLの破損はCIで拒否する。
