import discord
from discord.ext import commands
import yaml
import os
from ARONA.spam_blocker.error.errors import setup_error_handler


def load_config():
    """設定ファイルを読み込む"""
    with open('config.yaml', 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


class SpamBlockerCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = load_config()
        print(f'許可されたBOT: {self.config.get("allowed_bots", [])}')
        print(f'監視対象サーバー: {self.config.get("monitored_guilds", [])}')
        print(f'監視対象チャンネル: {self.config.get("monitored_channels", [])}')

    @commands.Cog.listener()
    async def on_message(self, message):
        # BOT自身のメッセージは無視
        if message.author == self.bot.user:
            return

        # DMは無視
        if not message.guild:
            return

        # 監視対象サーバーのチェック
        monitored_guilds = self.config.get('monitored_guilds', [])
        if monitored_guilds and str(message.guild.id) not in monitored_guilds:
            return

        # 監視対象チャンネルかチェック
        monitored_channels = self.config.get('monitored_channels', [])
        channel_id = str(message.channel.id)
        if monitored_channels and channel_id not in monitored_channels:
            return

        # 管理者は常に許可
        if hasattr(message.author, 'guild_permissions') and message.author.guild_permissions.administrator:
            return

        # BOTの場合
        if message.author.bot:
            allowed_bots = self.config.get('allowed_bots', [])
            # 許可リストに含まれていないBOTのメッセージを削除
            if str(message.author.id) not in allowed_bots:
                await message.delete()
                print(f'削除: 許可されていないBOT {message.author.name} (ID: {message.author.id})')

                # 警告メッセージを送信(オプション)
                if self.config.get('send_warning', False):
                    warning = await message.channel.send(
                        f'⚠️ 許可されていないBOT `{message.author.name}` の投稿を削除しました。'
                    )
                    # 5秒後に警告メッセージも削除
                    await warning.delete(delay=5)

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def add_guild(self, ctx, guild_id: str):
        """監視対象サーバーを追加"""
        monitored_guilds = self.config.get('monitored_guilds', [])
        if guild_id not in monitored_guilds:
            monitored_guilds.append(guild_id)
            self.config['monitored_guilds'] = monitored_guilds
            with open('config.yaml', 'w', encoding='utf-8') as f:
                yaml.dump(self.config, f, allow_unicode=True)
            await ctx.send(f'✅ サーバー ID `{guild_id}` を監視対象に追加しました')
        else:
            await ctx.send(f'⚠️ サーバー ID `{guild_id}` は既に監視対象です')

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def reload_config(self, ctx):
        """設定ファイルを再読み込み"""
        try:
            self.config = load_config()
            await ctx.send('✅ 設定ファイルを再読み込みしました')
        except Exception as e:
            await ctx.send(f'❌ エラー: {e}')

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def list_bots(self, ctx):
        """許可されているBOTのリストを表示"""
        bot_list = '\n'.join([f'- <@{bot_id}>' for bot_id in self.config['allowed_bots']])
        embed = discord.Embed(
            title='許可されたBOT一覧',
            description=bot_list if bot_list else 'なし',
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def add_bot(self, ctx, bot_id: str):
        """許可BOTリストにBOTを追加"""
        if bot_id not in self.config['allowed_bots']:
            self.config['allowed_bots'].append(bot_id)
            with open('config.yaml', 'w', encoding='utf-8') as f:
                yaml.dump(self.config, f, allow_unicode=True)
            await ctx.send(f'✅ BOT ID `{bot_id}` を許可リストに追加しました')
        else:
            await ctx.send(f'⚠️ BOT ID `{bot_id}` は既に許可リストに含まれています')

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def remove_bot(self, ctx, bot_id: str):
        """許可BOTリストからBOTを削除"""
        if bot_id in self.config['allowed_bots']:
            self.config['allowed_bots'].remove(bot_id)
            with open('config.yaml', 'w', encoding='utf-8') as f:
                yaml.dump(self.config, f, allow_unicode=True)
            await ctx.send(f'✅ BOT ID `{bot_id}` を許可リストから削除しました')
        else:
            await ctx.send(f'⚠️ BOT ID `{bot_id}` は許可リストに含まれていません')

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def add_channel(self, ctx, channel_id: str):
        """監視対象チャンネルを追加"""
        if channel_id not in self.config['monitored_channels']:
            self.config['monitored_channels'].append(channel_id)
            with open('config.yaml', 'w', encoding='utf-8') as f:
                yaml.dump(self.config, f, allow_unicode=True)
            await ctx.send(f'✅ チャンネル ID `{channel_id}` を監視対象に追加しました')
        else:
            await ctx.send(f'⚠️ チャンネル ID `{channel_id}` は既に監視対象です')


async def setup(bot):
    await bot.add_cog(SpamBlockerCog(bot))