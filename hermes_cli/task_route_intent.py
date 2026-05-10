"""Natural-language rewrites for explicit task-routing requests.

Keep the scope narrow: only rewrite messages that clearly ask Hermes to hand a
job to Claude/Codex or to route the task. Ordinary conversation must remain a
normal user turn.
"""

from __future__ import annotations

import re
from typing import Optional

_CLAUDE_PREFIXES = (
    re.compile(r"^\s*(?:请|麻烦|帮我|直接|就)?\s*(?:交给|给|让)\s*claude\s*(?:来|去)?(?:做|处理|推进|搞定)?[:：,，\s-]*(?P<body>.+?)\s*$", re.IGNORECASE),
    re.compile(r"^\s*claude\s*(?:来|去)?(?:做|处理|推进|搞定)[:：,，\s-]*(?P<body>.+?)\s*$", re.IGNORECASE),
)

_CODEX_PREFIXES = (
    re.compile(r"^\s*(?:请|麻烦|帮我|直接|就)?\s*(?:交给|给|让)\s*codex\s*(?:来|去)?(?:做|处理|推进|搞定)?[:：,，\s-]*(?P<body>.+?)\s*$", re.IGNORECASE),
    re.compile(r"^\s*codex\s*(?:来|去)?(?:做|处理|推进|搞定)[:：,，\s-]*(?P<body>.+?)\s*$", re.IGNORECASE),
)

_ROUTE_PATTERNS = (
    re.compile(r"^\s*(?:请|麻烦|帮我)?\s*(?:路由|分配|判断|看看).*(?:给谁做|谁来做|该谁做|该\s*hermes\s*还是\s*codex).*$", re.IGNORECASE),
    re.compile(r"^\s*这个任务给谁做[:：,，\s-]*(?P<body>.+?)\s*$", re.IGNORECASE),
    re.compile(r"^\s*(?:帮我)?路由一下[:：,，\s-]*(?P<body>.+?)\s*$", re.IGNORECASE),
    re.compile(r"^\s*让\s*hermes\s*分配任务[:：,，\s-]*(?P<body>.+?)\s*$", re.IGNORECASE),
)

_AUTO_CLAUDE_PATTERNS = (
    re.compile(r"收尾|closeout|session[- ]?end|更新\s*today|更新\s*active[- ]?tasks|quick[- ]?sync|同步到|沉淀", re.IGNORECASE),
    re.compile(r"内容|文案|风格|推文|长文|文章|总结框架|高层分析|方向判断", re.IGNORECASE),
)

_AUTO_CODEX_PATTERNS = (
    re.compile(r"bug|报错|错误|异常|修复|debug|调试|traceback|test|pytest|lint|build|compile", re.IGNORECASE),
    re.compile(r"repo|代码|实现|重构|refactor|diff|pr|review|commit|worktree|ci|deploy", re.IGNORECASE),
    re.compile(r"前端|后端|接口|api|数据库|schema|migration", re.IGNORECASE),
)

_AUTO_HERMES_PATTERNS = (
    re.compile(r"状态|health|quota|额度|端口|进程|日志|VPS|磁盘|CPU|内存|检查", re.IGNORECASE),
    re.compile(r"研究|查一下|盘点|triage|audit|cron|tg|telegram|gateway", re.IGNORECASE),
)

_HIGH_RISK_PATTERNS = (
    re.compile(r"真钱|实盘|生产|production|下单|转账|withdraw|充值|改线上|删库|封号|账号", re.IGNORECASE),
)

_CLOSEOUT_QUESTION_PATTERNS = (
    re.compile(r"这个对话.*(收尾|总结|沉淀|closeout)", re.IGNORECASE),
    re.compile(r"(值不值得|有没有必要).*(收尾|总结|沉淀)", re.IGNORECASE),
)

_QUESTION_RE = re.compile(r"[?？]|(吗|么|呢)|\b(how|what|why|whether|can i|could i|能不能|可不可以|是不是)\b", re.IGNORECASE)

_TRAILING_NOISE_RE = re.compile(r"(?:[。！!,.?？]+|(?:一下|吧|谢谢|thanks|thank you|pls|please))+$", re.IGNORECASE)


def _clean_body(text: str) -> str:
    body = (text or "").strip()
    body = body.strip("`\"'“”‘’")
    body = _TRAILING_NOISE_RE.sub("", body).strip()
    return body


def _looks_like_question(text: str) -> bool:
    return bool(_QUESTION_RE.search(text or ""))


def _matches_any(patterns: tuple[re.Pattern[str], ...], text: str) -> bool:
    return any(pattern.search(text) for pattern in patterns)


def _maybe_build_closeout_command(stripped: str) -> Optional[str]:
    text = _clean_body(stripped)
    if not text or not _looks_like_question(text):
        return None
    if not _matches_any(_CLOSEOUT_QUESTION_PATTERNS, text):
        return None
    prompt = "请判断这个对话是否值得收尾；如果值得，直接完成收尾并更新 today 和 active-tasks"
    return f"/claude-task {prompt}"


def _maybe_build_auto_route_command(stripped: str) -> Optional[str]:
    text = _clean_body(stripped)
    if not text or _looks_like_question(text) or _matches_any(_HIGH_RISK_PATTERNS, text):
        return None

    if _matches_any(_AUTO_CODEX_PATTERNS, text):
        return f"/route-task {text}"
    if _matches_any(_AUTO_CLAUDE_PATTERNS, text):
        return f"/route-task {text}"
    if _matches_any(_AUTO_HERMES_PATTERNS, text):
        return f"/route-task {text}"
    return None


def maybe_build_task_route_command(text: str) -> Optional[str]:
    stripped = (text or "").strip()
    if not stripped or stripped.startswith("/") or "\n" in stripped:
        return None

    for pattern in _CLAUDE_PREFIXES:
        match = pattern.match(stripped)
        if match:
            body = _clean_body(match.group("body"))
            return f"/claude-task {body}" if body else None

    for pattern in _CODEX_PREFIXES:
        match = pattern.match(stripped)
        if match:
            body = _clean_body(match.group("body"))
            return f"/codex-task {body}" if body else None

    for pattern in _ROUTE_PATTERNS:
        match = pattern.match(stripped)
        body = _clean_body(match.groupdict().get("body", stripped)) if match else ""
        candidate = body or stripped
        # Guard against turning a bare question with no task content into a useless route command.
        if candidate and candidate != stripped:
            return f"/route-task {candidate}"
        if match and candidate == stripped and len(stripped) > 8:
            return f"/route-task {candidate}"

    closeout_cmd = _maybe_build_closeout_command(stripped)
    if closeout_cmd:
        return closeout_cmd

    # Do not auto-route ordinary short task fragments like "修复" / "看看状态".
    # Keep natural-language rewrites narrow: only explicit delegation / explicit routing.
    return None
