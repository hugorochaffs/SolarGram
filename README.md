# Monitoramento Local APsystems & Relatórios Diários no Telegram

Este projeto realiza a leitura local (via TCP socket puro na porta 8899) da sua unidade **APsystems ECU** (ECU-R, ECU-R-PRO, ECU-B ou ECU-C) sem depender da nuvem da APsystems nem de estruturas pesadas como o Home Assistant.

O sistema roda em segundo plano, monitorando o sistema solar, registrando os picos de geração diários (do sistema, de cada microinversor e de cada painel/módulo fotovoltaico) e enviando um **relatório completo diariamente às 18:00 no Telegram**. Caso ocorra qualquer falha de comunicação com a ECU, um alerta imediato também é enviado ao Telegram.

---

## 📋 Funcionalidades

- **Monitoramento em Tempo Real:** Leitura direta da ECU via protocolo local em socket TCP.
- **Rastreamento de Picos:** Registra a potência máxima atingida no dia pelo sistema, por cada microinversor e por cada módulo fotovoltaico individual.
- **Relatório Diário no Telegram (18:00):**
  - Geração de energia do dia (`kWh`)
  - Geração acumulada total (`kWh`)
  - Pico de potência do sistema no dia (`W` e o horário em que ocorreu)
  - Quantidade de microinversores online/offline
  - Status individual de cada microinversor (Frequência `Hz`, Temperatura `°C`, Sinal, Potência Atual e Pico do Dia)
  - Status de cada módulo fotovoltaico/canal (Potência Atual `W`, Tensão `V` e Pico do Dia)
- **Notificação de Falha & Recuperação:** Emite alerta se a ECU ficar inacessível e avisa quando a conexão for reestabelecida.
- **Zero Dependências Pesadas:** Desenvolvido em Python 3 puro (utiliza apenas bibliotecas nativas da linguagem).

---

## 🛠️ Arquivos do Projeto

- `main.py`: Ponto de entrada do serviço continuado e tratamento de comandos CLI.
- `ecu_client.py`: Comunicação TCP com a ECU e decodificação do protocolo binário.
- `stats_tracker.py`: Gerenciamento e persistência dos picos diários no arquivo `daily_stats.json`.
- `telegram_notifier.py`: Formatação HTML e envio de mensagens para a API do Telegram Bot.
- `.env`: Arquivo de configuração das credenciais e parâmetros locais.
- `.env.example`: Modelo do arquivo de configuração.
- `apsystems-monitor.service`: Arquivo de unidade para instalação do serviço no Linux (`systemd`).

---

## ⚙️ Configuração (`.env`)

Copie o arquivo de exemplo `.env.example` ou edite diretamente o arquivo `.env`:

```env
# ==========================================
# Configurações da ECU APsystems
# ==========================================
ECU_IP=192.168.xx.xx
ECU_PORT=8899
ECU_ID=xxxxxxxxx
POLL_INTERVAL_SECONDS=120
REPORT_TIME=18:00

# ==========================================
# Configurações do Bot do Telegram
# ==========================================
TELEGRAM_BOT_TOKEN=123456789:ABCdefGhIJKlmNoPQRstuVWXyz
TELEGRAM_CHAT_ID=12345678
TELEGRAM_ALERT_ON_FAILURE=true
ALERT_COOLDOWN_MINUTES=60
```

### Como obter o Token e Chat ID do Telegram:
1. **Bot Token:** Abra o Telegram e converse com o [@BotFather](https://t.me/BotFather). Envie `/newbot`, escolha um nome e usuário e copie o token gerado.
2. **Chat ID:** Abra seu bot recém-criado, clique em `Start` e envie uma mensagem. Em seguida, busque pelo seu Chat ID usando o [@userinfobot](https://t.me/userinfobot) ou [@raw_data_bot](https://t.me/raw_data_bot).

---

## 🧪 Como Testar Manualmente

Você pode executar testes específicos pelo terminal usando as flags do `main.py`:

1. **Testar comunicação com a ECU local:**
   ```bash
   python3 main.py --test-ecu
   ```

2. **Testar envio de mensagem para o Telegram:**
   ```bash
   python3 main.py --test-telegram
   ```

3. **Gerar e enviar o Relatório Diário imediatamente (sem esperar as 18:00):**
   ```bash
   python3 main.py --test-report
   ```

---

## 📦 Instalação como Serviço no Linux (`systemd`)

Para garantir que o monitoramento seja executado em segundo plano e inicie automaticamente na inicialização do sistema, instale o serviço no `systemd`:

1. **Copie o arquivo de serviço para o diretório do systemd:**
   ```bash
   sudo cp apsystems-monitor.service /etc/systemd/system/
   ```

2. **Recarregue as configurações do systemd:**
   ```bash
   sudo systemctl daemon-reload
   ```

3. **Habilite o serviço para iniciar com o sistema:**
   ```bash
   sudo systemctl enable apsystems-monitor.service
   ```

4. **Inicie o serviço imediatamente:**
   ```bash
   sudo systemctl start apsystems-monitor.service
   ```

5. **Verifique o status do serviço:**
   ```bash
   sudo systemctl status apsystems-monitor.service
   ```

6. **Para visualizar os logs em tempo real:**
   ```bash
   journalctl -u apsystems-monitor.service -f
   ```

---

## 📝 Exemplo de Relatório Recebido no Telegram

```html
☀️ RELATÓRIO DIÁRIO DE GERAÇÃO SOLAR
📅 Data: 12/08/2026 às 18:00
📍 ECU ID: xxxxxxxx

📊 RESUMO GERAL DE GERAÇÃO:
• ⚡ Geração Hoje: 34,13 kWh
• 📈 Total Acumulado: 3.921,76 kWh
• 🔥 Pico do Sistema: 3.250 W (às 12:42:10)
• 🔌 Status Inversores: 5 / 8 Online

🛠️ STATUS DOS MICROINVERSORES E MÓDULOS:

🟢 Microinversor xxxxxxxx
  • Sinal: 1/5 | Freq: 60.0 Hz | Temp: 36°C
  • Potência Atual: 35 W | Pico Hoje: 540 W (12:40:15)
  • Módulos Fotovoltaicos (Canais):
    ▫️ Módulo 1: 18 W @ 206 V | Pico: 275 W
    ▫️ Módulo 2: 17 W @ 206 V | Pico: 265 W

🟢 Microinversor xxxxxxxxx
  • Sinal: 3/5 | Freq: 60.1 Hz | Temp: 36°C
  • Potência Atual: 50 W | Pico Hoje: 1180 W (12:42:10)
  • Módulos Fotovoltaicos (Canais):
    ▫️ Módulo 1: 13 W @ 204 V | Pico: 295 W
    ▫️ Módulo 2: 12 W @ 204 V | Pico: 295 W
    ▫️ Módulo 3: 12 W @ 204 V | Pico: 295 W
    ▫️ Módulo 4: 13 W @ 204 V | Pico: 295 W

🔴 Microinversor xxxxxxxxx
  • Status: ⚠️ Offline / Sem sinal de comunicação com a ECU
```
