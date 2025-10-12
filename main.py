import discord
from discord.ext import commands
import yaml
import os


# Botをモバイルとして識別させるためのカスタム関数
async def mobile_identify(self):
    """Botをモバイルとして識別させるためのカスタム関数"""
    payload = {
        'op': self.IDENTIFY,
        'd': {
            'token': self.token,
            'properties': {
                '$os': 'Discord Android',
                '$browser': 'Discord Android',
                '$device': 'Discord Android'
            },
            'compress': True,
            'large_threshold': 250,
            'intents': self._connection.intents.value
        }
    }
    if self.shard_id is not None and self.shard_count is not None:
        payload['d']['shard'] = [self.shard_id, self.shard_count]
    state = self._connection
    if state._activity is not None or state._status is not None:
        payload['d']['presence'] = {
            'status': state._status,
            'game': state._activity,
            'since': 0,
            'afk': False
        }
    await self.call_hooks('before_identify', self.shard_id, initial=self._initial_identify)
    await self.send_as_json(payload)


# 設定を読み込む
def load_config():
    import shutil

    # config.yamlが存在しない場合、config.default.yamlからコピー
    if not os.path.exists('config.yaml'):
        if os.path.exists('config.default.yaml'):
            shutil.copy('config.default.yaml', 'config.yaml')
            print('✅ config.default.yaml から config.yaml を作成しました')
            print('⚠️  config.yaml を編集してbot_tokenなどを設定してください')
        else:
            print('❌ エラー: config.default.yaml が見つかりません')
            exit(1)

    with open('config.yaml', 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


# エラーハンドラーをセットアップ
def setup_error_handler(bot):
    """グローバルエラーハンドラーを設定"""

    @bot.event
    async def on_command_error(ctx, error):
        if isinstance(error, commands.CommandNotFound):
            return
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f'❌ 必要な引数が不足しています: {error.param.name}')
        elif isinstance(error, commands.MissingPermissions):
            await ctx.send('❌ このコマンドを実行する権限がありません')
        else:
            await ctx.send(f'❌ エラーが発生しました: {str(error)}')
            print(f'Error: {error}')


# intentsの設定
intents = discord.Intents.default()
intents.message_content = True
intents.members = True  # メンバー参加イベントを受信するために必要
intents.guilds = True

bot = commands.Bot(command_prefix='!!!', intents=intents)


@bot.event
async def on_ready():
    print('=' * 50)
    print(f'🤖 {bot.user} でログインしました')
    print('📱 モバイルステータスで表示されています')
    print(f'🌐 {len(bot.guilds)} サーバーに接続中')
    print('=' * 50)

    # ステータスメッセージを設定
    await bot.change_presence(
        activity=discord.Game(name="spam blocker v1.0")
    )


# エラーハンドラーをセットアップ
setup_error_handler(bot)


# Cogを読み込む
async def load_extensions():
    """全てのCogを読み込む"""
    extensions = [
        'ARONA.spam_blocker.spam_blocker_cog.py',
        'ARONA.music.music_cog',
        'ARONA.message.welcome_message_cog.py',  # 新しく追加
    ]

    for ext in extensions:
        try:
            await bot.load_extension(ext)
            print(f'✅ {ext} を読み込みました')
        except Exception as e:
            print(f'❌ {ext} の読み込みに失敗しました: {e}')


# BOTを起動
if __name__ == '__main__':
    config = load_config()
    token = config.get('bot_token')

    if not token:
        print('❌ エラー: config.yaml に bot_token が設定されていません')
        exit(1)
    else:
        # モバイルステータスを有効化
        discord.gateway.DiscordWebSocket.identify = mobile_identify

        # Cogを読み込んでからBOTを起動
        import asyncio


        async def main():
            async with bot:
                await load_extensions()
                await bot.start(token)


        asyncio.run(main())