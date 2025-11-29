# DINPLUG – Home Assistant Integration

Integração customizada do Home Assistant para controlar módulos de iluminação **DINPLUG** via Telnet (porta 23).

Esta integração permite controlar cargas individuais dos módulos DINPLUG como entidades `light`, incluindo:
- Luzes On/Off
- Dimmers (0–100%)
- Múltiplos módulos e múltiplos canais
- Atualizações em tempo real por telemetria `R:LOAD`

> 📌 Esta versão utiliza **Config Flow** para configuração da conexão e **YAML** para a configuração das luzes.

---

## 📦 Instalação

1. Baixe este repositório.
2. Copie a pasta:

`custom_components/dinplug`

para dentro do diretório de configuração do Home Assistant:

`/config/custom_components/dinplug`

A estrutura final deve ficar assim:

```
/config
└── custom_components
    └── dinplug
        ├── __init__.py
        ├── const.py
        ├── light.py
        ├── hub.py
        ├── config_flow.py
        └── manifest.json
```

3. Reinicie o Home Assistant.

---

## ⚙️ Configuração

### 1. Adicionar a Integração (via UI)

A conexão com o controlador DINPLUG é configurada pela interface do Home Assistant:

1. Vá para **Configurações > Dispositivos e Serviços**.
2. Clique em **Adicionar Integração** e procure por **"DINPLUG"**.
3. Insira o **endereço IP** e a **porta** do seu controlador.

O Home Assistant estabelecerá uma conexão única e centralizada que será usada para todas as luzes.

### 2. Configurar as Luzes (via YAML)

As luzes ainda são definidas no seu arquivo `configuration.yaml`:

```yaml
light:
  - platform: dinplug
    lights:
      - name: "Sala Teto"
        device: 104
        channel: 1
        dimmer: true

      - name: "Cozinha Spots"
        device: 107
        channel: 4
        dimmer: false
```

### Campos disponíveis
| Campo | Tipo | Obrigatório | Descrição |
| --- | --- | --- | --- |
| `lights` | lista | ✔ Sim | Lista de cargas |
| `device` | número | ✔ Sim | Endereço do módulo (ex: 104) |
| `channel` | número | ✔ Sim | Canal do módulo (1–n) |
| `name` | string | ✔ Sim | Nome da entidade no HA |
| `dimmer` | booleano | ✖ Não (true) | `true` = dimmer, `false` = on/off |

---

### 💡 Como funciona

A integração usa uma arquitetura de "hub":

1.  **Conexão Central (Hub):** O Home Assistant (via Config Flow) estabelece uma única conexão TCP com o controlador DINPLUG, gerenciada pela classe `M4Hub`.
2.  **Comandos e Telemetria:**
    *   **Envio:** As entidades `light` enviam comandos para o hub, que os encaminha para o controlador no formato `LOAD <device> <channel> <level>`.
    *   **Recebimento:** O hub escuta a telemetria `R:LOAD <device> <channel> <level>` e atualiza o estado da entidade correspondente em tempo real.
3.  **Disponibilidade:** O hub monitora a conexão e o status dos módulos com o comando `STA`, marcando as entidades como disponíveis ou indisponíveis.

Este modelo garante que apenas uma conexão seja usada, evitando conflitos e sobrecarga no controlador.

### 🔌 Exemplo completo

1.  **Configuração da Conexão (UI):**
    *   IP: `192.168.51.30`
    *   Porta: `23`

2.  **Configuração das Luzes (`configuration.yaml`):**
    ```yaml
    light:
      - platform: dinplug
        lights:
          - name: "Sala Teto"
            device: 104
            channel: 1
            dimmer: true

          - name: "Sala Arandela"
            device: 104
            channel: 2
            dimmer: false

          - name: "Spots Cozinha"
            device: 107
            channel: 4
            dimmer: true

          - name: "Corredor"
            device: 105
            channel: 3
            dimmer: false
    ```

---

### ✔️ Recursos suportados

- [x] Configuração da conexão via UI (Config Flow)
- [x] Controle ON/OFF
- [x] Controle de dimmer (brightness)
- [x] Atualização instantânea por telemetria
- [x] Sem polling
- [x] Múltiplos módulos e canais
- [x] Disponibilidade online/offline por módulo

### 🚧 Roadmap (próximas versões)

- [ ] Auto-descoberta de loads via `REFRESH`
- [ ] Suporte a Scenes (`SCN`)
- [ ] Suporte a Cortinas (`SHADE`)
- [ ] Suporte a HVAC
- [ ] Criação automática de `Devices` por módulo

---

### 🐞 Debug (opcional)

Para ativar logs detalhados da integração:

```yaml
logger:
  default: warning
  logs:
    custom_components.dinplug: debug
```
