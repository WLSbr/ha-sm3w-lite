"""Constantes da integração SM-3W Lite (via MQTT)."""

DOMAIN = "sm3w_lite"

CONF_TOPIC = "topic"

DEFAULT_NAME = "Medidor de Energia SM-3W Lite"

# Tempo (em segundos) que a tela de configuração espera por uma primeira
# mensagem no tópico informado, só para confirmar que está tudo certo
# antes de criar a entrada de configuração.
LISTEN_TIMEOUT = 8
