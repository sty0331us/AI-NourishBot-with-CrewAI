"""Shared IBM watsonx.ai client configuration."""

import logging
import os

from dotenv import load_dotenv
from ibm_watsonx_ai import APIClient, Credentials
from ibm_watsonx_ai.foundation_models import ModelInference

load_dotenv()

logger = logging.getLogger(__name__)

WATSONX_URL = os.getenv("WATSONX_URL", "https://us-south.ml.cloud.ibm.com")
WATSONX_API_KEY = os.getenv("WATSONX_API_KEY", "")
WATSONX_PROJECT_ID = os.getenv("WATSONX_PROJECT_ID", "skills-network")

VISION_MODEL_ID = os.getenv(
    "VISION_MODEL_ID", "meta-llama/llama-3-2-90b-vision-instruct"
)
TEXT_MODEL_ID = os.getenv("TEXT_MODEL_ID", "ibm/granite-4-h-small")


def get_credentials() -> Credentials:
    """Build watsonx credentials from environment variables."""
    kwargs = {"url": WATSONX_URL}
    if WATSONX_API_KEY:
        kwargs["api_key"] = WATSONX_API_KEY
    return Credentials(**kwargs)


def get_api_client() -> APIClient:
    """Return a configured watsonx API client."""
    return APIClient(get_credentials())


def get_vision_model(max_tokens: int = 300) -> ModelInference:
    """Return a vision-capable ModelInference instance."""
    return ModelInference(
        model_id=VISION_MODEL_ID,
        credentials=get_credentials(),
        project_id=WATSONX_PROJECT_ID,
        params={"max_tokens": max_tokens},
    )


def get_text_model(max_tokens: int = 150) -> ModelInference:
    """Return a text ModelInference instance for filtering / reasoning."""
    return ModelInference(
        model_id=TEXT_MODEL_ID,
        credentials=get_credentials(),
        project_id=WATSONX_PROJECT_ID,
        params={"max_tokens": max_tokens},
    )
