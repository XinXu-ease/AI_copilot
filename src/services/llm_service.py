import json
import logging
from typing import Any, Type, TypeVar

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
          "Do not include any explanation outside the JSON object."
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
          "Do not include any explanation outside the JSON object."
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

        if text.startswith("```"):
            text = text.strip("`")
            text = text.replace("json\n", "", 1).strip()

        try:
            data = json.loads(text)
            return data
        except json.JSONDecodeError as exc:
            error_msg = (
                f"Model output was not valid JSON.\n"
                f"{debug_info}\n"
                f"Full output:\n{text[:1500]}"
            )
            logger.exception(error_msg)
            raise LLMJSONParseError(error_msg) from exc

    except LLMJSONParseError:
        raise
    except Exception as exc:
        logger.exception(f"LLM API call failed with {type(exc).__name__}: {str(exc)[:500]}")
        logger.error(f"Model: {model}, Base URL: {settings.LITELLM_BASE_URL}")
        raise LLMServiceError(f"LLM API failed ({type(exc).__name__}): {str(exc)[:200]}") from exc