from gateway.config import Platform
from gateway.platforms.base import MessageEvent, MessageType
from gateway.run import GatewayRunner
from gateway.session import SessionSource


def _make_event(text: str) -> MessageEvent:
    return MessageEvent(
        text=text,
        message_type=MessageType.TEXT,
        source=SessionSource(platform=Platform.TELEGRAM, chat_id="12345", chat_type="dm"),
    )


def test_gateway_rewrites_natural_language_switch():
    runner = object.__new__(GatewayRunner)
    event = _make_event("换成 opus")

    rewritten = runner._apply_natural_language_model_switch(event)

    assert rewritten is True
    assert event.text == "/model opus"


def test_gateway_leaves_regular_message_untouched():
    runner = object.__new__(GatewayRunner)
    event = _make_event("我如果想主动切 5.4 或者 opus 只能通过命令吗")

    rewritten = runner._apply_natural_language_model_switch(event)

    assert rewritten is False
    assert event.text == "我如果想主动切 5.4 或者 opus 只能通过命令吗"

