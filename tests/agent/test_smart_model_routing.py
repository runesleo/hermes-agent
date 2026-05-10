from agent.smart_model_routing import choose_cheap_model_route


_BASE_CONFIG = {
    "enabled": True,
    "cheap_model": {
        "provider": "openrouter",
        "model": "google/gemini-2.5-flash",
    },
}


def test_returns_none_when_disabled():
    cfg = {**_BASE_CONFIG, "enabled": False}
    assert choose_cheap_model_route("what time is it in tokyo?", cfg) is None


def test_routes_short_simple_prompt():
    result = choose_cheap_model_route("what time is it in tokyo?", _BASE_CONFIG)
    assert result is not None
    assert result["provider"] == "openrouter"
    assert result["model"] == "google/gemini-2.5-flash"
    assert result["routing_reason"] == "simple_turn"


def test_skips_long_prompt():
    prompt = "please summarize this carefully " * 20
    assert choose_cheap_model_route(prompt, _BASE_CONFIG) is None


def test_skips_code_like_prompt():
    prompt = "debug this traceback: ```python\nraise ValueError('bad')\n```"
    assert choose_cheap_model_route(prompt, _BASE_CONFIG) is None


def test_skips_tool_heavy_prompt_keywords():
    prompt = "implement a patch for this docker error"
    assert choose_cheap_model_route(prompt, _BASE_CONFIG) is None


def test_resolve_turn_route_falls_back_to_primary_when_route_runtime_cannot_be_resolved(monkeypatch):
    from agent.smart_model_routing import resolve_turn_route

    monkeypatch.setattr(
        "hermes_cli.runtime_provider.resolve_runtime_provider",
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError("bad route")),
    )
    result = resolve_turn_route(
        "what time is it in tokyo?",
        _BASE_CONFIG,
        {
            "model": "anthropic/claude-sonnet-4",
            "provider": "openrouter",
            "base_url": "https://openrouter.ai/api/v1",
            "api_mode": "chat_completions",
            "api_key": "sk-primary",
        },
    )
    assert result["model"] == "anthropic/claude-sonnet-4"
    assert result["runtime"]["provider"] == "openrouter"
    assert result["label"] is None


def test_routes_premium_prompt_when_configured():
    cfg = {
        **_BASE_CONFIG,
        "premium_model": {"provider": "custom", "model": "claude-opus-4-7"},
    }
    result = choose_cheap_model_route("Polymarket 策略真钱撤单前先收敛方案", cfg)
    assert result is not None
    assert result["provider"] == "custom"
    assert result["model"] == "claude-opus-4-7"
    assert result["routing_reason"] == "premium_turn"


def test_routes_mid_prompt_when_configured():
    cfg = {
        **_BASE_CONFIG,
        "mid_model": {"provider": "custom", "model": "claude-4.5-sonnet"},
    }
    result = choose_cheap_model_route("帮我做个产品规划和取舍判断", cfg)
    assert result is not None
    assert result["provider"] == "custom"
    assert result["model"] == "claude-4.5-sonnet"
    assert result["routing_reason"] == "mid_turn"


def test_code_prompt_does_not_route_to_mid_model_without_code_model():
    cfg = {
        **_BASE_CONFIG,
        "mid_model": {"provider": "custom", "model": "claude-4.5-sonnet"},
    }
    assert choose_cheap_model_route("写一个复杂实现计划并改代码", cfg) is None


def test_code_prompt_routes_to_code_model_when_configured():
    cfg = {
        **_BASE_CONFIG,
        "mid_model": {"provider": "custom", "model": "claude-4.5-sonnet"},
        "code_model": {"provider": "openai-codex", "model": "gpt-5.5"},
    }
    result = choose_cheap_model_route("写一个复杂实现计划并改代码", cfg)
    assert result is not None
    assert result["provider"] == "openai-codex"
    assert result["model"] == "gpt-5.5"
    assert result["routing_reason"] == "code_turn"


def test_strategy_and_data_prompts_route_to_code_model_when_configured():
    cfg = {
        **_BASE_CONFIG,
        "code_model": {"provider": "custom", "model": "gpt-5.5-medium"},
    }
    result = choose_cheap_model_route("评估这个策略的数据 pipeline 和回测 PnL", cfg)
    assert result is not None
    assert result["provider"] == "custom"
    assert result["model"] == "gpt-5.5-medium"
    assert result["routing_reason"] == "code_turn"


def test_money_execution_prompt_stays_primary_without_premium_model():
    cfg = {
        **_BASE_CONFIG,
        "code_model": {"provider": "custom", "model": "gpt-5.5-medium"},
    }
    assert choose_cheap_model_route("真钱策略下单前帮我判断一下", cfg) is None


def test_content_prompt_stays_primary_without_premium_model():
    cfg = {
        **_BASE_CONFIG,
        "code_model": {"provider": "custom", "model": "gpt-5.5-medium"},
    }
    assert choose_cheap_model_route("写一条推文", cfg) is None


def test_irreversible_strategy_prompt_stays_primary_without_premium_model():
    cfg = {
        **_BASE_CONFIG,
        "code_model": {"provider": "custom", "model": "gpt-5.5-medium"},
    }
    assert choose_cheap_model_route("这个策略要不要上线，帮我做最终判断", cfg) is None


def test_uncertain_or_escalation_prompt_stays_primary_without_premium_model():
    cfg = {
        **_BASE_CONFIG,
        "code_model": {"provider": "custom", "model": "gpt-5.5-medium"},
    }
    assert choose_cheap_model_route("medium 说不确定，升级给 Opus 复核", cfg) is None
