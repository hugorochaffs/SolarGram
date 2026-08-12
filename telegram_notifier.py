import json
import logging
import urllib.request
import urllib.error
from datetime import datetime

logger = logging.getLogger("TelegramNotifier")

class TelegramNotifier:
    """
    Envia mensagens e relatórios formatados para o Telegram usando a API do Telegram Bot (Pure Python standard library).
    """

    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token.strip()
        self.chat_id = str(chat_id).strip()
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"

    def is_configured(self) -> bool:
        """Verifica se o token e o chat_id foram fornecidos."""
        return bool(self.bot_token and self.chat_id and self.bot_token != "SEU_TELEGRAM_BOT_TOKEN_AQUI")

    def send_message(self, text: str, parse_mode: str = "HTML") -> bool:
        """Envia uma mensagem de texto formatada para o Telegram."""
        if not self.is_configured():
            logger.warning("TelegramNotifier não configurado no .env (token ou chat_id ausentes).")
            return False

        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": True
        }

        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                self.api_url,
                data=data,
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                res_body = json.loads(response.read().decode("utf-8"))
                if res_body.get("ok"):
                    logger.info("Mensagem enviada com sucesso para o Telegram.")
                    return True
                else:
                    logger.error(f"Erro na API do Telegram: {res_body}")
                    return False
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="ignore")
            logger.error(f"Erro HTTP Telegram API ({e.code}): {err_body}")
            return False
        except Exception as e:
            logger.error(f"Exceção ao enviar mensagem para o Telegram: {e}")
            return False

    def send_daily_report(self, stats_data: dict, ecu_info: dict) -> bool:
        """Formata e envia o relatório diário completo de geração de energia fotovoltaica."""
        date_str = datetime.now().strftime("%d/%m/%Y")
        
        today_kwh = stats_data.get("today_energy_kwh", 0.0)
        lifetime_kwh = stats_data.get("lifetime_energy_kwh", 0.0)
        sys_peak_w = stats_data.get("system_peak_w", 0)
        sys_peak_time = stats_data.get("system_peak_time", "N/A")

        inverters = stats_data.get("inverters", {})
        total_invs = len(inverters)
        online_invs = sum(1 for inv in inverters.values() if inv.get("online"))

        lines = [
            "☀️ <b>RELATÓRIO DIÁRIO DE GERAÇÃO SOLAR</b>",
            f"📅 <b>Data:</b> {date_str} às 18:00",
            f"📍 <b>ECU ID:</b> <code>{ecu_info.get('ecu_id', 'N/A')}</code>",
            "",
            "📊 <b>RESUMO GERAL DE GERAÇÃO:</b>",
            f"• ⚡ <b>Geração Hoje:</b> <code>{today_kwh:.2f} kWh</code>",
            f"• 📈 <b>Total Acumulado:</b> <code>{lifetime_kwh:,.2f} kWh</code>".replace(",", "X").replace(".", ",").replace("X", "."),
            f"• 🔥 <b>Pico do Sistema:</b> <code>{sys_peak_w} W</code> (às {sys_peak_time})",
            f"• 🔌 <b>Status Inversores:</b> <code>{online_invs} / {total_invs} Online</code>",
            "",
            "🛠️ <b>STATUS DOS MICROINVERSORES E MÓDULOS:</b>"
        ]

        if not inverters:
            lines.append("<i>Nenhum microinversor registrado no dia de hoje.</i>")

        for uid, inv in inverters.items():
            is_online = inv.get("online", False)
            if is_online:
                sig = inv.get("signal", 0)
                freq = inv.get("freq", 0.0)
                temp = inv.get("temp", 0)
                cur_power = inv.get("current_power_w", 0)
                peak_power = inv.get("peak_power_w", 0)
                peak_time = inv.get("peak_time", "")

                lines.append(f"\n🟢 <b>Microinversor <code>{uid}</code></b>")
                lines.append(f"  • Sinal: <code>{sig}/5</code> | Freq: <code>{freq:.1f} Hz</code> | Temp: <code>{temp}°C</code>")
                lines.append(f"  • Potência Atual: <code>{cur_power} W</code> | <b>Pico Hoje:</b> <code>{peak_power} W</code> ({peak_time})")
                lines.append("  • <b>Módulos Fotovoltaicos (Canais):</b>")

                channels = inv.get("channels", {})
                for ch_id, ch in sorted(channels.items(), key=lambda x: int(x[0])):
                    ch_p = ch.get("current_power_w", 0)
                    ch_v = ch.get("voltage_v", 0)
                    ch_pk = ch.get("peak_power_w", 0)
                    lines.append(f"    ▫️ Módulo {ch_id}: <code>{ch_p} W</code> @ <code>{ch_v} V</code> | <b>Pico:</b> <code>{ch_pk} W</code>")
            else:
                lines.append(f"\n🔴 <b>Microinversor <code>{uid}</code></b>")
                lines.append("  • Status: ⚠️ <i>Offline / Sem sinal de comunicação com a ECU</i>")

        text = "\n".join(lines)
        return self.send_message(text)

    def send_ecu_failure_alert(self, ip: str, port: int, error_msg: str) -> bool:
        """Envia alerta de falha de conexão com a ECU."""
        now_str = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        text = (
            "⚠️ <b>ALERTA: FALHA DE CONEXÃO COM A ECU</b>\n\n"
            f"Não foi possível estabelecer conexão com a ECU da APsystems no IP <code>{ip}:{port}</code>.\n\n"
            f"❌ <b>Erro:</b> <code>{error_msg}</code>\n"
            f"⏰ <b>Horário:</b> {now_str}\n\n"
            "<i>Verifique se a ECU está ligada e conectada na mesma rede local.</i>"
        )
        return self.send_message(text)

    def send_ecu_recovery_notification(self, ip: str, port: int) -> bool:
        """Envia notificação informando que a conexão com a ECU voltou ao normal."""
        now_str = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        text = (
            "✅ <b>CONEXÃO COM A ECU RESTABELECIDA</b>\n\n"
            f"A comunicação com a ECU no IP <code>{ip}:{port}</code> foi restabelecida com sucesso!\n"
            f"⏰ <b>Horário:</b> {now_str}"
        )
        return self.send_message(text)
