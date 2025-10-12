"""
メッセージ/LLM関連のエラークラス
"""


class MessageError(Exception):
    """メッセージ関連の基底エラークラス"""
    pass


class LLMError(MessageError):
    """LLM（Claude API）関連のエラー"""
    pass


class ConfigError(MessageError):
    """設定ファイル関連のエラー"""
    pass


class RateLimitError(LLMError):
    """レート制限エラー"""
    pass


class TokenLimitError(LLMError):
    """トークン制限エラー"""
    pass