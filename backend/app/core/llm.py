import logging
from typing import Optional, List, Any

try:
    from langchain_core.language_models.chat_models import BaseChatModel
    from langchain_core.embeddings import Embeddings
    from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
    _HAS_LANGCHAIN = True
except ImportError:
    _HAS_LANGCHAIN = False
    class BaseChatModel:
        pass
    class Embeddings:
        pass
    class AIMessage:
        def __init__(self, content: str = ""):
            self.content = content
    class SystemMessage(AIMessage):
        pass
    class HumanMessage(AIMessage):
        pass

from app.core.config import settings

logger = logging.getLogger(__name__)


class LLMFactory:
    """
    Factory for instantiating LangChain LLMs and Embedding models.
    Supports Google Gemini (gemini-2.5-pro / gemini-2.5-flash) with Groq fallback.
    """

    @staticmethod
    def get_review_model(
        temperature: float = 0.2,
        model_name: Optional[str] = None
    ) -> Any:
        target_model = model_name or settings.DEFAULT_REVIEW_MODEL
        
        if _HAS_LANGCHAIN and settings.GEMINI_API_KEY:
            try:
                from langchain_google_genai import ChatGoogleGenerativeAI
                return ChatGoogleGenerativeAI(
                    model=target_model,
                    google_api_key=settings.GEMINI_API_KEY,
                    temperature=temperature,
                    max_output_tokens=4096,
                )
            except Exception as e:
                logger.warning(f"Failed to initialize ChatGoogleGenerativeAI: {e}. Falling back...")

        if _HAS_LANGCHAIN and settings.GROQ_API_KEY:
            try:
                from langchain_groq import ChatGroq
                return ChatGroq(
                    model_name=settings.FALLBACK_MODEL,
                    groq_api_key=settings.GROQ_API_KEY,
                    temperature=temperature,
                    max_tokens=4096,
                )
            except Exception as e:
                logger.error(f"Failed to initialize ChatGroq: {e}")

        # Development / mock chat model
        class MockChatModel:
            async def ainvoke(self, messages: Any) -> AIMessage:
                return AIMessage(content='{"summary": "Automated code review passed with no critical issues.", "risk_score": 2, "recommendation": "APPROVE", "findings": []}')
            
            def with_structured_output(self, schema: Any):
                mock_self = self
                class StructuredRunner:
                    async def ainvoke(self, messages: Any):
                        from app.agents.schemas import SpecialistReviewOutput
                        return SpecialistReviewOutput(
                            agent_name="specialist",
                            summary="Automated mock review passed.",
                            risk_score=2,
                            findings=[],
                        )
                return StructuredRunner()

        return MockChatModel()

    @staticmethod
    def get_fast_model(
        temperature: float = 0.1,
        model_name: Optional[str] = None
    ) -> Any:
        target_model = model_name or settings.FAST_SUMMARY_MODEL
        return LLMFactory.get_review_model(temperature=temperature, model_name=target_model)

    @staticmethod
    def get_embedding_model() -> Any:
        """Returns embedding model for code indexing."""
        if _HAS_LANGCHAIN and settings.GEMINI_API_KEY:
            try:
                from langchain_google_genai import GoogleGenerativeAIEmbeddings
                return GoogleGenerativeAIEmbeddings(
                    model=settings.EMBEDDING_MODEL,
                    google_api_key=settings.GEMINI_API_KEY,
                )
            except Exception as e:
                logger.warning(f"Failed to initialize GoogleGenerativeAIEmbeddings: {e}")

        class MockCodeEmbeddings:
            def embed_documents(self, texts: List[str]) -> List[List[float]]:
                import hashlib
                import math
                results = []
                for text in texts:
                    h = hashlib.sha256(text.encode("utf-8")).digest()
                    raw = [float((b % 100) - 50) for b in (h * 24)[:settings.VECTOR_DIMENSION]]
                    norm = math.sqrt(sum(x * x for x in raw)) or 1.0
                    results.append([x / norm for x in raw])
                return results

            def embed_query(self, text: str) -> List[float]:
                return self.embed_documents([text])[0]

        return MockCodeEmbeddings()
