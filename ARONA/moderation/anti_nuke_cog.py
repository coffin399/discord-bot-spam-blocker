import asyncio
import logging
from collections import defaultdict, deque
from typing import Optional

import discord
from discord.ext import commands
import yaml

logger = logging.getLogger(__name__)


def load_config():
    with open('config.yaml', 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


class AntiNukeCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.recent_actions = defaultdict(
            lambda: defaultdict(lambda: defaultdict(deque))
        )
        self.config = {}
        self.settings = {}
        self.enabled = False
        self.punishment = 'strip_roles'
        self.log_channel_id: Optional[int] = None
        self.quarantine_role_id: Optional[int] = None
        self.exempt_user_ids: set[int] = set()
        self.exempt_role_ids: set[int] = set()
        self.action_thresholds = {}
        self.monitored_guild_ids: set[int] = set()
        self.refresh_settings()

    # ------------------------------------------------------------------
    # Configuration helpers
    # ------------------------------------------------------------------
    def refresh_settings(self):
        try:
            self.config = load_config() or {}
        except FileNotFoundError:
            logger.error('config.yaml が見つからないため、Anti-nuke を無効化します')
            self.enabled = False
            return

        self.settings = self.config.get('anti_nuke') or {}
        self.enabled = bool(self.settings.get('enabled', False))
        punishment = str(self.settings.get('punishment', 'strip_roles')).lower()
        self.punishment = punishment if punishment in {'strip_roles', 'kick', 'ban'} else 'strip_roles'
        self.log_channel_id = self._to_int(self.settings.get('log_channel_id'))
        self.quarantine_role_id = self._to_int(self.settings.get('quarantine_role_id'))
        self.exempt_user_ids = self._to_int_set(self.settings.get('exempt_user_ids', []))
        self.exempt_role_ids = self._to_int_set(self.settings.get('exempt_role_ids', []))
        self.action_thresholds = self.settings.get('action_thresholds', {})
        self.monitored_guild_ids = self._to_int_set(self.config.get('monitored_guilds', []))
        self.recent_actions.clear()

        logger.info(
            'Anti-nuke 設定を読み込みました: enabled=%s punishment=%s log_channel_id=%s',
            self.enabled,
            self.punishment,
            self.log_channel_id,
        )

    @staticmethod
    def _to_int(value) -> Optional[int]:
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _to_int_set(self, values) -> set[int]:
        result = set()
        if not values:
            return result
        for value in values:
            parsed = self._to_int(value)
            if parsed is not None:
                result.add(parsed)
        return result

    def _is_enabled_for_guild(self, guild: discord.Guild) -> bool:
        if not self.enabled:
            return False
        if not self.monitored_guild_ids:
            return True
        return guild.id in self.monitored_guild_ids

    def _threshold_for_action(self, action_key: str) -> tuple[int, int]:
        config = self.action_thresholds.get(action_key) or {}
        try:
            count = int(config.get('count', 0))
        except (TypeError, ValueError):
            count = 0
        try:
            window = int(config.get('window_seconds', 0))
        except (TypeError, ValueError):
            window = 0
        return max(count, 0), max(window, 1)

    # ------------------------------------------------------------------
    # Event listeners
    # ------------------------------------------------------------------
    @commands.Cog.listener()
    async def on_ready(self):
        if self.enabled:
            logger.info('Anti-nuke が有効になりました (punishment=%s)', self.punishment)
        else:
            logger.info('Anti-nuke は無効化されています')

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        await self._handle_audit_action(
            guild=channel.guild,
            action_key='channel_delete',
            audit_action=discord.AuditLogAction.channel_delete,
            target_id=channel.id,
            note=f'チャンネル削除: #{channel.name}',
        )

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel):
        await self._handle_audit_action(
            guild=channel.guild,
            action_key='channel_create',
            audit_action=discord.AuditLogAction.channel_create,
            target_id=channel.id,
            note=f'チャンネル作成: #{channel.name}',
        )

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role):
        await self._handle_audit_action(
            guild=role.guild,
            action_key='role_delete',
            audit_action=discord.AuditLogAction.role_delete,
            target_id=role.id,
            note=f'ロール削除: {role.name}',
        )

    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: discord.User):
        await self._handle_audit_action(
            guild=guild,
            action_key='member_ban',
            audit_action=discord.AuditLogAction.ban,
            target_id=user.id,
            note=f'ユーザーBAN: {user} ({user.id})',
        )

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        await self._handle_audit_action(
            guild=member.guild,
            action_key='member_kick',
            audit_action=discord.AuditLogAction.kick,
            target_id=member.id,
            note=f'ユーザーKICK: {member} ({member.id})',
        )

    # ------------------------------------------------------------------
    # Commands
    # ------------------------------------------------------------------
    @commands.command(name='antinuke_reload')
    @commands.has_permissions(administrator=True)
    async def antinuke_reload(self, ctx: commands.Context):
        self.refresh_settings()
        await ctx.send('✅ Anti-nuke 設定を再読み込みしました')

    @commands.command(name='antinuke_status')
    @commands.has_permissions(administrator=True)
    async def antinuke_status(self, ctx: commands.Context):
        enabled_text = '有効' if self.enabled else '無効'
        lines = [
            f'Anti-nuke: **{enabled_text}**',
            f'処罰方法: `{self.punishment}`',
        ]
        for key, (count, window) in self._iter_thresholds():
            lines.append(f'- {key}: {count} 件 / {window} 秒')
        await ctx.send('\n'.join(lines))

    def _iter_thresholds(self):
        for key in sorted(self.action_thresholds.keys()):
            yield key, self._threshold_for_action(key)

    # ------------------------------------------------------------------
    # Core logic
    # ------------------------------------------------------------------
    async def _handle_audit_action(
        self,
        guild: discord.Guild,
        action_key: str,
        audit_action: discord.AuditLogAction,
        target_id: Optional[int],
        note: str,
    ):
        if guild is None or not self._is_enabled_for_guild(guild):
            return

        executor = await self._get_audit_executor(guild, audit_action, target_id)
        if executor is None:
            return

        await self._register_action(guild, executor, action_key, note)

    async def _get_audit_executor(
        self,
        guild: discord.Guild,
        audit_action: discord.AuditLogAction,
        target_id: Optional[int],
    ) -> Optional[discord.abc.User]:
        await asyncio.sleep(1)  # 監査ログが反映されるまで短時間待機
        try:
            async for entry in guild.audit_logs(limit=5, action=audit_action):
                if target_id is not None:
                    entry_target = getattr(entry.target, 'id', None)
                    if entry_target != target_id:
                        continue
                if (discord.utils.utcnow() - entry.created_at).total_seconds() > 120:
                    continue
                if entry.user is None:
                    continue
                return entry.user
        except discord.Forbidden:
            await self._log_action(
                guild,
                '⚠️ 監査ログにアクセスできませんでした。`View Audit Log` 権限を確認してください。',
            )
        except discord.HTTPException as exc:
            logger.warning('監査ログの取得に失敗しました: %s', exc)
        return None

    async def _register_action(
        self,
        guild: discord.Guild,
        executor: discord.abc.User,
        action_key: str,
        note: str,
    ):
        executor_id = executor.id
        if self._should_ignore_executor(guild, executor_id):
            return

        count_limit, window_seconds = self._threshold_for_action(action_key)
        if count_limit <= 0:
            return

        now = discord.utils.utcnow()
        actions = self.recent_actions[guild.id][executor_id][action_key]
        actions.append(now)

        while actions and (now - actions[0]).total_seconds() > window_seconds:
            actions.popleft()

        if len(actions) >= count_limit:
            self.recent_actions[guild.id].pop(executor_id, None)
            await self._log_action(
                guild,
                f'🚨 Anti-nuke 発動: {self._format_executor(executor)} が "{action_key}" を短時間に実行 ({note})',
            )
            await self._punish_user(guild, executor, action_key, note)
        else:
            logger.debug(
                'Anti-nuke トラッキング: guild=%s executor=%s action=%s count=%s/%s',
                guild.id,
                executor_id,
                action_key,
                len(actions),
                count_limit,
            )

    def _format_executor(self, executor: discord.abc.User) -> str:
        if isinstance(executor, discord.Member):
            return f'{executor.mention} ({executor.id})'
        return f'{executor} ({executor.id})'

    def _should_ignore_executor(self, guild: discord.Guild, user_id: int) -> bool:
        if user_id == self.bot.user.id or user_id == guild.owner_id:
            return True
        if user_id in self.exempt_user_ids:
            return True

        member = guild.get_member(user_id)
        if member is None:
            return False

        if self.exempt_role_ids and any(role.id in self.exempt_role_ids for role in member.roles):
            return True
        return False

    async def _punish_user(
        self,
        guild: discord.Guild,
        executor: discord.abc.User,
        action_key: str,
        note: str,
    ):
        reason = f'Anti-nuke: {action_key} - {note}'
        member = guild.get_member(executor.id)
        if member is None:
            try:
                member = await guild.fetch_member(executor.id)
            except discord.NotFound:
                member = None
            except discord.HTTPException as exc:
                logger.warning('メンバー情報の取得に失敗しました: %s', exc)

        try:
            if self.punishment == 'strip_roles':
                await self._strip_roles(guild, member, reason)
            elif self.punishment == 'kick':
                await self._kick_member(guild, member, executor.id, reason)
            elif self.punishment == 'ban':
                await self._ban_member(guild, executor.id, reason)
        except discord.Forbidden:
            await self._log_action(
                guild,
                f'⚠️ Anti-nuke の処罰に失敗しました (権限不足)。対象: {self._format_executor(executor)}',
            )
        except discord.HTTPException as exc:
            await self._log_action(
                guild,
                f'⚠️ Anti-nuke の処罰実行時にエラーが発生: {exc}',
            )

    async def _strip_roles(self, guild: discord.Guild, member: Optional[discord.Member], reason: str):
        if member is None:
            logger.warning('Anti-nuke strip_roles: メンバー情報が取得できませんでした')
            return
        bot_member = guild.me or await guild.fetch_member(self.bot.user.id)
        if not bot_member.guild_permissions.manage_roles:
            raise discord.Forbidden(guild, 'manage_roles が不足しています')

        removable_roles = [
            role for role in member.roles
            if not role.is_default() and bot_member.top_role > role
        ]
        if removable_roles:
            await member.remove_roles(*removable_roles, reason=reason)
        if self.quarantine_role_id:
            quarantine_role = guild.get_role(self.quarantine_role_id)
            if quarantine_role and bot_member.top_role > quarantine_role:
                await member.add_roles(quarantine_role, reason='Anti-nuke quarantine')

    async def _kick_member(
        self,
        guild: discord.Guild,
        member: Optional[discord.Member],
        user_id: int,
        reason: str,
    ):
        if member is not None:
            await guild.kick(member, reason=reason)
        else:
            raise discord.Forbidden(guild, 'kick 対象がギルドに存在しません')

    async def _ban_member(self, guild: discord.Guild, user_id: int, reason: str):
        await guild.ban(discord.Object(id=user_id), reason=reason, delete_message_days=0)

    async def _log_action(self, guild: discord.Guild, message: str):
        logger.info('%s (%s)', message, guild.id)
        if not self.log_channel_id:
            return
        channel = guild.get_channel(self.log_channel_id)
        if channel is None:
            try:
                channel = await guild.fetch_channel(self.log_channel_id)
            except (discord.NotFound, discord.HTTPException, discord.Forbidden):
                logger.warning('ログチャンネル %s にアクセスできません', self.log_channel_id)
                return
        if getattr(channel, 'guild', None) and channel.guild.id != guild.id:
            return
        try:
            await channel.send(message)
        except discord.Forbidden:
            logger.warning('ログチャンネルへの送信権限がありません')


async def setup(bot: commands.Bot):
    await bot.add_cog(AntiNukeCog(bot))
