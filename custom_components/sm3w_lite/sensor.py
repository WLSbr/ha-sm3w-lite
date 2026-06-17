"""Plataforma de sensores da integração SM-3W Lite.

As entidades são criadas dinamicamente a partir das chaves que aparecem
no JSON publicado pelo medidor. Isso significa que, se o seu medidor não
enviar algum campo (por exemplo, por não ser bidirecional), o sensor
correspondente simplesmente não é criado — e se um firmware futuro
adicionar um campo novo que a gente não conhece, ele ainda aparece como
um sensor genérico em vez de ser descartado.
"""
from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    UnitOfApparentPower,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfFrequency,
    UnitOfPower,
    UnitOfReactivePower,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import SM3WLiteCoordinator


@dataclass(frozen=True)
class _Meta:
    """Metadados de exibição para um campo conhecido do medidor."""

    name: str
    unit: str | None
    device_class: SensorDeviceClass | None
    state_class: SensorStateClass | None
    diagnostic: bool = False


# Mapa: chave do JSON do medidor -> como exibir no Home Assistant.
#
# Observação sobre "pga/pgb/pgc" e "yuaub/yuauc/yubuc": o fabricante não
# documenta publicamente esses campos. Pelos valores observados (em graus,
# e próximos dos 120° esperados entre fases de um sistema trifásico
# equilibrado), a melhor interpretação é que são ângulos de fase. Se algum
# dia você descobrir o significado exato, é só ajustar o nome aqui.
_KNOWN: dict[str, _Meta] = {
    # Potência ativa (W)
    "pa": _Meta("Potência Ativa Fase A", UnitOfPower.WATT, SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT),
    "pb": _Meta("Potência Ativa Fase B", UnitOfPower.WATT, SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT),
    "pc": _Meta("Potência Ativa Fase C", UnitOfPower.WATT, SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT),
    "pt": _Meta("Potência Ativa Total", UnitOfPower.WATT, SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT),
    # Potência reativa (var)
    "qa": _Meta("Potência Reativa Fase A", UnitOfReactivePower.VOLT_AMPERE_REACTIVE, SensorDeviceClass.REACTIVE_POWER, SensorStateClass.MEASUREMENT),
    "qb": _Meta("Potência Reativa Fase B", UnitOfReactivePower.VOLT_AMPERE_REACTIVE, SensorDeviceClass.REACTIVE_POWER, SensorStateClass.MEASUREMENT),
    "qc": _Meta("Potência Reativa Fase C", UnitOfReactivePower.VOLT_AMPERE_REACTIVE, SensorDeviceClass.REACTIVE_POWER, SensorStateClass.MEASUREMENT),
    "qt": _Meta("Potência Reativa Total", UnitOfReactivePower.VOLT_AMPERE_REACTIVE, SensorDeviceClass.REACTIVE_POWER, SensorStateClass.MEASUREMENT),
    # Potência aparente (VA)
    "sa": _Meta("Potência Aparente Fase A", UnitOfApparentPower.VOLT_AMPERE, SensorDeviceClass.APPARENT_POWER, SensorStateClass.MEASUREMENT),
    "sb": _Meta("Potência Aparente Fase B", UnitOfApparentPower.VOLT_AMPERE, SensorDeviceClass.APPARENT_POWER, SensorStateClass.MEASUREMENT),
    "sc": _Meta("Potência Aparente Fase C", UnitOfApparentPower.VOLT_AMPERE, SensorDeviceClass.APPARENT_POWER, SensorStateClass.MEASUREMENT),
    "st": _Meta("Potência Aparente Total", UnitOfApparentPower.VOLT_AMPERE, SensorDeviceClass.APPARENT_POWER, SensorStateClass.MEASUREMENT),
    # Tensão (V)
    "uarms": _Meta("Tensão Fase A", UnitOfElectricPotential.VOLT, SensorDeviceClass.VOLTAGE, SensorStateClass.MEASUREMENT),
    "ubrms": _Meta("Tensão Fase B", UnitOfElectricPotential.VOLT, SensorDeviceClass.VOLTAGE, SensorStateClass.MEASUREMENT),
    "ucrms": _Meta("Tensão Fase C", UnitOfElectricPotential.VOLT, SensorDeviceClass.VOLTAGE, SensorStateClass.MEASUREMENT),
    # Corrente (A)
    "iarms": _Meta("Corrente Fase A", UnitOfElectricCurrent.AMPERE, SensorDeviceClass.CURRENT, SensorStateClass.MEASUREMENT),
    "ibrms": _Meta("Corrente Fase B", UnitOfElectricCurrent.AMPERE, SensorDeviceClass.CURRENT, SensorStateClass.MEASUREMENT),
    "icrms": _Meta("Corrente Fase C", UnitOfElectricCurrent.AMPERE, SensorDeviceClass.CURRENT, SensorStateClass.MEASUREMENT),
    "itrms": _Meta("Corrente Total", UnitOfElectricCurrent.AMPERE, SensorDeviceClass.CURRENT, SensorStateClass.MEASUREMENT),
    # Fator de potência (adimensional)
    "pfa": _Meta("Fator de Potência Fase A", None, SensorDeviceClass.POWER_FACTOR, SensorStateClass.MEASUREMENT),
    "pfb": _Meta("Fator de Potência Fase B", None, SensorDeviceClass.POWER_FACTOR, SensorStateClass.MEASUREMENT),
    "pfc": _Meta("Fator de Potência Fase C", None, SensorDeviceClass.POWER_FACTOR, SensorStateClass.MEASUREMENT),
    "pft": _Meta("Fator de Potência Total", None, SensorDeviceClass.POWER_FACTOR, SensorStateClass.MEASUREMENT),
    # Ângulos (graus) — ver observação acima sobre a interpretação destes campos
    "pga": _Meta("Ângulo do Fator de Potência Fase A", "°", None, SensorStateClass.MEASUREMENT, diagnostic=True),
    "pgb": _Meta("Ângulo do Fator de Potência Fase B", "°", None, SensorStateClass.MEASUREMENT, diagnostic=True),
    "pgc": _Meta("Ângulo do Fator de Potência Fase C", "°", None, SensorStateClass.MEASUREMENT, diagnostic=True),
    "yuaub": _Meta("Ângulo de Tensão Ua-Ub", "°", None, SensorStateClass.MEASUREMENT, diagnostic=True),
    "yuauc": _Meta("Ângulo de Tensão Ua-Uc", "°", None, SensorStateClass.MEASUREMENT, diagnostic=True),
    "yubuc": _Meta("Ângulo de Tensão Ub-Uc", "°", None, SensorStateClass.MEASUREMENT, diagnostic=True),
    # Frequência (Hz)
    "freq": _Meta("Frequência da Rede", UnitOfFrequency.HERTZ, SensorDeviceClass.FREQUENCY, SensorStateClass.MEASUREMENT),
    # Energia consumida (kWh) — acumulada, sempre crescente
    "epa_c": _Meta("Consumo Fase A", UnitOfEnergy.KILO_WATT_HOUR, SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING),
    "epb_c": _Meta("Consumo Fase B", UnitOfEnergy.KILO_WATT_HOUR, SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING),
    "epc_c": _Meta("Consumo Fase C", UnitOfEnergy.KILO_WATT_HOUR, SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING),
    "ept_c": _Meta("Consumo Total", UnitOfEnergy.KILO_WATT_HOUR, SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING),
    # Energia gerada (kWh) — acumulada, sempre crescente
    "epa_g": _Meta("Geração Fase A", UnitOfEnergy.KILO_WATT_HOUR, SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING),
    "epb_g": _Meta("Geração Fase B", UnitOfEnergy.KILO_WATT_HOUR, SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING),
    "epc_g": _Meta("Geração Fase C", UnitOfEnergy.KILO_WATT_HOUR, SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING),
    "ept_g": _Meta("Geração Total", UnitOfEnergy.KILO_WATT_HOUR, SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING),
    # Diagnóstico do equipamento
    "tpsd": _Meta("Temperatura Interna", UnitOfTemperature.CELSIUS, SensorDeviceClass.TEMPERATURE, SensorStateClass.MEASUREMENT, diagnostic=True),
    "rssi_wifi": _Meta("Sinal Wi-Fi", "dBm", SensorDeviceClass.SIGNAL_STRENGTH, SensorStateClass.MEASUREMENT, diagnostic=True),
}


def _build_description(key: str) -> SensorEntityDescription:
    """Monta a descrição do sensor: usa o mapa conhecido, ou um nome genérico."""
    meta = _KNOWN.get(key)
    if meta is None:
        return SensorEntityDescription(
            key=key,
            name=key.replace("_", " ").upper(),
            state_class=SensorStateClass.MEASUREMENT,
        )
    return SensorEntityDescription(
        key=key,
        name=meta.name,
        native_unit_of_measurement=meta.unit,
        device_class=meta.device_class,
        state_class=meta.state_class,
        entity_category=EntityCategory.DIAGNOSTIC if meta.diagnostic else None,
    )


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> None:
    """Cria os sensores conforme as chaves forem aparecendo nos dados do medidor."""
    coordinator: SM3WLiteCoordinator = hass.data[DOMAIN][entry.entry_id]

    known_keys: set[str] = set()

    @callback
    def _add_new_entities() -> None:
        if coordinator.data is None:
            return
        new_keys = set(coordinator.data) - known_keys
        if not new_keys:
            return
        known_keys.update(new_keys)
        async_add_entities(
            SM3WLiteSensor(coordinator, entry, _build_description(key))
            for key in new_keys
        )

    _add_new_entities()
    entry.async_on_unload(coordinator.async_add_listener(_add_new_entities))


class SM3WLiteSensor(CoordinatorEntity[SM3WLiteCoordinator], SensorEntity):
    """Uma única grandeza elétrica reportada pelo medidor."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: SM3WLiteCoordinator,
        entry: ConfigEntry,
        description: SensorEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="IE Tecnologia",
            model="SM-3W Lite",
        )

    @property
    def native_value(self):
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get(self.entity_description.key)
