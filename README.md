# M4 DINPLUG – Home Assistant Integration (YAML)

Integração customizada do Home Assistant para controlar módulos de iluminação **M4 / DINPLUG** via Telnet (porta 23).

Esta integração permite controlar cargas individuais dos módulos M4 como entidades `light`, incluindo:
- Luzes On/Off  
- Dimmers (0–100%)  
- Múltiplos módulos e múltiplos canais  
- Atualizações em tempo real por telemetria `R:LOAD`

> 📌 Esta é a versão baseada em **YAML** (sem Config Flow).
>  
> Ideal para instalações profissionais, simples e diretas.

---

## 📦 Instalação

1. Baixe este repositório.
2. Copie a pasta:



custom_components/dinplug


para dentro do diretório de configuração do Home Assistant:



/config/custom_components/dinplug


A estrutura final deve ficar assim:



/config
└── custom_components
└── dinplug
├── init.py
├── const.py
├── light.py
└── manifest.json


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
### Campos disponíveis
| Campo | Tipo | Obrigatório | Descrição |
| --- | --- | --- | --- |
| `host` | string | ✔ Sim | IP do controlador DINPLUG |
| `port` | número | ✖ Não (23) | Porta Telnet |
| `lights` | lista | ✔ Sim | Lista de cargas |
| `device` | número | ✔ Sim | Endereço do módulo (ex: 104) |
| `channel` | número | ✔ Sim | Canal do módulo (1–n) |
| `name` | string | ✔ Sim | Nome da entidade no HA |
| `dimmer` | booleano | ✖ Não (true) | `TRUE` = dimmer, `FALSE` = on/off |

### 💡 Como funciona

O Home Assistant abre uma conexão TCP com o controlador M4 e:

**Envia comandos:**

`LOAD <device> <channel> <level>`

- `level = 0` → OFF
- `level = 1–100` → dimmer
- `level = 100` → ON

**Recebe telemetria:**

`R:LOAD <device> <channel> <level>`
Atualiza o estado instantaneamente no HA.

**Mantém conexão viva:**

- Envia `STA` periodicamente
- Monitora `R:MODULE STATUS` para disponibilidade

Tudo é push-based — sem polling.

### 🔌 Exemplo completo
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

- [x] Controle ON/OFF
- [x] Controle de dimmer (brightness)
- [x] Atualização instantânea por telemetria
- [x] Sem polling
- [x] Múltiplos módulos e canais
- [x] Disponibilidade online/offline por módulo

### 🚧 Roadmap (próximas versões)

- [ ] Auto-descoberta de loads via `REFRESH`
- [ ] Configuração via UI (Config Flow)
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
