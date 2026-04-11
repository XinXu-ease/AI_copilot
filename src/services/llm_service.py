import json
import logging
from typing import Any, Callable, Type, TypeVar

from openai import OpenAI
from pydantic import BaseModel, ValidationError

from src.config.settings import settings

logger = logging.getLogger(__name__)

# 初始化时打印配置
import sys
print(f"[INIT] LLM Service initialized", file=sys.stderr)
print(f"[INIT] Model: {settings.LITELLM_MODEL}", file=sys.stderr)
print(f"[INIT] Base URL: {settings.LITELLM_BASE_URL}", file=sys.stderr)
print(f"[INIT] Token exists: {bool(settings.LITELLM_TOKEN)}", file=sys.stderr)

T = TypeVar("T", bound=BaseModel)

client = OpenAI(
    api_key=settings.LITELLM_TOKEN,
    base_url=settings.LITELLM_BASE_URL,
)


class LLMServiceError(Exception):
    pass


class LLMJSONParseError(LLMServiceError):
    pass


class LLMValidationError(LLMServiceError):
    pass


ToolHandler = Callable[[dict[str, Any]], Any]


def _build_messages(system_prompt: str, user_prompt: str) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


def _extract_text(response: Any) -> str:
    try:
        return response.choices[0].message.content or ""
    except Exception as exc:
        raise LLMServiceError(f"Failed to extract response text: {exc}") from exc


RESPONSE_LENGTH_INSTRUCTION = (
    "Keep the entire JSON response under 2000 characters. "
    "Prefer concise field values and short lists. "
    "If a field can be expressed with fewer words, do so."
)


def _extract_balanced_json(text: str) -> str | None:
    """Try to recover the first balanced JSON object from a response."""
    start = text.find("{")
    if start == -1:
        return None

    depth = 0
    in_string = False
    escaped = False

    for index in range(start, len(text)):
        char = text[index]

        if escaped:
            escaped = False
            continue

        if char == "\\":
            escaped = True
            continue

        if char == '"':
            in_string = not in_string
            continue

        if in_string:
            continue

        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start:index + 1]

    return None


def _parse_json_text(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text.replace("json\n", "", 1).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        recovered = _extract_balanced_json(text)
        if recovered and recovered != text:
            try:
                logger.warning("Attempting to recover JSON from balanced object substring")
                return json.loads(recovered)
            except json.JSONDecodeError:
                pass

        raise LLMJSONParseError(
            f"Model output was not valid JSON.\nRaw output:\n{text[:1500]}"
        ) from exc


def call_text(
    system_prompt: str,
    user_prompt: str,
    *,
    model: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> str:
    model = model or settings.LITELLM_MODEL
    temperature = settings.LLM_TEMPERATURE if temperature is None else temperature
    max_tokens = settings.LLM_MAX_TOKENS if max_tokens is None else max_tokens

    try:
        response = client.chat.completions.create(
            model=model,
            messages=_build_messages(system_prompt, user_prompt),
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=settings.LLM_TIMEOUT,
        )
        return _extract_text(response)

    except Exception as exc:
        logger.exception("LLM text call failed")
        raise LLMServiceError(f"LLM text call failed: {exc}") from exc


def call_json(
    system_prompt: str,
    user_prompt: str,
    *,
    model: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> dict[str, Any]:
    model = model or settings.LITELLM_MODEL
    temperature = settings.LLM_TEMPERATURE if temperature is None else temperature
    max_tokens = settings.LLM_MAX_TOKENS if max_tokens is None else max_tokens

    final_user_prompt = (
        user_prompt
        + "\n\nReturn valid JSON only. Do not wrap in markdown. "
            "Do not include any explanation outside the JSON object. "
            f"{RESPONSE_LENGTH_INSTRUCTION}"
    )

    try:
        response = client.chat.completions.create(
            model=model,
            messages=_build_messages(system_prompt, final_user_prompt),
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=settings.LLM_TIMEOUT,
            response_format={"type": "json_object"},
        )
        text = _extract_text(response).strip()

        if text.startswith("```"):
            text = text.strip("`")
            text = text.replace("json\n", "", 1).strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            logger.exception("Failed to parse JSON from model output")
            raise LLMJSONParseError(
                f"Model output was not valid JSON.\nRaw output:\n{text}"
            ) from exc

    except Exception as exc:
        logger.exception("LLM JSON call failed")
        raise LLMServiceError(f"LLM JSON call failed: {exc}") from exc


def call_pydantic(
    system_prompt: str,
    user_prompt: str,
    schema: Type[T],
    *,
    model: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> T:
    data = call_json(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
    )

    try:
        return schema.model_validate(data)
    except ValidationError as exc:
        logger.exception("JSON validation against schema failed")
        raise LLMValidationError(
            f"JSON did not match schema {schema.__name__}: {exc}"
        ) from exc


def call_llm_json_with_tools(
    system_prompt: str,
    user_prompt: str,
    *,
    tools: list[dict[str, Any]],
    tool_handlers: dict[str, ToolHandler],
    max_tool_rounds: int = 4,
    model: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> dict[str, Any]:
    model = model or settings.LITELLM_MODEL
    temperature = settings.LLM_TEMPERATURE if temperature is None else temperature
    max_tokens = settings.LLM_MAX_TOKENS if max_tokens is None else max_tokens

    final_user_prompt = (
        user_prompt
        + "\n\nReturn valid JSON only. "
          "Do not wrap in markdown. "
          "Do not include any explanation outside the JSON object. "
          f"{RESPONSE_LENGTH_INSTRUCTION}"
    )

    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": final_user_prompt},
    ]

    try:
        for _ in range(max_tool_rounds + 1):
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                tools=tools,
                tool_choice="auto",
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=settings.LLM_TIMEOUT,
                response_format={"type": "json_object"},
            )

            message = response.choices[0].message
            tool_calls = message.tool_calls or []

            if not tool_calls:
                text = (message.content or "").strip()
                return _parse_json_text(text)

            assistant_message: dict[str, Any] = {
                "role": "assistant",
                "content": message.content or "",
                "tool_calls": [
                    {
                        "id": call.id,
                        "type": "function",
                        "function": {
                            "name": call.function.name,
                            "arguments": call.function.arguments or "{}",
                        },
                    }
                    for call in tool_calls
                ],
            }
            messages.append(assistant_message)

            for call in tool_calls:
                tool_name = call.function.name
                handler = tool_handlers.get(tool_name)
                if handler is None:
                    tool_result: Any = {"error": f"Tool not implemented: {tool_name}"}
                else:
                    try:
                        raw_arguments = call.function.arguments or "{}"
                        args = json.loads(raw_arguments)
                    except json.JSONDecodeError:
                        args = {}

                    try:
                        tool_result = handler(args)
                    except Exception as tool_exc:
                        logger.exception("Tool execution failed: %s", tool_name)
                        tool_result = {"error": f"Tool {tool_name} failed: {str(tool_exc)}"}

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.id,
                        "content": json.dumps(tool_result, ensure_ascii=False),
                    }
                )

        raise LLMServiceError("Tool-calling exceeded max rounds without final JSON output")
    except LLMJSONParseError:
        raise
    except Exception as exc:
        logger.exception("LLM tool-calling failed")
        raise LLMServiceError(f"LLM tool-calling failed: {exc}") from exc

def call_llm_json(
    system_prompt: str,
    user_prompt: str,
    *,
    model: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> dict:
    model = model or settings.LITELLM_MODEL
    temperature = settings.LLM_TEMPERATURE if temperature is None else temperature
    max_tokens = settings.LLM_MAX_TOKENS if max_tokens is None else max_tokens

    final_user_prompt = (
        user_prompt
        + "\n\nReturn valid JSON only. "
          "Do not wrap in markdown. "
            "Do not include any explanation outside the JSON object. "
            f"{RESPONSE_LENGTH_INSTRUCTION}"
    )

    try:
        response = client.chat.completions.create(
            model=model,
            messages=_build_messages(system_prompt, final_user_prompt),
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=settings.LLM_TIMEOUT,
            response_format={"type": "json_object"},
        )

        text = _extract_text(response).strip()

        # 调试信息
        debug_info = f"\n[DEBUG] Model: {model} | Response length: {len(text)}"
        if len(text) > 0:
            debug_info += f"\nFirst 300 chars:\n{text[:300]}"
        else:
            debug_info += "\n!!! EMPTY RESPONSE FROM MODEL !!!"

        logger.info(debug_info)

        return _parse_json_text(text)

    except LLMJSONParseError:
        raise
    except Exception as exc:
        logger.exception(f"LLM API call failed with {type(exc).__name__}: {str(exc)[:500]}")
        logger.error(f"Model: {model}, Base URL: {settings.LITELLM_BASE_URL}")
        raise LLMServiceError(f"LLM API failed ({type(exc).__name__}): {str(exc)[:200]}") from exc