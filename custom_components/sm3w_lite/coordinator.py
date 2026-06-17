"""Coordenador de dados para o medidor SM-3W Lite, alimentado via MQTT.

O medidor publica periodicamente (a cada poucos segundos) uma mensagem JSON
em um tópico MQTT configurado no próprio equipamento. Esse coordenador se
inscreve nesse tópico e repassa os dados já convertidos para float para as
entidades (sensores), no estilo "push" recomendado pela documentação do
Home Assistant para fontes de dados que não precisam ser consultadas
(polling), apenas escutadas.
"""
from __future__ import annotations

import json
import logging
from typing import Any

from homeassistant.components import mqtt
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


def extract_numeric_fields(payload: dict[str, Any]) -> dict[str, float]:
    """Converte os campos numéricos do payload (exceto 'id') para float.

    O medidor envia todos os valores como strings (ex.: "616.24"), então
    aqui a gente tenta converter cada um; campos que não forem números
    (como o "id") são ignorados silenciosamente.
    """
    data: dict[str, float] = {}
    for key, value in payload.items():
        if key == "id":
            continue
        try:
            data[key] = float(value)
        except (TypeError, ValueError):
            continue
    return data


class SM3WLiteCoordinator(DataUpdateCoordinator[dict[str, float]]):
    """Mantém os últimos valores recebidos via MQTT para um medidor."""

    def __init__(self, hass: HomeAssistant, topic: str) -> None:
        self.topic = topic
        self.device_id: str | None = None
        self._unsubscribe = None
        # update_interval=None -> este coordenador nunca faz polling.
        # Os dados só são atualizados quando uma mensagem MQTT chega
        # (via self.async_set_updated_data, chamado em _message_received).
        super().__init__(
            hass,
            _LOGGER,
            name=f"sm3w_lite_{topic}",
            update_interval=None,
        )

    async def async_start(self) -> None:
        """Assina o tópico MQTT do medidor."""
        self._unsubscribe = await mqtt.async_subscribe(
            self.hass, self.topic, self._message_received, qos=0
        )

    async def async_stop(self) -> None:
        """Cancela a assinatura do tópico MQTT."""
        if self._unsubscribe is not None:
            self._unsubscribe()
            self._unsubscribe = None

    @callback
    def _message_received(self, msg) -> None:
        """Processa uma nova mensagem recebida do medidor."""
        try:
            raw = json.loads(msg.payload)
        except (ValueError, TypeError):
            _LOGGER.debug(
                "Payload recebido em %s não é um JSON válido: %s",
                self.topic,
                msg.payload,
            )
            return

        if not isinstance(raw, dict):
            _LOGGER.debug("Payload recebido em %s não é um objeto JSON", self.topic)
            return

        raw_id = raw.get("id")
        if raw_id is not None:
            self.device_id = str(raw_id)

        data = extract_numeric_fields(raw)
        if data:
            self.async_set_updated_data(data)
