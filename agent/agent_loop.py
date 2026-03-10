"""ReAct agent loop — shared by detection and RCA agents."""

from __future__ import annotations

import json
import logging
from typing import Any

from agent.llm_client import llm_client
from agent.tool_registry import registry

logger = logging.getLogger(__name__)

MAX_ROUNDS = 3


async def run_agent_loop(
    system_prompt: str,
    user_message: str,
    max_rounds: int = MAX_ROUNDS,
) -> dict[str, Any]:
    """Run a ReAct loop: LLM thinks → calls tools → repeats → final JSON answer.

    Returns parsed JSON from the LLM's final response.
    """
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]
    tools = registry.get_openai_tools()

    for round_num in range(1, max_rounds + 1):
        logger.info("Agent loop round %d/%d", round_num, max_rounds)
        response = await llm_client.chat(messages, tools=tools)

        # If no tool calls, this is the final answer
        tool_calls = response.get("tool_calls")
        if not tool_calls:
            return _parse_json_response(response.get("content", ""))

        # Process tool calls
        messages.append(response)
        for tc in tool_calls:
            fn_name = tc["function"]["name"]
            fn_args = json.loads(tc["function"]["arguments"]) if isinstance(tc["function"]["arguments"], str) else tc["function"]["arguments"]
            logger.info("Tool call: %s(%s)", fn_name, fn_args)

            result = await registry.dispatch(fn_name, fn_args)
            messages.append({
                "role": "tool",
                "tool_call_id": tc["id"],
                "content": result,
            })

    # Max rounds reached — ask for final answer without tools
    messages.append({
        "role": "user",
        "content": "최대 분석 라운드에 도달했습니다. 지금까지의 정보를 바탕으로 최종 JSON 결과를 제출하세요.",
    })
    response = await llm_client.chat(messages, tools=None)
    return _parse_json_response(response.get("content", ""))


def _parse_json_response(content: str) -> dict[str, Any]:
    """Extract JSON from LLM response (handles markdown code blocks)."""
    text = content.strip()
    if "```json" in text:
        text = text.split("```json", 1)[1].split("```", 1)[0].strip()
    elif "```" in text:
        text = text.split("```", 1)[1].split("```", 1)[0].strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        logger.warning("Failed to parse LLM JSON, returning raw content")
        return {"raw_content": content, "parse_error": True}
