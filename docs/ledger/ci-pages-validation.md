# GitHub Pages 検証境界

GitHub Pages は研究結果を生成する場所ではなく、repository に存在する evidence を機械的に閲覧する projection とする。正準データは `docs/`、`data/`、`generated/`、`api/` の repository file であり、Pages manifest は deploy 時に再生成する派生物である。

## Build contract

`scripts/build_pages_site.py` は canonical content roots を再帰走査し、`manifest.json` を生成する。テーマ名や個別研究を登録する allowlist は持たない。

各 entry には path、category、module、media type、size、viewer、exact revision の GitHub source/raw URL を記録する。5 MB 以下の file は Pages artifact に mirror し、それを超える file は source-only として exact revision へリンクする。

viewer は file type から決定する。

- JSON: formatted JSON
- CSV / TSV: generic table preview
- Markdown / text / log / YAML / TOML / XML / SQL: text
- image: image preview
- HTML / PDF: embedded preview
- その他または mirror threshold 超過: source/download link

## Pull Request candidate

`Build and deploy modular evidence browser` workflow は変更 commit から `_site` を生成し、次を検証する。

- synthetic test で、新しい module/file が UI や workflow の個別変更なしに manifest へ追加される
- manifest revision が candidate commit と一致する
- manifest path が重複しない
- manifest に記録した mirrored file がすべて実在する
- `docs` / `data` / `generated` / `api` の各 canonical root が discovery 対象になっている
- HTTP 経由で index、manifest、revision、JS、CSS、代表 artifact を取得できる

検証証拠は `pages-candidate-validation-<commit SHA>` artifact に保存する。Pull Request の合否には production URL を使わない。

## main deployment

main の Pages deploy 成功後、`Verify deployed GitHub Pages` workflow が production を polling する。`revision.json` と `manifest.json` の revision が deploy 対象 commit と一致し、generic frontend と代表 mirrored artifact が実際に取得できた場合だけ release verification を成功とする。

検証証拠は `pages-production-validation-<commit SHA>` artifact に保存する。merge と release は別状態として扱う。
