# DINPLUG Lighting (YAML)

Integração customizada do Home Assistant para controlar módulos de iluminação DINPLUG via Telnet (porta 23).

## Instalação

1. Copie a pasta `custom_components/dinplug` deste repositório para a pasta
   `custom_components` da configuração do seu Home Assistant. Fica assim:

   ```text
   /config/
     custom_components/
       dinplug/
         __init__.py
         const.py
         light.py
         manifest.json
