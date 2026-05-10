"""Helpers for optional cheap-vs-strong model routing."""

from __future__ import annotations

import os
import re
from typing import Any, Dict, Optional

from utils import is_truthy_value

_COMPLEX_KEYWORDS = {
    "debug",
    "debugging",
    "implement",
    "implementation",
    "refactor",
    "patch",
    "traceback",
    "stacktrace",
    "exception",
    "error",
    "analyze",
    "analysis",
    "investigate",
    "architecture",
    "design",
    "compare",
    "benchmark",
    "optimize",
    "optimise",
    "review",
    "terminal",
    "shell",
    "tool",
    "tools",
    "pytest",
    "test",
    "tests",
    "plan",
    "planning",
    "delegate",
    "subagent",
    "cron",
    "docker",
    "kubernetes",
    "strategy",
    "backtest",
    "pnl",
}

_COMPLEX_SUBSTRINGS = {
    "复杂",
    "实现",
    "改代码",
    "修复",
    "调试",
    "排查",
    "分析",
    "架构",
    "设计",
    "测试",
    "验证",
    "repo",
    "代码",
    "策略",
    "数据",
    "回测",
    "pnl",
    "PnL",
    "schema",
    "pipeline",
    "fair value",
    "toxicity",
    "做市",
}

# These should not run on the cheapest/simple route.  If a premium_model is
# configured, route them up; otherwise keep the primary runtime.
_PREMIUM_SUBSTRINGS = {
    "opus",
    "高价值",
    "长上下文",
    "复杂综合",
    "内容",
    "文章",
    "推文",
    "quote",
    "小红书",
    "品牌",
    "人设",
    "商业化",
    "产品策略",
    "最终判断",
    "最终决策",
    "拍板",
    "不可逆",
    "irreversible",
    "go/no-go",
    "上线",
    "下线",
    "换参数",
    "调仓",
    "仓位",
    "position",
    "真实资金",
    "真实交易",
    "执行交易",
    "真钱",
    "实盘",
    "生产",
    "部署",
    "账号",
    "钱包",
    "撤单",
    "下单",
    "资金",
    "转账",
    "密钥",
    "credential",
    "secret",
    "api key",
    "private key",
    "不确定",
    "置信度低",
    "uncertain",
    "escalate",
    "升级给 opus",
    "polymarket",
    "trader-vps",
}

# Medium-strength work benefits from Sonnet when available, but should not
# force Opus. If mid_model is absent, it stays on primary.
_MID_SUBSTRINGS = {
    "计划",
    "规划",
    "判断",
    "取舍",
    "权衡",
    "复盘",
    "写文章",
    "改稿",
    "总结一下",
    "拆解",
    "产品",
    "roadmap",
}

_URL_RE = re.compile(r"https?://|www\.", re.IGNORECASE)


def _protected_keywords(cfg: Dict[str, Any]) -> set[str]:
    """Return lowercase protected keywords that should stay on the primary model."""
    raw = cfg.get("protected_keywords") or []
    if isinstance(raw, str):
        raw = [raw]
    if not isinstance(raw, (list, tuple, set)):
        return set()
    result = set()
    for item in raw:
        token = str(item or "").strip().lower()
        if token:
            result.add(token)
    return result


def _coerce_bool(value: Any, default: bool = False) -> bool:
    return is_truthy_value(value, default=default)


def _coerce_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _configured_model(cfg: Dict[str, Any], key: str, reason: str) -> Optional[Dict[str, Any]]:
    raw = cfg.get(key) or {}
    if not isinstance(raw, dict):
        return None
    provider = str(raw.get("provider") or "").strip().lower()
    model = str(raw.get("model") or "").strip()
    if not provider or not model:
        return None
    route = dict(raw)
    route["provider"] = provider
    route["model"] = model
    route["routing_reason"] = reason
    return route


def _is_simple_turn(text: str, cfg: Dict[str, Any]) -> bool:
    max_chars = _coerce_int(cfg.get("max_simple_chars"), 160)
    max_words = _coerce_int(cfg.get("max_simple_words"), 28)

    if len(text) > max_chars:
        return False
    if len(text.split()) > max_words:
        return False
    if text.count("\n") > 1:
        return False
    if "```" in text or "`" in text:
        return False
    if _URL_RE.search(text):
        return False

    lowered = text.lower()
    protected = _protected_keywords(cfg)
    if any(keyword and keyword in lowered for keyword in protected):
        return False
    if any(keyword in lowered for keyword in _COMPLEX_SUBSTRINGS):
        return False
    if any(keyword in lowered for keyword in _MID_SUBSTRINGS):
        return False
    if any(keyword in lowered for keyword in _PREMIUM_SUBSTRINGS):
        return False
    words = {token.strip(".,:;!?()[]{}\"'`") for token in lowered.split()}
    if words & _COMPLEX_KEYWORDS:
        return False
    if words & protected:
        return False
    return True


def choose_cheap_model_route(user_message: str, routing_config: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Return an optional non-primary model route for this turn.

    Backward-compatible name: historically this only returned cheap_model for
    simple turns. It now supports conservative tiers:
      - premium_model for money/production/strategy/explicit Opus work
      - mid_model for planning/content/judgment when configured
      - cheap_model for trivial turns

    If a tier is not configured, the caller stays on the primary model.
    """
    cfg = routing_config or {}
    if not _coerce_bool(cfg.get("enabled"), False):
        return None

    text = (user_message or "").strip()
    if not text:
        return None

    lowered = text.lower()
    protected = _protected_keywords(cfg)

    if any(keyword in lowered for keyword in _PREMIUM_SUBSTRINGS):
        route = _configured_model(cfg, "premium_model", "premium_turn")
        if route:
            return route
        return None

    # Explicit protected keywords keep their old semantics unless the config
    # opts into protected_keyword_model. This prevents accidental escalation of
    # workflow commands to Opus when Leo wants them handled by the primary.
    if any(keyword and keyword in lowered for keyword in protected):
        route = _configured_model(cfg, "protected_keyword_model", "protected_keyword_turn")
        if route:
            return route
        return None

    # Code/debug/tool-heavy work should use code_model when configured. This
    # keeps Hermes' primary model high-quality (Opus) while routing serious
    # implementation/debug/test work to Codex.
    words = {token.strip(".,:;!?()[]{}\"'`") for token in lowered.split()}
    if any(keyword in lowered for keyword in _COMPLEX_SUBSTRINGS) or words & _COMPLEX_KEYWORDS:
        route = _configured_model(cfg, "code_model", "code_turn")
        if route:
            return route
        return None

    if any(keyword in lowered for keyword in _MID_SUBSTRINGS):
        route = _configured_model(cfg, "mid_model", "mid_turn")
        if route:
            return route

    if _is_simple_turn(text, cfg):
        return _configured_model(cfg, "cheap_model", "simple_turn")

    return None


def resolve_turn_route(user_message: str, routing_config: Optional[Dict[str, Any]], primary: Dict[str, Any]) -> Dict[str, Any]:
    """Resolve the effective model/runtime for one turn.

    Returns a dict with model/runtime/signature/label fields.
    """
    route = choose_cheap_model_route(user_message, routing_config)
    if not route:
        return {
            "model": primary.get("model"),
            "runtime": {
                "api_key": primary.get("api_key"),
                "base_url": primary.get("base_url"),
                "provider": primary.get("provider"),
                "api_mode": primary.get("api_mode"),
                "command": primary.get("command"),
                "args": list(primary.get("args") or []),
                "credential_pool": primary.get("credential_pool"),
            },
            "label": None,
            "signature": (
                primary.get("model"),
                primary.get("provider"),
                primary.get("base_url"),
                primary.get("api_mode"),
                primary.get("command"),
                tuple(primary.get("args") or ()),
            ),
        }

    from hermes_cli.runtime_provider import resolve_runtime_provider

    explicit_api_key = None
    api_key_env = str(route.get("api_key_env") or "").strip()
    if api_key_env:
        explicit_api_key = os.getenv(api_key_env) or None

    try:
        runtime = resolve_runtime_provider(
            requested=route.get("provider"),
            explicit_api_key=explicit_api_key,
            explicit_base_url=route.get("base_url"),
        )
    except Exception:
        return {
            "model": primary.get("model"),
            "runtime": {
                "api_key": primary.get("api_key"),
                "base_url": primary.get("base_url"),
                "provider": primary.get("provider"),
                "api_mode": primary.get("api_mode"),
                "command": primary.get("command"),
                "args": list(primary.get("args") or []),
                "credential_pool": primary.get("credential_pool"),
            },
            "label": None,
            "signature": (
                primary.get("model"),
                primary.get("provider"),
                primary.get("base_url"),
                primary.get("api_mode"),
                primary.get("command"),
                tuple(primary.get("args") or ()),
            ),
        }

    return {
        "model": route.get("model"),
        "runtime": {
            "api_key": runtime.get("api_key"),
            "base_url": runtime.get("base_url"),
            "provider": runtime.get("provider"),
            "api_mode": runtime.get("api_mode"),
            "command": runtime.get("command"),
            "args": list(runtime.get("args") or []),
            "credential_pool": runtime.get("credential_pool"),
        },
        "label": f"smart route → {route.get('model')} ({runtime.get('provider')})",
        "signature": (
            route.get("model"),
            runtime.get("provider"),
            runtime.get("base_url"),
            runtime.get("api_mode"),
            runtime.get("command"),
            tuple(runtime.get("args") or ()),
        ),
    }
