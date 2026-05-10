from agent.copilot_acp_client import CopilotACPClient


def test_build_launch_command_injects_model_before_acp_args():
    client = CopilotACPClient(
        acp_command="copilot",
        acp_args=["--acp", "--stdio"],
    )

    cmd = client._build_launch_command("claude-sonnet-4.6")

    assert cmd == [
        "copilot",
        "--model",
        "claude-sonnet-4.6",
        "--acp",
        "--stdio",
    ]


def test_build_launch_command_respects_explicit_model_flag():
    client = CopilotACPClient(
        acp_command="copilot",
        acp_args=["--model", "gpt-4.1", "--acp", "--stdio"],
    )

    cmd = client._build_launch_command("claude-sonnet-4.6")

    assert cmd == [
        "copilot",
        "--model",
        "gpt-4.1",
        "--acp",
        "--stdio",
    ]
