"""
AI服务错误消息处理
"""

def get_user_friendly_error_message(error: str) -> str:
    """
    将技术错误消息转换为用户友好的提示
    
    Args:
        error: 原始错误消息
    
    Returns:
        用户友好的错误消息
    """
    if not error:
        return "发生未知错误，请稍后再试。"
    error_lower = error.lower()
    
    # API限制错误
    if "rate limit exceeded" in error_lower or "429" in error:
        return "AI服务今日使用次数已达上限，请稍后再试或联系管理员。"
    
    # 账户余额不足
    if "insufficient credits" in error_lower or "402" in error:
        return "AI服务账户余额不足，请检查账户余额后重试。"
    
    # 网络连接错误
    if "connection" in error_lower or "timeout" in error_lower:
        return "网络连接异常，请检查网络连接后重试。"
    
    # 模型不可用
    if "no endpoints found" in error_lower or "404" in error:
        return "AI模型暂时不可用，请稍后再试。"
    
    # 默认错误消息
    return f"AI服务暂时不可用：{error}。请稍后再试或联系管理员。"
