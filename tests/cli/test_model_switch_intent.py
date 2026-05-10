from hermes_cli.model_switch_intent import maybe_build_model_switch_command


def test_builds_gpt_54_command_from_chinese_switch_phrase():
    assert maybe_build_model_switch_command("帮我切到 5.4") == "/model gpt-5.4"


def test_builds_opus_command_from_short_alias():
    assert maybe_build_model_switch_command("换成 opus") == "/model opus"


def test_builds_global_command_from_default_phrase():
    assert maybe_build_model_switch_command("默认用 sonnet") == "/model sonnet --global"


def test_builds_gpt_41_command_from_english_phrase():
    assert maybe_build_model_switch_command("switch to gpt 4.1") == "/model gpt-4.1"


def test_does_not_trigger_on_model_discussion_question():
    assert maybe_build_model_switch_command("我如果想主动切 5.4 或者 opus 只能通过命令吗") is None
