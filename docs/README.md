# Discord Spam Blocker - 公式サイト

Discord Spam Blockerの公式ウェブサイトです。GitHub Pagesでホストされています。

## サイト構成

- `index.html` - メインページ
- `features.html` - 機能詳細ページ
- `setup.html` - セットアップガイド
- `commands.html` - コマンドリファレンス
- `styles.css` - スタイルシート
- `script.js` - JavaScript機能

## デプロイ方法

このサイトはGitHub Pagesで自動デプロイされます。

1. リポジトリの設定で「Pages」を有効化
2. ソースを「Deploy from a branch」に設定
3. ブランチを「main」、フォルダを「/docs」に設定

## ローカル開発

ローカルでサイトを確認するには、docsディレクトリをHTTPサーバーで配信してください。

```bash
# Python 3の場合
cd docs
python -m http.server 8000

# Node.jsの場合
npx serve docs
```

## カスタマイズ

サイトのカスタマイズは以下のファイルを編集してください：

- 色やスタイル: `styles.css`
- 機能やアニメーション: `script.js`
- コンテンツ: 各HTMLファイル

## ライセンス

このプロジェクトは自由に使用・改変できます。
