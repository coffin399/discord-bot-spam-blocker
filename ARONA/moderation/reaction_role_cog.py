import json
import os
from pathlib import Path
from typing import Dict, Optional

import discord
from discord.ext import commands
import yaml

DATA_DIR = Path(__file__).parent.parent.parent / 'data'
DATA_FILE = DATA_DIR / 'reaction_roles.json'
DATA_DIR.mkdir(exist_ok=True)


def load_config():
    with open('config.yaml', 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def load_reaction_roles() -> Dict[str, Dict[str, int]]:
    if not DATA_FILE.exists():
        return {}
    try:
        with DATA_FILE.open('r', encoding='utf-8') as f:
            raw = json.load(f)
            return {k: v for k, v in raw.items() if isinstance(v, dict)}
    except (json.JSONDecodeError, OSError):
        return {}


def save_reaction_roles(data: Dict[str, Dict[str, int]]) -> None:
    try:
        with DATA_FILE.open('w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except OSError as exc:
        print(f'リアクションロールの保存に失敗しました: {exc}')


class ReactionRoleCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.config = load_config()
        self.monitored_guild_ids = self._to_int_set(self.config.get('monitored_guilds', []))
        self.mappings = load_reaction_roles()

    def _to_int_set(self, values) -> set[int]:
        result = set()
        if not values:
            return result
        for value in values:
            try:
                result.add(int(value))
            except (TypeError, ValueError):
                continue
        return result

    def _is_enabled_for_guild(self, guild: discord.Guild) -> bool:
        if not self.monitored_guild_ids:
            return True
        return guild.id in self.monitored_guild_ids

    @commands.command(name='reactionrole')
    @commands.has_permissions(manage_roles=True)
    async def reaction_role(
        self,
        ctx: commands.Context,
        message_id: int,
        emoji: str,
        role_id: int,
    ):
        """指定メッセージに絵文字を追加し、リアクションでロールを付与します"""
        if not self._is_enabled_for_guild(ctx.guild):
            await ctx.send('⚠️ このサーバーではリアクションロールは無効です')
            return

        try:
            target_message = await ctx.channel.fetch_message(message_id)
        except discord.NotFound:
            await ctx.send('❌ 指定されたメッセージが見つかりません')
            return
        except discord.Forbidden:
            await ctx.send('❌ メッセージの取得権限がありません')
            return

        role = ctx.guild.get_role(role_id)
        if role is None:
            await ctx.send('❌ 指定されたロールが見つかりません')
            return

        try:
            await target_message.add_reaction(emoji)
        except discord.Forbidden:
            await ctx.send('❌ 絵文字を追加する権限がありません')
            return
        except discord.HTTPException as exc:
            await ctx.send(f'❌ 絵文字の追加に失敗しました: {exc}')
            return

        key = f'{ctx.guild.id}-{target_message.id}'
        self.mappings.setdefault(key, {})[emoji] = role_id
        save_reaction_roles(self.mappings)

        await ctx.send(
            f'✅ リアクションロールを設定しました\n'
            f'メッセージ: {message_id}\n'
            f'絵文字: {emoji}\n'
            f'ロール: {role.mention}'
        )

    @commands.command(name='rmlist')
    @commands.has_permissions(manage_roles=True)
    async def rm_reaction_role_list(self, ctx: commands.Context):
        """現在のリアクションロール設定を一覧表示します"""
        guild_mappings = {
            k: v for k, v in self.mappings.items()
            if k.startswith(f'{ctx.guild.id}-')
        }
        if not guild_mappings:
            await ctx.send('📋 リアクションロールは設定されていません')
            return

        lines = ['📋 リアクションロール一覧:']
        for key, emoji_to_role in guild_mappings.items():
            _, msg_id = key.split('-', 1)
            lines.append(f'メッセージID {msg_id}:')
            for emoji_str, rid in emoji_to_role.items():
                role = ctx.guild.get_role(rid)
                role_text = role.mention if role else f'不明なロール({rid})'
                lines.append(f'  {emoji_str} → {role_text}')
        await ctx.send('\n'.join(lines))

    @commands.command(name='rmreactionrole')
    @commands.has_permissions(manage_roles=True)
    async def rm_reaction_role(
        self,
        ctx: commands.Context,
        message_id: int,
        emoji: str,
    ):
        """指定メッセージの絵文字リアクションロールを削除します"""
        key = f'{ctx.guild.id}-{message_id}'
        if key not in self.mappings or emoji not in self.mappings[key]:
            await ctx.send('❌ 指定された設定が見つかりません')
            return

        del self.mappings[key][emoji]
        if not self.mappings[key]:
            del self.mappings[key]
        save_reaction_roles(self.mappings)

        try:
            target_message = await ctx.channel.fetch_message(message_id)
            await target_message.clear_reaction(emoji)
        except discord.HTTPException:
            pass  # リアクション削除失敗は無視

        await ctx.send('✅ リアクションロールを削除しました')

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if payload.guild_id is None:
            return
        if not self._is_enabled_for_guild(discord.Object(id=payload.guild_id)):
            return
        if payload.user_id == self.bot.user.id:
            return

        key = f'{payload.guild_id}-{payload.message_id}'
        mapping = self.mappings.get(key, {})
        role_id = mapping.get(str(payload.emoji))
        if role_id is None:
            return

        guild = self.bot.get_guild(payload.guild_id)
        if guild is None:
            return
        member = guild.get_member(payload.user_id)
        if member is None:
            try:
                member = await guild.fetch_member(payload.user_id)
            except discord.NotFound:
                return

        role = guild.get_role(role_id)
        if role is None:
            return
        if member.guild_permissions.administrator:
            return

        try:
            await member.add_roles(role, reason='リアクションロール')
        except discord.Forbidden:
            return

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        if payload.guild_id is None:
            return
        if not self._is_enabled_for_guild(discord.Object(id=payload.guild_id)):
            return
        if payload.user_id == self.bot.user.id:
            return

        key = f'{payload.guild_id}-{payload.message_id}'
        mapping = self.mappings.get(key, {})
        role_id = mapping.get(str(payload.emoji))
        if role_id is None:
            return

        guild = self.bot.get_guild(payload.guild_id)
        if guild is None:
            return
        member = guild.get_member(payload.user_id)
        if member is None:
            try:
                member = await guild.fetch_member(payload.user_id)
            except discord.NotFound:
                return

        role = guild.get_role(role_id)
        if role is None:
            return
        if member.guild_permissions.administrator:
            return

        try:
            await member.remove_roles(role, reason='リアクションロール解除')
        except discord.Forbidden:
            return


async def setup(bot: commands.Bot):
    await bot.add_cog(ReactionRoleCog(bot))
