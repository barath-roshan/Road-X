"""LLM Provider Abstraction layer supporting Mock, Groq, OpenAI, and Hugging Face integration for RoadX RAG."""

from __future__ import annotations

import json
import re
import urllib.request
import urllib.error
from abc import ABC, abstractmethod
from typing import Optional

from backend.config import chatbot_settings
from backend.chatbot.prompts import SYSTEM_GROUNDING_PROMPT
from ml.common.logging_config import get_logger

logger = get_logger(__name__)


class LLMProvider(ABC):
    """Abstract interface for grounded LLM text generation."""

    @abstractmethod
    def generate_response(
        self,
        user_query: str,
        context_text: str,
        system_prompt: Optional[str] = None,
    ) -> str:
        """Generate grounded conversational response."""
        pass


class MockLLMProvider(LLMProvider):
    """Deterministic grounded response generator for offline testing and mock mode."""

    def generate_response(
        self,
        user_query: str,
        context_text: str,
        system_prompt: Optional[str] = None,
    ) -> str:
        """Parse structured context and query to generate grounded, accurate response."""
        query_lower = user_query.lower().strip()

        if not user_query or not user_query.strip():
            return "Please provide a valid question regarding your grievances or road operations."

        # Check for Grievance query
        if any(term in query_lower for term in ["complaint", "grievance", "status", "pothole", "track", "progress", "my road"]):
            if "CITIZEN ACCOUNT GRIEVANCES:" in context_text and "No grievances reported" not in context_text:
                # Extract grievance lines
                lines = context_text.splitlines()
                grievance_lines = [l for l in lines if l.startswith("Grievance #")]
                if grievance_lines:
                    response_parts = ["Here is the current status of your submitted road grievance(s):"]
                    for line in grievance_lines:
                        response_parts.append(f"- {line}")
                    response_parts.append("\nOur government officers and contractors are managing these reports according to RoadX workflows.")
                    return "\n".join(response_parts)
            elif "No grievances reported" in context_text:
                return "You currently do not have any submitted grievances registered under your RoadX account."

        # Check for Road Operation / Closure query
        if any(term in query_lower for term in ["road operation", "closure", "closed", "detour", "alternative route", "restriction", "maintenance"]):
            if "ACTIVE/PLANNED MUNICIPAL ROAD OPERATIONS:" in context_text and "No active public road operations" not in context_text:
                lines = context_text.splitlines()
                op_lines = [l for l in lines if l.startswith("Operation #")]
                if op_lines:
                    response_parts = ["Active and planned municipal road operations affecting traffic:"]
                    for line in op_lines:
                        response_parts.append(f"- {line}")
                    return "\n".join(response_parts)
            elif "No active public road operations" in context_text:
                return "There are currently no active or planned public road operations or closures reported in your area."

        # Check for Knowledge Base FAQs matching
        if "ROADX KNOWLEDGE BASE GUIDANCE & FAQS:" in context_text and "No specific knowledge base guidance" not in context_text:
            lines = context_text.splitlines()
            kb_lines = [l for l in lines if l.startswith("Knowledge #")]
            if kb_lines:
                kb_text_block = "\n".join(kb_lines)
                return f"Based on official RoadX platform guidance:\n{kb_text_block}"

        # Fallback when context is insufficient
        return "I don't have enough information in RoadX records to answer that question. Please check back later or contact municipal support."


class GroqLLMProvider(LLMProvider):
    """External LLM Provider integration via Groq OpenAI-compatible API."""

    def __init__(self, api_key: str, model: str = "llama3-8b-8192") -> None:
        self.api_key = api_key
        self.model = model
        self.fallback = MockLLMProvider()

    def generate_response(
        self,
        user_query: str,
        context_text: str,
        system_prompt: Optional[str] = None,
    ) -> str:
        """Call Groq API with system grounding prompt."""
        if not self.api_key:
            logger.warning("Groq API key missing. Falling back to MockLLMProvider.")
            return self.fallback.generate_response(user_query, context_text, system_prompt)

        sys_prompt = system_prompt or SYSTEM_GROUNDING_PROMPT.format(context_text=context_text)
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_query},
            ],
            "temperature": chatbot_settings.llm_temperature,
            "max_tokens": chatbot_settings.llm_max_tokens,
        }

        try:
            req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            logger.error("Groq LLM API invocation failed: %s. Using safe fallback.", e)
            return self.fallback.generate_response(user_query, context_text, system_prompt)


class OpenAILLMProvider(LLMProvider):
    """External LLM Provider integration via OpenAI Chat API."""

    def __init__(self, api_key: str, model: str = "gpt-3.5-turbo") -> None:
        self.api_key = api_key
        self.model = model
        self.fallback = MockLLMProvider()

    def generate_response(
        self,
        user_query: str,
        context_text: str,
        system_prompt: Optional[str] = None,
    ) -> str:
        """Call OpenAI API with system grounding prompt."""
        if not self.api_key:
            logger.warning("OpenAI API key missing. Falling back to MockLLMProvider.")
            return self.fallback.generate_response(user_query, context_text, system_prompt)

        sys_prompt = system_prompt or SYSTEM_GROUNDING_PROMPT.format(context_text=context_text)
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_query},
            ],
            "temperature": chatbot_settings.llm_temperature,
            "max_tokens": chatbot_settings.llm_max_tokens,
        }

        try:
            req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            logger.error("OpenAI LLM API invocation failed: %s. Using safe fallback.", e)
            return self.fallback.generate_response(user_query, context_text, system_prompt)


def get_llm_provider() -> LLMProvider:
    """Factory function returning configured LLMProvider based on settings."""
    provider_name = chatbot_settings.llm_provider.lower()

    if provider_name == "groq" and chatbot_settings.llm_api_key:
        return GroqLLMProvider(api_key=chatbot_settings.llm_api_key, model=chatbot_settings.llm_model)
    elif provider_name == "openai" and chatbot_settings.llm_api_key:
        return OpenAILLMProvider(api_key=chatbot_settings.llm_api_key, model=chatbot_settings.llm_model)
    else:
        return MockLLMProvider()
