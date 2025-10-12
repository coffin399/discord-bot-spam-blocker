# Discord スパム対策 BOT

Discord サーバーで許可されていない BOT の投稿を自動的に削除するスパム対策 BOT です。YAML ファイルで簡単に設定でき、特定のチャンネルのみを監視することも可能です。

## 機能

- ✅ 許可リストに基づく BOT 投稿の制御
- ✅ 特定チャンネルのみを監視対象に設定可能
- ✅ 管理者権限を持つユーザーは常に投稿可能
- ✅ コマンドによる動的な設定変更
- ✅ 削除時の警告メッセージ表示（オプション）
- ✅ YAML ファイルによる簡単な設定管理

## セットアップ

### 1. 必要なライブラリをインストール

**Windows の場合（start.bat で自動インストール）：**
```bash
start.bat
```
初回実行時に必要なライブラリが自動的にインストールされます。

**Mac/Linux の場合：**
```bash
pip install discord.py pyyaml
```

### 2. ファイルを配置

以下のファイルを同じディレクトリに配置してください：

- `bot.py` - BOT 本体
- `config.default.yaml` - デフォルト設定ファイル

### 3. Discord BOT を作成

1. [Discord Developer Portal](https://discord.com/developers/applications) にアクセス
2. 「New Application」をクリックして新しいアプリケーションを作成
3. 「Bot」タブに移動し、「Add Bot」をクリック
4. 「TOKEN」セクションで「Copy」をクリックしてトークンをコピー
5. 「Privileged Gateway Intents」で以下を有効化：
   - `MESSAGE CONTENT INTENT`
   - `SERVER MEMBERS INTENT`

### 4. BOT をサーバーに招待

1. Developer Portal の「OAuth2」→「URL Generator」に移動
2. 「SCOPES」で `bot` を選択
3. 「BOT PERMISSIONS」で以下を選択：
   - `Read Messages/View Channels`
   - `Send Messages`
   - `Manage Messages`
   - `Read Message History`
4. 生成された URL からサーバーに BOT を招待

### 5. 初回起動と設定

```bash
python bot.py
```

初回起動時に `config.yaml` が自動生成されます。

### 6. config.yaml を編集

`config.yaml` を開いて以下を設定：

```yaml
# Discord BOTトークン（必須）
bot_token: "YOUR_BOT_TOKEN_HERE"

# 許可するBOTのIDリスト
allowed_bots:
  - "123456789012345678"  # 許可したいBOTのIDを追加
  - "234567890123456789"

# 監視対象のチャンネルID
monitored_channels:
  - "345678901234567890"  # 監視したいチャンネルIDを追加
  - "456789012345678901"

# 削除時に警告メッセージを送信するか
send_warning: true
```

### 7. BOT を起動

**Windows の場合：**
```bash
start.bat
```

**Mac/Linux の場合：**
```bash
python bot.py
```

## BOT ID・チャンネル ID の取得方法

1. Discord の「設定」→「詳細設定」→「開発者モード」を有効化
2. BOT またはチャンネルを右クリック
3. 「ID をコピー」を選択

## 管理コマンド

すべてのコマンドは管理者権限が必要です。コマンドプレフィックスは `!!!` です。

### BOT 管理

- `!!!add_bot <BOT_ID>` - 許可 BOT リストに追加
- `!!!remove_bot <BOT_ID>` - 許可 BOT リストから削除
- `!!!list_bots` - 許可されている BOT の一覧を表示

### チャンネル管理

- `!!!add_channel <CHANNEL_ID>` - 監視対象チャンネルを追加

### その他

- `!!!reload_config` - 設定ファイルを再読み込み

## 使用例

```bash
# 許可BOTを追加
!!!add_bot 123456789012345678

# 許可BOTを削除
!!!remove_bot 123456789012345678

# 許可BOTの一覧を表示
!!!list_bots

# 監視チャンネルを追加
!!!add_channel 345678901234567890

# 設定を再読み込み
!!!reload_config
```

## ファイル構成

```
.
├── bot.py                   # BOT本体
├── config.default.yaml      # デフォルト設定（テンプレート）
├── config.yaml             # 実際の設定（自動生成）
├── start.bat               # Windows用起動スクリプト
└── README.md               # このファイル
```

## セキュリティ注意事項

- `config.yaml` には BOT トークンなどの機密情報が含まれます
- Git にコミットする場合は、必ず `.gitignore` に `config.yaml` を追加してください
- `config.default.yaml` のみをコミットし、`config.yaml` はローカルで管理してください

### .gitignore の例

```
config.yaml
__pycache__/
*.pyc
```

## トラブルシューティング

### BOT が起動しない

- `config.yaml` に正しい BOT トークンが設定されているか確認
- 必要なライブラリがインストールされているか確認

### BOT が投稿を削除しない

- BOT に「メッセージを管理」権限があるか確認
- `config.yaml` の `monitored_channels` に正しいチャンネル ID が設定されているか確認
- Discord の開発者モードが有効になっているか確認

### コマンドが動作しない

- コマンドを実行するユーザーに管理者権限があるか確認
- コマンドの前に `!!!` が付いているか確認

## ライセンス

このプロジェクトは自由に使用・改変できます。

## 貢献

バグ報告や機能追加の提案は歓迎します！