import discord
from discord.ext import commands
import openai
import yaml
from ARONA.message.error.errors import LLMError, ConfigError


class LLMCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = self._load_config()

        # OpenAI互換APIの設定
        api_key = self.config.get('openai_api_key')
        base_url = self.config.get('openai_base_url')  # 互換API用のベースURL

        if base_url:
            # カスタムベースURLを使用（OpenAI互換API）
            self.client = openai.AsyncOpenAI(
                api_key=api_key,
                base_url=base_url
            )
            print(f'🔗 カスタムAPI: {base_url}')
        else:
            # 通常のOpenAI API
            self.client = openai.AsyncOpenAI(api_key=api_key)
            print(f'🔗 OpenAI API を使用')

        self.system_prompt = self.config.get('system_prompt', '')
        self.model = self.config.get('model', 'gpt-4-turbo-preview')
        self.max_tokens = self.config.get('max_tokens', 500)
        self.temperature = self.config.get('temperature', 0.8)

    def _load_config(self):
        """config.yamlから設定を読み込む"""
        try:
            with open('config.yaml', 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                if not config.get('openai_api_key'):
                    raise ConfigError('openai_api_key が config.yaml に設定されていません')
                return config
        except FileNotFoundError:
            raise ConfigError('config.yaml が見つかりません')
        except yaml.YAMLError as e:
            raise ConfigError(f'config.yaml の読み込みに失敗しました: {e}')

    @commands.Cog.listener()
    async def on_ready(self):
        """Cog起動時のメッセージ"""
        print(f'🤖 {self.__class__.__name__} が読み込まれました')
        print(f'📝 モデル: {self.model}')
        print(f'💬 システムプロンプト: {len(self.system_prompt)} 文字')
        print(f'👋 ようこそメッセージ: 有効')

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """新しいメンバーが参加したときの処理"""
        # Botは無視
        if member.bot:
            return

        # システムメッセージチャンネルを取得
        system_channel = member.guild.system_channel
        if not system_channel:
            # システムチャンネルがない場合は最初のテキストチャンネルを使用
            system_channel = next(
                (ch for ch in member.guild.text_channels if ch.permissions_for(member.guild.me).send_messages),
                None
            )

        if not system_channel:
            print(f'⚠️ {member.guild.name} にメッセージを送信できるチャンネルがありません')
            return

        try:
            # ようこそメッセージを生成
            welcome_message = await self._generate_welcome_message(member)

            # 新規メンバーをメンションして送信
            await system_channel.send(
                f'{member.mention} さん、ようこそ！🎉\n\n{welcome_message}',
                allowed_mentions=discord.AllowedMentions(users=[member])
            )

            print(f'✅ {member.display_name} へのようこそメッセージを送信しました')

        except LLMError as e:
            print(f'❌ ようこそメッセージの生成エラー: {e}')
            # エラー時はシンプルなメッセージを送信
            await system_channel.send(
                f'{member.mention} さん、ようこそ {member.guild.name} へ！👋',
                allowed_mentions=discord.AllowedMentions(users=[member])
            )
        except Exception as e:
            print(f'❌ 予期しないエラー: {e}')

    async def _generate_welcome_message(self, member: discord.Member) -> str:
        """OpenAI互換APIを使ってようこそメッセージを生成"""
        try:
            # サーバー情報をコンテキストに追加
            guild_context = f"""
サーバー名: {member.guild.name}
メンバー数: {member.guild.member_count}
新規参加者: {member.display_name}
"""

            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": guild_context}
            ]

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )

            return response.choices[0].message.content.strip()

        except openai.APIError as e:
            raise LLMError(f'API エラー: {str(e)}')
        except Exception as e:
            raise LLMError(f'メッセージ生成エラー: {str(e)}')


async def setup(bot):
    await bot.add_cog(LLMCog(bot))