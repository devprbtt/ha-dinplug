# DINPLUG Telnet - Home Assistant Integration (YAML)

Custom integration for Home Assistant to control **DINPLUG / M4** automation modules via Telnet (port 23).

This integration allows controlling individual channels from DINPLUG modules as `light`, `cover`, `climate`, and `sensor` entities, including:
- On/Off lights
- Dimmers (0–100%)
- Covers/shades (up, down, stop, set position)
- HVAC thermostats (set point, mode, fan speed)
- Button/keypad state sensors
- Real-time updates via telemetry (`R:LOAD`, `R:SHADE`, `R:HVAC`, `R:BTN`)
- Support for multiple hosts

> 📌 This is the **YAML-only** version (no Config Flow).
>
> Ideal for professional, simple, and direct setups.

---

## 📦 Installation

1.  Download this repository.
2.  Copy the `custom_components/dinplug` folder into your Home Assistant configuration directory:
    ```
    /config/custom_components/dinplug
    ```
    The final structure should look like this:
    ```
    /config
    └── custom_components
        └── dinplug
            ├── __init__.py
            ├── const.py
            ├── light.py
            ├── cover.py
            ├── climate.py
            ├── sensor.py
            └── manifest.json
    ```
3.  Restart Home Assistant.

---

## ⚙️ YAML Configuration

Add the `dinplug` platforms to your `configuration.yaml`. All platforms (`light`, `cover`, `climate`, `sensor`) share the same Telnet connection to the host.

### Example

```yaml
# Lights
light:
  - platform: dinplug
    host: 192.168.1.30
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

# Covers / Shades
cover:
  - platform: dinplug
    host: 192.168.1.30
    covers:
      - name: "Living Room Blind"
        device: 101
        channel: 1

# HVAC Thermostats
climate:
  - platform: dinplug
    host: 192.168.1.30
    hvacs:
      - name: "Living Room HVAC"
        device: 120
        min_temp: 16
        max_temp: 30

# Button/Keypad Sensors
sensor:
  - platform: dinplug
    host: 192.168.1.30
    buttons:
      - name: "Keypad 111 Button 1"
        device: 111
        button: 1
```

### 💡 How It Works

Home Assistant opens a single TCP connection to each DINPLUG controller and:

- **Sends commands:** `LOAD`, `SHADE`, `HVAC`
- **Receives telemetry:** `R:LOAD`, `R:SHADE`, `R:HVAC`, `R:BTN` for instant state updates.
- **Maintains connection:** Sends periodic `STA` commands and monitors `R:MODULE STATUS` for availability.

The integration is push-based—no polling.

---

## Converters

### CSV to YAML Converter

This repository includes a `csv-to-yaml.py` script (and a compiled `.exe` for Windows) to simplify YAML configuration.

The script reads a CSV file exported from the **Roehn Wizard** software and generates the corresponding `dinplug` YAML configuration for lights, covers, and other devices.

#### Usage

1.  **Export CSV:** In Roehn Wizard, export the device list for your project.
2.  **Run the script:**
    ```bash
    python csv-to-yaml.py your_exported_file.csv 192.168.1.30
    ```
    Replace `192.168.1.30` with your DINPLUG controller's IP address.
3.  **Copy the output:** The script will print the YAML configuration to the console. Copy and paste it into your `configuration.yaml`.

---

## 🐞 Debugging

To enable detailed logs for the integration, add the following to `configuration.yaml`:

```yaml
logger:
  default: warning
  logs:
    custom_components.dinplug: debug
```

---
---

# (Português)

## M4 DINPLUG – Integração Home Assistant (YAML)

Integração customizada do Home Assistant para controlar módulos de automação **M4 / DINPLUG** via Telnet (porta 23).

Esta integração permite controlar canais individuais dos módulos DINPLUG como entidades `light`, `cover`, `climate` e `sensor`, incluindo:
- Luzes On/Off
- Dimmers (0–100%)
- Cortinas/persianas (abrir, fechar, parar, definir posição)
- Termostatos de Ar Condicionado (set point, modo, ventilação)
- Sensores de estado de botões/teclas
- Atualizações em tempo real por telemetria (`R:LOAD`, `R:SHADE`, `R:HVAC`, `R:BTN`)
- Suporte a múltiplos hosts

> 📌 Esta é a versão baseada em **YAML** (sem Config Flow).
>
> Ideal para instalações profissionais, simples e diretas.

---

## 📦 Instalação

1.  Baixe este repositório.
2.  Copie a pasta `custom_components/dinplug` para dentro do diretório de configuração do seu Home Assistant:
    ```
    /config/custom_components/dinplug
    ```
    A estrutura final deve ficar assim:
    ```
    /config
    └── custom_components
        └── dinplug
            ├── __init__.py
            ├── const.py
            ├── light.py
            ├── cover.py
            ├── climate.py
            ├── sensor.py
            └── manifest.json
    ```
3.  Reinicie o Home Assistant.

---

## ⚙️ Configuração via YAML

Adicione as plataformas `dinplug` ao seu `configuration.yaml`. Todas as plataformas (`light`, `cover`, `climate`, `sensor`) compartilham a mesma conexão Telnet com o host.

### Exemplo

```yaml
# Luzes
light:
  - platform: dinplug
    host: 192.168.1.30
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

# Cortinas / Persianas
cover:
  - platform: dinplug
    host: 192.168.1.30
    covers:
      - name: "Sala Persiana"
        device: 101
        channel: 1

# Termostatos de Ar Condicionado
climate:
  - platform: dinplug
    host: 192.168.1.30
    hvacs:
      - name: "Sala HVAC"
        device: 120
        min_temp: 16
        max_temp: 30

# Sensores de Botões/Teclas
sensor:
  - platform: dinplug
    host: 192.168.1.30
    buttons:
      - name: "Teclado 111 Botão 1"
        device: 111
        button: 1
```

### 💡 Como funciona

O Home Assistant abre uma única conexão TCP com cada controlador DINPLUG e:

- **Envia comandos:** `LOAD`, `SHADE`, `HVAC`
- **Recebe telemetria:** `R:LOAD`, `R:SHADE`, `R:HVAC`, `R:BTN` para atualizações de estado instantâneas.
- **Mantém a conexão:** Envia comandos `STA` periodicamente e monitora `R:MODULE STATUS` para disponibilidade.

A integração é baseada em *push* — sem *polling*.

---

## Conversores ##

### Conversor CSV para YAML

Este repositório inclui o script `csv-to-yaml.py` (e um executável `.exe` para Windows) para simplificar a configuração YAML.

O script lê um arquivo CSV exportado do software **Roehn Wizard** e gera a configuração YAML correspondente para luzes, cortinas e outros dispositivos `dinplug`.

#### Como usar

1.  **Exporte o CSV:** No Roehn Wizard, exporte a lista de dispositivos do seu projeto.
2.  **Execute o script:**
    ```bash
    python csv-to-yaml.py seu_arquivo_exportado.csv 192.168.1.30
    ```
    Substitua `192.168.1.30` pelo endereço IP do seu controlador DINPLUG.
3.  **Copie o resultado:** O script irá imprimir a configuração YAML no console. Copie e cole no seu `configuration.yaml`.

---

## 🐞 Debug

Para ativar logs detalhados da integração, adicione o seguinte ao `configuration.yaml`:

```yaml
logger:
  default: warning
  logs:
    custom_components.dinplug: debug
```
