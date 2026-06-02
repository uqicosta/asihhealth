"""
AsihHealth - LLM Client
Support: Ollama (primary, gratis), Groq, Gemini
Optimized for Indonesian health content generation
"""

import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from config.settings import (
    LLM_PROVIDER, OLLAMA_HOST, OLLAMA_MODEL,
    GROQ_API_KEY, GROQ_MODEL,
    GEMINI_API_KEY, GEMINI_MODEL
)

logger = logging.getLogger(__name__)


class LLMClient:
    """Unified LLM client with cost-efficient defaults."""

    def __init__(self, provider: Optional[str] = None, model: Optional[str] = None):
        self.provider = provider or LLM_PROVIDER

        # Choose smart default model based on provider
        if model:
            self.model = model
        else:
            if self.provider == "groq":
                self.model = GROQ_MODEL
            elif self.provider == "gemini":
                self.model = GEMINI_MODEL
            else:
                self.model = OLLAMA_MODEL

        if self.provider == "ollama":
            self._init_ollama()
        elif self.provider == "groq":
            # Safety check: user mungkin masih pakai nama model Ollama
            if ":" in self.model or self.model.startswith(("qwen", "llama3", "gemma")) and not self.model.startswith("llama-"):
                logger.warning(f"Model '{self.model}' sepertinya format Ollama. Beralih ke default Groq...")
                self.model = GROQ_MODEL
            self._init_groq()
        elif self.provider == "gemini":
            self._init_gemini()
        else:
            raise ValueError(f"Unsupported LLM provider: {self.provider}")

    def _init_ollama(self):
        try:
            import ollama
            self.client = ollama.Client(host=OLLAMA_HOST)
            logger.info(f"Ollama client initialized → {self.model}")
        except ImportError:
            raise ImportError("Install ollama: pip install ollama")

    def _init_groq(self):
        try:
            from groq import Groq
            self.client = Groq(api_key=GROQ_API_KEY)
            logger.info(f"Groq client initialized → {self.model}")
        except ImportError:
            raise ImportError("Install groq: pip install groq")

    def _init_gemini(self):
        try:
            import google.generativeai as genai
            genai.configure(api_key=GEMINI_API_KEY)
            self.client = genai.GenerativeModel(self.model)
            logger.info(f"Gemini client initialized → {self.model}")
        except ImportError:
            raise ImportError("Install google-generativeai: pip install google-generativeai")

    def generate(self, prompt: str, system: str = "", temperature: float = 0.7, max_tokens: int = 4096) -> str:
        """Generate text completion."""
        if self.provider == "ollama":
            return self._generate_ollama(prompt, system, temperature)
        elif self.provider == "groq":
            return self._generate_groq(prompt, system, temperature, max_tokens)
        elif self.provider == "gemini":
            return self._generate_gemini(prompt, system, temperature)
        raise NotImplementedError

    def _generate_ollama(self, prompt: str, system: str, temperature: float) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        response = self.client.chat(
            model=self.model,
            messages=messages,
            options={"temperature": temperature}
        )
        return response["message"]["content"]

    def _generate_groq(self, prompt: str, system: str, temperature: float, max_tokens: int) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        resp = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return resp.choices[0].message.content

    def _generate_gemini(self, prompt: str, system: str, temperature: float) -> str:
        if system:
            full_prompt = f"{system}\n\n{prompt}"
        else:
            full_prompt = prompt

        response = self.client.generate_content(
            full_prompt,
            generation_config={"temperature": temperature}
        )
        return response.text

    def generate_json(self, prompt: str, system: str = "", temperature: float = 0.6) -> Dict[str, Any]:
        """
        Generate and parse JSON response.
        Important for script generation.
        """
        # Add strong JSON instruction
        json_instruction = "\n\nWAJIB: Keluarkan HANYA JSON valid tanpa markdown code block atau teks lain."
        full_prompt = prompt + json_instruction

        raw = self.generate(full_prompt, system, temperature)

        # Clean common LLM JSON mistakes
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip("` \n")

        try:
            return json.loads(raw)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from LLM. Raw output:\n{raw[:500]}")
            raise ValueError(f"LLM returned invalid JSON: {e}")


def load_prompt_template(name: str) -> str:
    """Load prompt template from templates/prompts/"""
    template_path = Path(__file__).parent.parent / "templates" / "prompts" / f"{name}.txt"
    if not template_path.exists():
        raise FileNotFoundError(f"Prompt template not found: {template_path}")
    return template_path.read_text(encoding="utf-8")


def generate_health_script(topic: str, client: Optional[LLMClient] = None) -> Dict[str, Any]:
    """
    High-level function: Generate complete YouTube script for health topic.
    Returns structured dict ready for downstream processing.
    """
    client = client or LLMClient()
    template = load_prompt_template("health_script")

    prompt = template.format(topic=topic)

    system_prompt = (
        "Anda adalah penulis konten kesehatan YouTube berpengalaman yang sangat memahami "
        "bahasa Indonesia natural dan standar akurasi informasi medis."
    )

    logger.info(f"Generating health script for topic: {topic}")
    result = client.generate_json(prompt, system=system_prompt, temperature=0.65)

    # Basic validation
    required = ["title", "description", "script", "tags"]
    for key in required:
        if key not in result:
            raise ValueError(f"Missing required key in script output: {key}")

    logger.info(f"Script generated: '{result['title']}' ({len(result.get('script',''))} chars)")
    return result
