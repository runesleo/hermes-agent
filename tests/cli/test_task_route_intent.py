from hermes_cli.task_route_intent import maybe_build_task_route_command


def test_rewrites_explicit_claude_delegation():
    assert maybe_build_task_route_command("交给 Claude 帮我做今天工作收尾") == "/claude-task 帮我做今天工作收尾"


def test_rewrites_explicit_codex_delegation():
    assert maybe_build_task_route_command("让 Codex 处理 修这个 repo 的 bug") == "/codex-task 修这个 repo 的 bug"


def test_rewrites_explicit_route_request():
    assert maybe_build_task_route_command("帮我路由一下 修这个 repo 的 bug") == "/route-task 修这个 repo 的 bug"


def test_does_not_auto_route_plain_bugfix_request():
    assert maybe_build_task_route_command("修这个 repo 的 bug 并跑测试") is None


def test_does_not_auto_route_plain_closeout_request():
    assert maybe_build_task_route_command("帮我做今天工作收尾并更新 today 和 active-tasks") is None


def test_auto_routes_closeout_question_like_request():
    assert maybe_build_task_route_command("这个对话有值得收尾的吗") == "/claude-task 请判断这个对话是否值得收尾；如果值得，直接完成收尾并更新 today 和 active-tasks"


def test_does_not_auto_route_plain_infra_check_request():
    assert maybe_build_task_route_command("看看 trader-vps 状态和 quota") is None


def test_does_not_trigger_on_general_discussion():
    assert maybe_build_task_route_command("Hermes 将来能不能取代 Claude 和 Codex 作为入口？") is None


def test_does_not_trigger_on_high_risk_execution_request():
    assert maybe_build_task_route_command("帮我改线上生产策略并直接下单") is None


def test_does_not_auto_route_plain_bugfix_fragment():
    assert maybe_build_task_route_command("metar observer 修复") is None


def test_does_not_auto_route_plain_runtime_check_fragment():
    assert maybe_build_task_route_command("看看 gateway 状态") is None


def test_does_not_auto_route_plain_closeout_fragment():
    assert maybe_build_task_route_command("工作收尾") is None
