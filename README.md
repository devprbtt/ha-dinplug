# DINPLUG - Home Assistant Integration (YAML)

This custom integration for Home Assistant allows you to control **DINPLUG** modules via Telnet (port 23).

It supports the following platforms:
- `light`: For On/Off lights and dimmers.
- `cover`: For shades and blinds.
- `climate`: For HVAC systems.
- `sensor`: To monitor keypad button presses.

> 📌 This is the **YAML-based** version (no Config Flow). Ideal for simple, direct, and professional installations.

---

## ⚠️ Breaking Change (Version 0.2.0)

The YAML configuration format has been updated to support multiple platforms under a single host. If you are upgrading from a previous version, you **must** update your `configuration.yaml` file.

**Old format:**
```yaml
light:
  - platform: dinplug
    host: 192.168.51.30
    # ...
```

**New format:**
```yaml
dinplug:
  - host: 192.168.51.30
    lights:
      # ...
    shades:
      # ...
```

---

## 📦 Installation

1.  Download this repository.
2.  Copy the folder `custom_components/dinplug` into your Home Assistant configuration directory (`/config`).
3.  Restart Home Assistant.

The final structure should look like this:
```
/config
└── custom_components
    └── dinplug
        ├── __init__.py
        ├── hub.py
        ├── light.py
        ├── cover.py
        ├── climate.py
        ├── sensor.py
        └── manifest.json
```

---

## ⚙️ Configuration (YAML)

Add the `dinplug` integration to your `configuration.yaml` file. All platforms (light, cover, climate, sensor) are configured under the same host.

```yaml
dinplug:
  - host: 192.168.51.30
    port: 23
    lights:
      - name: "Living Room Ceiling"
        device: 104
        channel: 1
        dimmer: true
    shades:
      - name: "Living Room Shade"
        device: 201
        channel: 1
    hvacs:
      - name: "Main HVAC"
        device: 301
    buttons:
      - name: "Keypad Button 1"
        device: 401
        channel: 1
```

### Light Configuration
| Field     | Type    | Required      | Description                          |
|-----------|---------|---------------|--------------------------------------|
| `host`    | string  | ✔ Yes         | IP address of the DINPLUG controller |
| `port`    | number  | ✖ No (23)     | Telnet port                          |
| `lights`  | list    | ✔ Yes         | List of loads                        |
| `device`  | number  | ✔ Yes         | Module address (e.g., 104)           |
| `channel` | number  | ✔ Yes         | Module channel (1–n)                 |
| `name`    | string  | ✔ Yes         | Entity name in Home Assistant        |
| `dimmer`  | boolean | ✖ No (true)   | `true` = dimmer, `false` = on/off    |

### Cover (Shade) Configuration
| Field     | Type    | Required      | Description                          |
|-----------|---------|---------------|--------------------------------------|
| `shades`  | list    | ✔ Yes         | List of shades                       |
| `device`  | number  | ✔ Yes         | Module address                       |
| `channel` | number  | ✔ Yes         | Module channel                       |
| `name`    | string  | ✔ Yes         | Entity name in Home Assistant        |

### Climate (HVAC) Configuration
| Field     | Type    | Required      | Description                          |
|-----------|---------|---------------|--------------------------------------|
| `hvacs`   | list    | ✔ Yes         | List of HVAC units                   |
| `device`  | number  | ✔ Yes         | Module address                       |
| `name`    | string  | ✔ Yes         | Entity name in Home Assistant        |

### Sensor (Button) Configuration
| Field     | Type    | Required      | Description                          |
|-----------|---------|---------------|--------------------------------------|
| `buttons` | list    | ✔ Yes         | List of keypad buttons to monitor    |
| `device`  | number  | ✔ Yes         | Keypad address                       |
| `channel` | number  | ✔ Yes         | Button number                        |
| `name`    | string  | ✔ Yes         | Entity name in Home Assistant        |

---

### ✔️ Supported Features

- [x] Light: ON/OFF and dimmer control
- [x] Cover: Open, close, stop, and set position
- [x] Climate: Mode, temperature, and fan control
- [x] Sensor: Real-time button state (`press`, `release`, `hold`, `double`)
- [x] Instant status updates via telemetry
- [x] No polling

---

### 🐞 Debugging

To enable detailed logs, add this to `configuration.yaml`:
```yaml
logger:
  default: warning
  logs:
    custom_components.dinplug: debug
```

---
---

# DINPLUG – Integração Home Assistant (YAML)

Integração customizada do Home Assistant para controlar módulos **DINPLUG** via Telnet (porta 23).

Suporta as seguintes plataformas:
- `light`: Luzes On/Off e dimmers.
- `cover`: Cortinas e persianas.
- `climate`: Sistemas de ar condicionado (HVAC).
- `sensor`: Monitoramento de botões de keypads.

> 📌 Esta é a versão baseada em **YAML** (sem Config Flow). Ideal para instalações profissionais, simples e diretas.

---

## ⚠️ Breaking Change (Versão 0.2.0)

O formato de configuração YAML foi atualizado para suportar múltiplas plataformas sob um único host. Se você está atualizando de uma versão anterior, **precisa** atualizar seu arquivo `configuration.yaml`.

**Formato antigo:**
```yaml
light:
  - platform: dinplug
    host: 192.168.51.30
    # ...
```

**Novo formato:**
```yaml
dinplug:
  - host: 192.168.51.30
    lights:
      # ...
    shades:
      # ...
```

---

## 📦 Instalação

1.  Baixe este repositório.
2.  Copie a pasta `custom_components/dinplug` para o diretório de configuração do seu Home Assistant (`/config`).
3.  Reinicie o Home Assistant.

A estrutura final deve ficar assim:
```
/config
└── custom_components
    └── dinplug
        ├── __init__.py
        ├── hub.py
        ├── light.py
        ├── cover.py
        ├── climate.py
        ├── sensor.py
        └── manifest.json
```

---

## ⚙️ Configuração via YAML

Adicione a integração `dinplug` ao seu arquivo `configuration.yaml`. Todas as plataformas (light, cover, climate, sensor) são configuradas sob o mesmo host.

```yaml
dinplug:
  - host: 192.168.51.30
    port: 23
    lights:
      - name: "Sala Teto"
        device: 104
        channel: 1
        dimmer: true
    shades:
      - name: "Cortina Sala"
        device: 201
        channel: 1
    hvacs:
      - name: "AC Principal"
        device: 301
    buttons:
      - name: "Botão Keypad 1"
        device: 401
        channel: 1
```

### Configuração de Luzes (Light)
| Campo     | Tipo     | Obrigatório   | Descrição                           |
|-----------|----------|---------------|-------------------------------------|
| `host`    | string   | ✔ Sim         | IP do controlador DINPLUG           |
| `port`    | número   | ✖ Não (23)    | Porta Telnet                        |
| `lights`  | lista    | ✔ Sim         | Lista de cargas                     |
| `device`  | número   | ✔ Sim         | Endereço do módulo (ex: 104)        |
| `channel` | número   | ✔ Sim         | Canal do módulo (1–n)               |
| `name`    | string   | ✔ Sim         | Nome da entidade no HA              |
| `dimmer`  | booleano | ✖ Não (true)  | `true` = dimmer, `false` = on/off   |

### Configuração de Cortinas (Cover)
| Campo     | Tipo     | Obrigatório   | Descrição                           |
|-----------|----------|---------------|-------------------------------------|
| `shades`  | lista    | ✔ Sim         | Lista de cortinas                   |
| `device`  | número   | ✔ Sim         | Endereço do módulo                  |
| `channel` | número   | ✔ Sim         | Canal do módulo                     |
| `name`    | string   | ✔ Sim         | Nome da entidade no HA              |

### Configuração de Ar Condicionado (Climate)
| Campo     | Tipo     | Obrigatório   | Descrição                           |
|-----------|----------|---------------|-------------------------------------|
| `hvacs`   | lista    | ✔ Sim         | Lista de equipamentos de AC         |
| `device`  | número   | ✔ Sim         | Endereço do módulo                  |
| `name`    | string   | ✔ Sim         | Nome da entidade no HA              |

### Configuração de Sensores (Button)
| Campo     | Tipo     | Obrigatório   | Descrição                           |
|-----------|----------|---------------|-------------------------------------|
| `buttons` | lista    | ✔ Sim         | Lista de botões de keypad           |
| `device`  | número   | ✔ Sim         | Endereço do keypad                  |
| `channel` | número   | ✔ Sim         | Número do botão                     |
| `name`    | string   | ✔ Sim         | Nome da entidade no HA              |

---

### ✔️ Recursos Suportados

- [x] Light: Controle ON/OFF e dimmer
- [x] Cover: Abrir, fechar, parar e definir posição
- [x] Climate: Controle de modo, temperatura e ventilação
- [x] Sensor: Estado do botão em tempo real (`press`, `release`, `hold`, `double`)
- [x] Atualização de status instantânea por telemetria
- [x] Sem polling

---

### 🐞 Debug

Para ativar logs detalhados, adicione ao `configuration.yaml`:
```yaml
logger:
  default: warning
  logs:
    custom_components.dinplug: debug
```
