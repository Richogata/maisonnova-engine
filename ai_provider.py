# -*- coding: utf-8 -*-
"""Couche d'abstraction IA — AIProvider.

Encapsule le système Gemini existant (google-generativeai) avec :
  - repli automatique sur une liste de modèles ;
  - mode JSON optionnel (response_mime_type) ;
  - mode dégradé : si aucune clé API, ready=False et complete() renvoie None
    (l'application continue avec le fallback par règles / messages modèles).

Aucun nouveau service IA payant n'est introduit.
"""

import json
import logging
import re


class AIProvider:
    """Fournisseur IA unique de l'application (Gemini aujourd'hui)."""

    def __init__(self, api_key: str = "", models: list[str] | None = None,
                 timeout: int = 60):
        self.api_key = api_key or ""
        self.models = list(models) if models else []
        self.timeout = timeout
        self._configured = False
        if self.api_key:
            self._try_configure()

    # ── état ────────────────────────────────────────────────────────────────
    @property
    def ready(self) -> bool:
        return bool(self.api_key) and self._configured

    def configure(self, api_key: str) -> bool:
        self.api_key = api_key or ""
        self._configured = False
        if self.api_key:
            self._try_configure()
        return self.ready

    def _try_configure(self) -> None:
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            self._configured = True
        except Exception as exc:
            logging.warning("Gemini indisponible : %s", exc)
            self._configured = False

    # ── appels ──────────────────────────────────────────────────────────────
    def complete(self, system_prompt: str, user_text: str,
                 temperature: float = 0.6, json_mode: bool = False,
                 max_tokens: int = 700) -> str | None:
        """Appelle l'IA (repli automatique de modèle). Retourne le texte brut,
        ou None en cas d'échec total."""
        if not self.ready:
            return None
        try:
            import google.generativeai as genai
        except Exception:
            return None
        for name in self.models:
            try:
                genai.GenerativeModel(model_name=name)
                cfg = genai.types.GenerationConfig(
                    temperature=temperature,
                    max_output_tokens=max_tokens,
                    **({"response_mime_type": "application/json"} if json_mode else {}),
                )
                model = genai.GenerativeModel(model_name=name, system_instruction=system_prompt)
                resp = model.generate_content(user_text, generation_config=cfg,
                                              request_options={"timeout": self.timeout})
                if resp and getattr(resp, "text", None):
                    # réponse coupée par la limite de tokens → on ne renvoie JAMAIS
                    # un texte tronqué : l'application bascule sur le repli lisible
                    if _is_truncated(resp):
                        logging.warning("Réponse tronquée (MAX_TOKENS) sur %s — repli.", name)
                        return None
                    return resp.text
            except Exception as exc:
                logging.debug("Modèle %s en échec : %s", name, exc)
                continue
        return None


    def json(self, system_prompt: str, user_text: str, max_tokens: int = 800) -> dict | None:
        """Version 'mode JSON' avec nettoyage robuste des réponses."""
        raw = self.complete(system_prompt, user_text, temperature=0.2,
                            json_mode=True, max_tokens=max_tokens)
        if not raw:
            return None
        raw = raw.strip()
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        start, end = raw.find("{"), raw.rfind("}")
        if start == -1 or end == -1:
            return None
        try:
            return json.loads(raw[start:end + 1])
        except Exception:
            return None


def _is_truncated(resp) -> bool:
    """True si la réponse Gemini a été interrompue par la limite de tokens."""
    try:
        cand = resp.candidates[0]
        fr = getattr(cand, "finish_reason", None)
        if fr is None:
            return False
        name = getattr(fr, "name", None)
        if not name:
            name = str(fr)
        return "MAX_TOKENS" in name.upper()
    except Exception:
        return False
