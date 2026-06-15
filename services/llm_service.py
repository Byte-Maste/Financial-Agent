import time
from typing import Any

from groq import AsyncGroq
from langchain_core.callbacks import AsyncCallbackManagerForLLMRun
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_groq.chat_models import _convert_dict_to_message, _convert_message_to_dict

from core.config import settings
from core.logger import logger


def _groq_configured() -> bool:
    key = settings.groq_api_key
    return bool(key) and key.startswith("gsk_")


class FallbackLLM(BaseChatModel):
    """
    Drop-in replacement for any LangChain chat model.

    Uses the raw groq.Groq client (not langchain_groq.ChatGroq).
    Supports .with_structured_output(PydanticModel) transparently.
    """

    client: AsyncGroq | None = None
    model: str = ""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.client = AsyncGroq(api_key=settings.groq_api_key) if _groq_configured() else None
        self.model = settings.llm_model

    @property
    def _llm_type(self) -> str:
        return "groq"

    @property
    def _identifying_params(self) -> dict:
        return {"model": self.model}

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        raise NotImplementedError("Sync generate not supported; use async")

    async def _agenerate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: AsyncCallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        if not self.client:
            raise RuntimeError("No LLM provider configured — set GROQ_API_KEY in .env")

        message_dicts = [_convert_message_to_dict(m) for m in messages]
        params: dict = {"model": self.model}
        if stop:
            params["stop"] = stop
        params.update(kwargs)

        try:
            start = time.time()
            response = await self.client.chat.completions.create(
                messages=message_dicts, **params
            )
            elapsed = time.time() - start
            logger.info(f"LLM invoked | provider=groq | model={self.model} | took={elapsed:.2f}s")

            response_dict = response.model_dump() if hasattr(response, "model_dump") else dict(response)
            generations = []
            for res in response_dict.get("choices", []):
                message = _convert_dict_to_message(res["message"])
                gen = ChatGeneration(
                    message=message,
                    generation_info={"finish_reason": res.get("finish_reason")},
                )
                generations.append(gen)

            token_usage = response_dict.get("usage", {})
            llm_output = {
                "token_usage": token_usage,
                "model_name": self.model,
                "system_fingerprint": response_dict.get("system_fingerprint", ""),
            }
            return ChatResult(generations=generations, llm_output=llm_output)

        except Exception as e:
            logger.error(f"Groq LLM failed: {e}")
            raise
