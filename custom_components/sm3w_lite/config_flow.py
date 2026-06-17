"""Config flow da integração SM-3W Lite.

Permite adicionar quantos medidores forem necessários: basta repetir o
fluxo "Adicionar Integração" uma vez para cada medidor, cada um com seu
próprio tópico MQTT.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components import mqtt
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .const import CONF_TOPIC, DEFAULT_NAME, DOMAIN, LISTEN_TIMEOUT

_LOGGER = logging.getLogger(__name__)


async def _topic_has_messages(hass, topic: str) -> bool:
    """Escuta rapidamente o tópico para confirmar que o medidor está publicando ali."""
    received = asyncio.Event()

    @callback
    def _on_message(_msg) -> None:
        received.set()

    unsubscribe = await mqtt.async_subscribe(hass, topic, _on_message, qos=0)
    try:
        await asyncio.wait_for(received.wait(), timeout=LISTEN_TIMEOUT)
        return True
    except TimeoutError:
        return False
    finally:
        unsubscribe()


class SM3WLiteConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Fluxo de configuração: um medidor por entrada, múltiplas entradas permitidas."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            topic = user_input[CONF_TOPIC].strip()

            await self.async_set_unique_id(topic)
            self._abort_if_unique_id_configured()

            try:
                ok = await _topic_has_messages(self.hass, topic)
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Erro ao testar o tópico MQTT %s", topic)
                ok = False

            if not ok:
                errors["base"] = "no_message"
            else:
                return self.async_create_entry(
                    title=user_input.get(CONF_NAME) or DEFAULT_NAME,
                    data={CONF_TOPIC: topic, CONF_NAME: user_input.get(CONF_NAME)},
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_TOPIC): str,
                vol.Optional(CONF_NAME, default=DEFAULT_NAME): str,
            }
        )

        return self.async_show_form(
            step_id="user", data_schema=schema, errors=errors
        )
