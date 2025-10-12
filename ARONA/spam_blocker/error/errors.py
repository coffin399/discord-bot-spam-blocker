import discord
from discord.ext import commands
import traceback


async def on_command_error(ctx, error):
    """コマンドエラーのハンドリング"""

    # コマンドが見つからない場合は無視
    if isinstance(error, commands.CommandNotFound):
        return

    # 権限不足エラー
    if isinstance(error, commands.MissingPermissions):
        await ctx.send('❌ このコマンドを実行する権限がありません（管理者権限が必要です）')
        return

    # 引数不足エラー
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f'❌ 引数が不足しています: `{error.param.name}`')
        return

    # 引数の型エラー
    if isinstance(error, commands.BadArgument):
        await ctx.send(f'❌ 引数の形式が正しくありません')
        return

    # クールダウンエラー
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f'⏳ このコマンドは {error.retry_after:.1f}秒後に使用できます')
        return

    # BOTに必要な権限がない
    if isinstance(error, commands.BotMissingPermissions):
        perms = ', '.join(error.missing_permissions)
        await ctx.send(f'❌ BOTに必要な権限がありません: {perms}')
        return

    # その他のエラー
    print(f'❌ エラーが発生しました: {type(error).__name__}')
    print(f'詳細: {error}')
    traceback.print_exception(type(error), error, error.__traceback__)

    # ユーザーにエラーメッセージを送信
    embed = discord.Embed(
        title='❌ エラーが発生しました',
        description=f'```{str(error)[:1000]}```',
        color=discord.Color.red()
    )
    await ctx.send(embed=embed)


async def on_error(event, *args, **kwargs):
    """イベントエラーのハンドリング"""
    print(f'❌ イベント {event} でエラーが発生しました')
    traceback.print_exc()


def setup_error_handler(bot):
    """エラーハンドラーをbotに登録"""
    bot.on_command_error = on_command_error
    bot.on_error = on_error
    print('✅ エラーハンドラーを登録しました')