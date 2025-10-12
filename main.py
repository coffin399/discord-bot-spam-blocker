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


# intentsの設定
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!!!', intents=intents)


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


config = load_config()


@bot.event
async def on_ready():
    print(f'{bot.user} でログインしました')
    print(f'許可されたBOT: {config.get("allowed_bots", [])}')
    print(f'監視対象サーバー: {config.get("monitored_guilds", [])}')
    print(f'監視対象チャンネル: {config.get("monitored_channels", [])}')
    print('📱 モバイルステータスで表示されています')

    # ステータスメッセージを設定
    await bot.change_presence(
        activity=discord.Game(name="blocking spam...")
    )


@bot.event
async def on_message(message):
    # BOT自身のメッセージは無視
    if message.author == bot.user:
        return

    # 設定の存在確認
    if not config:
        await bot.process_commands(message)
        return

    # 監視対象サーバーのチェック
    monitored_guilds = config.get('monitored_guilds', [])
    if monitored_guilds and str(message.guild.id) not in monitored_guilds:
        await bot.process_commands(message)
        return

    # 監視対象チャンネルかチェック
    monitored_channels = config.get('monitored_channels', [])
    channel_id = str(message.channel.id)
    if monitored_channels and channel_id not in monitored_channels:
        await bot.process_commands(message)
        return

    # 管理者は常に許可
    if message.author.guild_permissions.administrator:
        await bot.process_commands(message)
        return

    # BOTの場合
    if message.author.bot:
        allowed_bots = config.get('allowed_bots', [])
        # 許可リストに含まれていないBOTのメッセージを削除
        if str(message.author.id) not in allowed_bots:
            await message.delete()
            print(f'削除: 許可されていないBOT {message.author.name} (ID: {message.author.id})')

            # 警告メッセージを送信（オプション）
            if config.get('send_warning', False):
                warning = await message.channel.send(
                    f'⚠️ 許可されていないBOT `{message.author.name}` の投稿を削除しました。'
                )
                # 5秒後に警告メッセージも削除
                await warning.delete(delay=5)
    else:
        # 一般ユーザーの投稿処理（必要に応じて）
        pass

    await bot.process_commands(message)


@bot.command()
@commands.has_permissions(administrator=True)
async def add_guild(ctx, guild_id: str):
    """監視対象サーバーを追加"""
    monitored_guilds = config.get('monitored_guilds', [])
    if guild_id not in monitored_guilds:
        monitored_guilds.append(guild_id)
        config['monitored_guilds'] = monitored_guilds
        with open('config.yaml', 'w', encoding='utf-8') as f:
            yaml.dump(config, f, allow_unicode=True)
        await ctx.send(f'✅ サーバー ID `{guild_id}` を監視対象に追加しました')
    else:
        await ctx.send(f'⚠️ サーバー ID `{guild_id}` は既に監視対象です')


@bot.command()
@commands.has_permissions(administrator=True)
async def reload_config(ctx):
    """設定ファイルを再読み込み"""
    global config
    try:
        config = load_config()
        await ctx.send('✅ 設定ファイルを再読み込みしました')
    except Exception as e:
        await ctx.send(f'❌ エラー: {e}')


@bot.command()
@commands.has_permissions(administrator=True)
async def list_bots(ctx):
    """許可されているBOTのリストを表示"""
    bot_list = '\n'.join([f'- <@{bot_id}>' for bot_id in config['allowed_bots']])
    embed = discord.Embed(
        title='許可されたBOT一覧',
        description=bot_list if bot_list else 'なし',
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)


@bot.command()
@commands.has_permissions(administrator=True)
async def add_bot(ctx, bot_id: str):
    """許可BOTリストにBOTを追加"""
    if bot_id not in config['allowed_bots']:
        config['allowed_bots'].append(bot_id)
        with open('config.yaml', 'w', encoding='utf-8') as f:
            yaml.dump(config, f, allow_unicode=True)
        await ctx.send(f'✅ BOT ID `{bot_id}` を許可リストに追加しました')
    else:
        await ctx.send(f'⚠️ BOT ID `{bot_id}` は既に許可リストに含まれています')


@bot.command()
@commands.has_permissions(administrator=True)
async def remove_bot(ctx, bot_id: str):
    """許可BOTリストからBOTを削除"""
    if bot_id in config['allowed_bots']:
        config['allowed_bots'].remove(bot_id)
        with open('config.yaml', 'w', encoding='utf-8') as f:
            yaml.dump(config, f, allow_unicode=True)
        await ctx.send(f'✅ BOT ID `{bot_id}` を許可リストから削除しました')
    else:
        await ctx.send(f'⚠️ BOT ID `{bot_id}` は許可リストに含まれていません')


@bot.command()
@commands.has_permissions(administrator=True)
async def add_channel(ctx, channel_id: str):
    """監視対象チャンネルを追加"""
    if channel_id not in config['monitored_channels']:
        config['monitored_channels'].append(channel_id)
        with open('config.yaml', 'w', encoding='utf-8') as f:
            yaml.dump(config, f, allow_unicode=True)
        await ctx.send(f'✅ チャンネル ID `{channel_id}` を監視対象に追加しました')
    else:
        await ctx.send(f'⚠️ チャンネル ID `{channel_id}` は既に監視対象です')


# BOTを起動
if __name__ == '__main__':
    token = config.get('bot_token')
    if not token:
        print('エラー: config.yaml に bot_token が設定されていません')
    else:
        # モバイルステータスを有効化
        discord.gateway.DiscordWebSocket.identify = mobile_identify
        bot.run(token)