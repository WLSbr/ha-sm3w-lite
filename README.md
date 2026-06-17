# SM-3W Lite (IE Tecnologia) para Home Assistant

Integração customizada e **não-oficial** (não afiliada à IE Tecnologia) para o
medidor de energia trifásico Wi-Fi **SM-3W Lite**, recebendo os dados via
**MQTT** — exatamente o método que o próprio medidor já usa para publicar.

Diferente de configurar manualmente sensores MQTT no `configuration.yaml`,
esta integração:

- Tem uma tela de configuração (Configurações → Dispositivos e Serviços →
  Adicionar Integração): você só informa o tópico MQTT e um nome.
- Cria **todos os sensores automaticamente**, a partir do que o medidor
  realmente está enviando (potência, corrente, tensão, fator de potência,
  energia consumida/gerada por fase e total, frequência, temperatura interna
  e sinal de Wi-Fi).
- Suporta **múltiplos medidores**: basta repetir "Adicionar Integração" uma
  vez para cada medidor, cada um com seu próprio tópico.
- Pode ser instalada por **qualquer pessoa** que tenha um medidor desses,
  sem precisar editar YAML.

## Pré-requisitos

- A integração **MQTT** do Home Assistant já configurada e funcionando
  (você já precisa disso para o medidor publicar os dados).
- O medidor já configurado para publicar em um tópico MQTT (isso é feito na
  interface web do próprio equipamento, na aba de configuração de
  transmissão).

## Instalação

### Opção A — Manual

1. Copie a pasta `custom_components/sm3w_lite` deste pacote para dentro da
   pasta `config/custom_components/` da sua instalação do Home Assistant
   (crie a pasta `custom_components` se ela não existir).
2. Reinicie o Home Assistant.
3. Vá em **Configurações → Dispositivos e Serviços → Adicionar Integração**,
   procure por **"SM-3W Lite"**.
4. Informe o tópico MQTT do medidor (ex.: `/api/energia/medidor`) e um nome
   (ex.: "Medidor Casa"). O Home Assistant vai escutar o tópico por alguns
   segundos para confirmar que está recebendo dados.
5. Repita o passo 3-4 para cada medidor adicional, usando o tópico de cada
   um.

### Opção B — Via HACS (depois de publicar no GitHub)

Para que **outras pessoas** instalem isso facilmente:

1. Crie um repositório no GitHub e suba todo o conteúdo desta pasta
   (`ha-sm3w-lite`) para lá — ele já está estruturado do jeito que o HACS
   espera (`custom_components/sm3w_lite/...` na raiz, mais o `hacs.json`).
2. Antes de publicar, edite o `manifest.json` e troque
   `"@seu-usuario-github"` e as URLs `seu-usuario-github` pelo seu usuário
   real do GitHub.
3. No Home Assistant, com o HACS instalado: **HACS → menu (⋮) → Repositórios
   personalizados** → cole a URL do seu repositório → categoria
   **Integração**.
4. Quem adicionar esse repositório custom no HACS vai conseguir instalar a
   integração pela interface, sem editar nada manualmente, e depois seguir
   os mesmos passos 3-4 da Opção A para adicionar seus medidores.

## Como descobrir o tópico MQTT do seu medidor

Se você ainda não sabe o tópico exato:

1. Vá em **Configurações → Dispositivos e Serviços → MQTT → Configurar →
   Ouvir um tópico**.
2. Digite `#` no campo e clique em "Começar a ouvir".
3. Espere o medidor publicar (geralmente a cada poucos segundos) e anote o
   nome do tópico que aparecer.

## Sensores criados

A maioria dos campos é criada automaticamente com nome, unidade e tipo
corretos (potência em W, corrente em A, tensão em V, energia em kWh, etc.).
Os campos `pga/pgb/pgc` (ângulo do fator de potência) e `yuaub/yuauc/yubuc`
(ângulo entre tensões de fase) não são documentados publicamente pelo
fabricante — a interpretação usada aqui é a mais coerente com os valores
observados, mas pode ser ajustada no arquivo `sensor.py` se você descobrir o
significado exato.

Se o seu medidor não enviar algum campo (por exemplo, os de geração, caso
não seja usado em modo bidirecional), o sensor correspondente simplesmente
não é criado.

## Limitações conhecidas

- A integração depende inteiramente do medidor estar publicando no tópico
  configurado; se o medidor ficar off-line, os sensores ficam
  "indisponíveis" até a próxima mensagem chegar.
- Não há suporte (ainda) para ler o histórico de meses anteriores guardado
  na memória interna do medidor — apenas os valores "ao vivo" publicados via
  MQTT.

## Aviso

Este é um projeto da comunidade, não tem qualquer vínculo, patrocínio ou
endosso da IE Tecnologia Ltda.
