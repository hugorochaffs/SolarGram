import os
import sys
import time
import argparse
import logging
from datetime import datetime

from ecu_client import APsystemsECUClient
from stats_tracker import StatsTracker
from telegram_notifier import TelegramNotifier

# Configura o sistema de log
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("APsystemsMonitor")

def load_env_file(env_path: str = ".env"):
    """Carregador simples de arquivo .env sem dependências externas."""
    if not os.path.exists(env_path):
        return
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                os.environ.setdefault(key, val)

def main():
    load_env_file(".env")

    parser = argparse.ArgumentParser(description="Monitoramento Local APsystems & Notificador Telegram")
    parser.add_argument("--test-ecu", action="store_true", help="Testa a conexão com a ECU e exibe os dados no terminal.")
    parser.add_argument("--test-telegram", action="store_true", help="Envia uma mensagem de teste para o Telegram.")
    parser.add_argument("--test-report", "--now", action="store_true", help="Gera e envia o relatório diário para o Telegram imediatamente.")
    args = parser.parse_args()

    # Leitura das configurações
    ecu_ip = os.getenv("ECU_IP", "192.168.1.253")
    ecu_port = int(os.getenv("ECU_PORT", "8899"))
    ecu_id = os.getenv("ECU_ID", "")
    poll_interval = int(os.getenv("POLL_INTERVAL_SECONDS", "120"))
    report_time_str = os.getenv("REPORT_TIME", "18:00")
    
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
    alert_on_failure = os.getenv("TELEGRAM_ALERT_ON_FAILURE", "true").lower() == "true"
    alert_cooldown_seconds = int(os.getenv("ALERT_COOLDOWN_MINUTES", "60")) * 60

    ecu_client = APsystemsECUClient(ip=ecu_ip, port=ecu_port, ecu_id=ecu_id)
    stats_tracker = StatsTracker("daily_stats.json")
    notifier = TelegramNotifier(bot_token=bot_token, chat_id=chat_id)

    # 1. Modo Teste de ECU
    if args.test_ecu:
        logger.info(f"--- TESTANDO CONEXÃO COM ECU ({ecu_ip}:{ecu_port}) ---")
        try:
            info = ecu_client.get_ecu_info()
            logger.info(f"Informações Gerais ECU: {info}")
            ts, invs = ecu_client.get_realtime_data()
            logger.info(f"Timestamp Medição: {ts}")
            logger.info(f"Microinversores Encontrados: {len(invs)}")
            for idx, inv in enumerate(invs, 1):
                logger.info(f"  [{idx}] Microinversor {inv['uid']} - Online: {inv['online']}, Temp: {inv['temp']}°C, Freq: {inv['freq']}Hz, Canais: {inv['channels']}")
            print("\n✅ Teste de ECU concluído com sucesso!")
        except Exception as e:
            logger.error(f"❌ Erro ao conectar com a ECU: {e}")
            sys.exit(1)
        return

    # 2. Modo Teste de Telegram
    if args.test_telegram:
        logger.info("--- TESTANDO CONFIGURAÇÃO DO TELEGRAM ---")
        if not notifier.is_configured():
            logger.error("❌ Telegram não configurado! Preencha TELEGRAM_BOT_TOKEN e TELEGRAM_CHAT_ID no arquivo .env.")
            sys.exit(1)
        ok = notifier.send_message("🤖 <b>Teste de Notificação APsystems</b>\nSe você recebeu esta mensagem, a integração com o Telegram está funcionando perfeitamente!")
        if ok:
            print("✅ Mensagem de teste enviada com sucesso para o Telegram!")
        else:
            print("❌ Falha ao enviar mensagem de teste para o Telegram. Verifique os logs.")
            sys.exit(1)
        return

    # 3. Modo Teste de Relatório Imediato (--test-report / --now)
    if args.test_report:
        logger.info("--- GERANDO RELATÓRIO DIÁRIO IMEDIATO ---")
        try:
            info = ecu_client.get_ecu_info()
            rt_data = ecu_client.get_realtime_data()
            stats_tracker.update(info, rt_data)
            ok = notifier.send_daily_report(stats_tracker.data, info)
            if ok:
                print("✅ Relatório diário enviado com sucesso para o Telegram!")
            else:
                print("❌ Falha ao enviar relatório diário para o Telegram.")
                sys.exit(1)
        except Exception as e:
            logger.error(f"❌ Erro ao gerar/enviar relatório: {e}")
            if notifier.is_configured() and alert_on_failure:
                notifier.send_ecu_failure_alert(ecu_ip, ecu_port, str(e))
            sys.exit(1)
        return

    # 4. Modo Serviço Contínuo (Loop Principal)
    logger.info(f"🚀 Iniciando Serviço de Monitoramento APsystems ({ecu_ip}:{ecu_port})")
    logger.info(f"⏰ Relatório agendado diariamente para as {report_time_str}")
    logger.info(f"🔄 Intervalo de amostragem: {poll_interval} segundos")

    ecu_was_offline = False
    last_alert_time = 0

    while True:
        try:
            now = datetime.now()
            current_hhmm = now.strftime("%H:%M")

            # Polling na ECU
            info = ecu_client.get_ecu_info()
            rt_data = ecu_client.get_realtime_data()

            # Atualiza histórico de picos e métricas
            stats_tracker.update(info, rt_data)

            # Notifica recuperação se estava offline
            if ecu_was_offline:
                logger.info("✅ Conexão com a ECU restabelecida!")
                if notifier.is_configured():
                    notifier.send_ecu_recovery_notification(ecu_ip, ecu_port)
                ecu_was_offline = False

            # Verifica se é hora do relatório diário (ex: 18:00)
            if current_hhmm == report_time_str and not stats_tracker.is_report_sent():
                logger.info(f"⏰ Horário atingido ({report_time_str}). Enviando relatório diário...")
                sent = notifier.send_daily_report(stats_tracker.data, info)
                if sent:
                    stats_tracker.mark_report_sent()
                    logger.info("✅ Relatório diário enviado e marcado como concluído para hoje.")
                else:
                    logger.error("❌ Falha ao enviar o relatório diário.")

        except Exception as e:
            logger.error(f"⚠️ Erro durante ciclo de monitoramento: {e}")
            
            now_ts = time.time()
            if not ecu_was_offline or (now_ts - last_alert_time) > alert_cooldown_seconds:
                ecu_was_offline = True
                last_alert_time = now_ts
                if notifier.is_configured() and alert_on_failure:
                    logger.info("Enviando alerta de falha de conexão para o Telegram...")
                    notifier.send_ecu_failure_alert(ecu_ip, ecu_port, str(e))

        time.sleep(poll_interval)

if __name__ == "__main__":
    main()
