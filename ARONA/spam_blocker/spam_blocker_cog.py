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

    def should_block_message(self, message):
        """メッセージをブロックすべきか判定"""
        # 埋め込みのチェック
        if message.embeds and self.config.get('block_embeds', False):
            return True

        # スパムキーワードのチェック
        spam_keywords = self.config.get('spam_keywords', [])
        if spam_keywords:
            content = message.content.lower()
            for keyword in spam_keywords:
                if keyword.lower() in content:
                    return True

            # 埋め込みのタイトル・説明文もチェック
            for embed in message.embeds:
                if embed.title and any(keyword.lower() in embed.title.lower() for keyword in spam_keywords):
                    return True
                if embed.description and any(keyword.lower() in embed.description.lower() for keyword in spam_keywords):
                    return True

        return False

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

            # 許可リストに含まれているBOTはスキップ
            if str(message.author.id) in allowed_bots:
                return

            # 許可されていないBOTのメッセージをチェック
            should_delete = False
            delete_reason = ""

            # デフォルト: 許可されていないBOTは全て削除
            if self.config.get('block_all_unauthorized_bots', True):
                should_delete = True
                delete_reason = "許可されていないBOT"
            # または特定の条件でのみ削除
            elif self.should_block_message(message):
                should_delete = True
                delete_reason = "スパムコンテンツを検出"

            if should_delete:
                await message.delete()

                # ログ出力
                log_msg = f'削除: {delete_reason} {message.author.name} (ID: {message.author.id})'
                if message.embeds:
                    log_msg += f' - 埋め込み数: {len(message.embeds)}'
                print(log_msg)

                # 警告メッセージを送信(オプション)
                if self.config.get('send_warning', False):
                    warning_text = f'⚠️ {delete_reason}: `{message.author.name}` の投稿を削除しました'
                    if message.embeds:
                        warning_text += f' (埋め込み: {len(message.embeds)}個)'

                    warning = await message.channel.send(warning_text)
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

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def add_keyword(self, ctx, *, keyword: str):
        """スパムキーワードを追加"""
        spam_keywords = self.config.get('spam_keywords', [])
        if keyword not in spam_keywords:
            spam_keywords.append(keyword)
            self.config['spam_keywords'] = spam_keywords
            with open('config.yaml', 'w', encoding='utf-8') as f:
                yaml.dump(self.config, f, allow_unicode=True)
            await ctx.send(f'✅ キーワード `{keyword}` をスパムリストに追加しました')
        else:
            await ctx.send(f'⚠️ キーワード `{keyword}` は既にスパムリストに含まれています')

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def list_keywords(self, ctx):
        """スパムキーワード一覧を表示"""
        keywords = self.config.get('spam_keywords', [])
        if keywords:
            keyword_list = '\n'.join([f'- {kw}' for kw in keywords])
            embed = discord.Embed(
                title='スパムキーワード一覧',
                description=keyword_list,
                color=discord.Color.orange()
            )
        else:
            embed = discord.Embed(
                title='スパムキーワード一覧',
                description='登録されているキーワードはありません',
                color=discord.Color.orange()
            )
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(SpamBlockerCog(bot))