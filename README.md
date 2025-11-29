# DINPLUG - Home Assistant Integration (YAML)

This custom integration for Home Assistant allows you to control **DINPLUG** lighting modules via Telnet (port 23).

It enables the control of individual loads from DINPLUG modules as `light` entities, including:
- On/Off lights
- Dimmers (0–100%)
- Multiple modules and channels
- Real-time status updates via `R:LOAD` telemetry

> 📌 This is the **YAML-based** version (no Config Flow). Ideal for simple, direct, and professional installations.

---

## 📦 Installation

1. Download this repository.
2. Copy the folder:

`custom_components/dinplug`

into your Home Assistant configuration directory:

`/config/custom_components/dinplug`

The final structure should look like this:

```
/config
└── custom_components
    └── dinplug
        ├── __init__.py
        ├── const.py
        ├── light.py
        └── manifest.json
```

3. Restart Home Assistant.

---

## ⚙️ Configuration (YAML)

Add the following to your `configuration.yaml` file:

```yaml
light:
  - platform: dinplug
    host: 192.168.51.30
    port: 23
    lights:
      - name: "Living Room Ceiling"
        device: 104
        channel: 1
        dimmer: true

      - name: "Kitchen Spots"
        device: 107
        channel: 4
        dimmer: false
```

### Available Fields
| Field     | Type    | Required      | Description                          |
|-----------|---------|---------------|--------------------------------------|
| `host`    | string  | ✔ Yes         | IP address of the DINPLUG controller |
| `port`    | number  | ✖ No (23)     | Telnet port                          |
| `lights`  | list    | ✔ Yes         | List of loads                        |
| `device`  | number  | ✔ Yes         | Module address (e.g., 104)           |
| `channel` | number  | ✔ Yes         | Module channel (1–n)                 |
| `name`    | string  | ✔ Yes         | Entity name in Home Assistant        |
| `dimmer`  | boolean | ✖ No (true)   | `true` = dimmer, `false` = on/off    |

---

## 🛠️ CSV to YAML Converter Tool

For installations with many lights, this repository includes a utility to quickly generate the YAML configuration from a CSV file.

### How to Use

1.  **Run the script:**
    *   If you have Python installed, run `python csv-to-yaml.py`.
    *   On Windows, you can use the executable: `csv-to-yaml.exe`.

2.  **Prepare the CSV file:**
    The CSV file must have the following columns: `Entity`, `Address`, `Button Type`, and `Label`.
    *   `Entity`: Use `Switch` for on/off lights or `Dimmer` for dimmable lights.
    *   `Address`: The module and channel in the format `device:channel` (e.g., `104:1`).
    *   `Button Type`: Use `Dimmer` to set the light as dimmable. Any other value will result in a standard on/off switch.
    *   `Label`: The desired name for the light.

    **Example `lights.csv`:**
    ```csv
    Entity,Label,Address,Button Type
    Dimmer,"Living Room Ceiling",104:1,Dimmer
    Switch,"Kitchen Spots",107:4,Rocker Switch
    Dimmer,"Bedroom Lamp",104:2,Dimmer
    ```

3.  **Generate the YAML:**
    *   Open the tool, select your CSV file, enter the controller's IP address, and click "Convert to YAML".
    *   You can then copy the generated configuration to your clipboard or save it as a `.yaml` file.

---

### 💡 How It Works

Home Assistant establishes a TCP connection with the DINPLUG controller and:

**Sends commands:**
`LOAD <device> <channel> <level>`
- `level = 0` → OFF
- `level = 1–100` → dimmer
- `level = 100` → ON

**Receives telemetry:**
`R:LOAD <device> <channel> <level>`
This instantly updates the entity's state in Home Assistant.

**Maintains connection:**
- Periodically sends `STA` to keep the connection alive.
- Monitors `R:MODULE STATUS` for availability.

Everything is push-based—no polling.

---

### ✔️ Supported Features

- [x] ON/OFF control
- [x] Dimmer control (brightness)
- [x] Instant status updates via telemetry
- [x] No polling
- [x] Multiple modules and channels
- [x] Online/offline availability per module

### 🚧 Roadmap (Future Releases)

- [ ] Auto-discovery of loads via `REFRESH`
- [ ] UI-based configuration (Config Flow)
- [ ] Scene support (`SCN`)
- [ ] Shade support (`SHADE`)
- [ ] HVAC support
- [ ] Automatic `Device` creation per module

---

### 🐞 Debugging (Optional)

To enable detailed logs for the integration, add this to your `configuration.yaml`:

```yaml
logger:
  default: warning
  logs:
    custom_components.dinplug: debug
```

---
---

# DINPLUG – Integração Home Assistant (YAML)

Integração customizada do Home Assistant para controlar módulos de iluminação **DINPLUG** via Telnet (porta 23).

Esta integração permite controlar cargas individuais dos módulos DINPLUG como entidades `light`, incluindo:
- Luzes On/Off
- Dimmers (0–100%)
- Múltiplos módulos e múltiplos canais
- Atualizações em tempo real por telemetria `R:LOAD`

> 📌 Esta é a versão baseada em **YAML** (sem Config Flow). Ideal para instalações profissionais, simples e diretas.

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
        └── manifest.json
```

3. Reinicie o Home Assistant.

---

## ⚙️ Configuração via YAML

Adicione ao `configuration.yaml`:

```yaml
light:
  - platform: dinplug
    host: 192.168.51.30
    port: 23
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

### Campos Disponíveis
| Campo    | Tipo      | Obrigatório | Descrição                           |
|----------|-----------|-------------|-------------------------------------|
| `host`   | string    | ✔ Sim       | IP do controlador DINPLUG           |
| `port`   | número    | ✖ Não (23)  | Porta Telnet                        |
| `lights` | lista     | ✔ Sim       | Lista de cargas                     |
| `device` | número    | ✔ Sim       | Endereço do módulo (ex: 104)        |
| `channel`| número    | ✔ Sim       | Canal do módulo (1–n)               |
| `name`   | string    | ✔ Sim       | Nome da entidade no HA              |
| `dimmer` | booleano  | ✖ Não (true)| `true` = dimmer, `false` = on/off   |

---

## 🛠️ Ferramenta Conversora CSV para YAML

Para instalações com muitas luzes, este repositório inclui um utilitário para gerar rapidamente a configuração YAML a partir de um arquivo CSV.

### Como Usar

1.  **Execute o script:**
    *   Se você tem Python instalado, execute `python csv-to-yaml.py`.
    *   No Windows, você pode usar o executável: `csv-to-yaml.exe`.

2.  **Prepare o arquivo CSV:**
    O arquivo CSV deve ter as seguintes colunas: `Entity`, `Address`, `Button Type`, e `Label`.
    *   `Entity`: Use `Switch` para luzes on/off ou `Dimmer` para luzes dimerizáveis.
    *   `Address`: O módulo e o canal no formato `device:channel` (ex: `104:1`).
    *   `Button Type`: Use `Dimmer` para definir a luz como dimerizável. Qualquer outro valor resultará em uma luz on/off.
    *   `Label`: O nome desejado para a luz.

    **Exemplo `luzes.csv`:**
    ```csv
    Entity,Label,Address,Button Type
    Dimmer,"Sala Teto",104:1,Dimmer
    Switch,"Spots Cozinha",107:4,Rocker Switch
    Dimmer,"Luz Quarto",104:2,Dimmer
    ```

3.  **Gere o YAML:**
    *   Abra a ferramenta, selecione seu arquivo CSV, insira o endereço IP do controlador e clique em "Convert to YAML".
    *   Você pode copiar a configuração gerada ou salvá-la em um arquivo `.yaml`.

---

### 💡 Como Funciona

O Home Assistant abre uma conexão TCP com o controlador DINPLUG e:

**Envia comandos:**
`LOAD <device> <channel> <level>`
- `level = 0` → OFF
- `level = 1–100` → dimmer
- `level = 100` → ON

**Recebe telemetria:**
`R:LOAD <device> <channel> <level>`
Atualiza o estado instantaneamente no HA.

**Mantém a conexão:**
- Envia `STA` periodicamente para manter a conexão ativa.
- Monitora `R:MODULE STATUS` para disponibilidade.

Tudo é push-based — sem polling.

---

### ✔️ Recursos Suportados

- [x] Controle ON/OFF
- [x] Controle de dimmer (brightness)
- [x] Atualização instantânea por telemetria
- [x] Sem polling
- [x] Múltiplos módulos e canais
- [x] Disponibilidade online/offline por módulo

### 🚧 Roadmap (Próximas Versões)

- [ ] Auto-descoberta de loads via `REFRESH`
- [ ] Configuração via UI (Config Flow)
- [ ] Suporte a Scenes (`SCN`)
- [ ] Suporte a Cortinas (`SHADE`)
- [ ] Suporte a HVAC
- [ ] Criação automática de `Devices` por módulo

---

### 🐞 Debug (Opcional)

Para ativar logs detalhados da integração, adicione ao `configuration.yaml`:

```yaml
logger:
  default: warning
  logs:
    custom_components.dinplug: debug
```
