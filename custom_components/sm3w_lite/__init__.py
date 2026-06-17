"""Integração SM-3W Lite (IE Tecnologia) via MQTT para o Home Assistant."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_TOPIC, DOMAIN
from .coordinator import SM3WLiteCoordinator

PLATFORMS = ["sensor"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Configura uma entrada (um medidor) a partir do tópico MQTT salvo."""
    coordinator = SM3WLiteCoordinator(hass, entry.data[CONF_TOPIC])
    await coordinator.async_start()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Remove uma entrada: cancela a assinatura MQTT e descarrega os sensores."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        coordinator: SM3WLiteCoordinator | None = hass.data[DOMAIN].pop(
            entry.entry_id, None
        )
        if coordinator is not None:
            await coordinator.async_stop()
    return unloaded
