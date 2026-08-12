import json
import os
import logging
from datetime import datetime

logger = logging.getLogger("StatsTracker")

class StatsTracker:
    """
    Gerencia o rastreamento diário de métricas e picos de geração de energia fotovoltaica.
    Salva os dados em um arquivo JSON local para persistência entre reinicializações.
    """

    def __init__(self, filepath: str = "daily_stats.json"):
        self.filepath = filepath
        self.data = self._load()

    def _get_default_structure(self, date_str: str) -> dict:
        return {
            "date": date_str,
            "system_peak_w": 0,
            "system_peak_time": "",
            "today_energy_kwh": 0.0,
            "lifetime_energy_kwh": 0.0,
            "report_sent": False,
            "last_updated": "",
            "inverters": {}
        }

    def _load(self) -> dict:
        today_str = datetime.now().strftime("%Y-%m-%d")
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if data.get("date") == today_str:
                        return data
            except Exception as e:
                logger.warning(f"Erro ao ler arquivo de estatísticas {self.filepath}: {e}")

        # Se mudou o dia ou o arquivo não existe/está corrompido, inicia estrutura nova
        return self._get_default_structure(today_str)

    def save(self):
        """Persiste os dados em disco."""
        try:
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Erro ao salvar arquivo de estatísticas {self.filepath}: {e}")

    def update(self, ecu_info: dict, realtime_data: tuple[str, list[dict]]):
        """
        Atualiza os dados de hoje com uma nova medição da ECU.
        Calcula e atualiza os picos de potência do sistema, dos microinversores e de cada módulo.
        """
        today_str = datetime.now().strftime("%Y-%m-%d")
        now_time_str = datetime.now().strftime("%H:%M:%S")

        # Se virou o dia, reseta para o novo dia
        if self.data.get("date") != today_str:
            self.data = self._get_default_structure(today_str)

        timestamp_str, inverters_list = realtime_data

        # Atualiza energias da ECU
        self.data["today_energy_kwh"] = max(self.data.get("today_energy_kwh", 0.0), ecu_info.get("today_energy_kwh", 0.0))
        self.data["lifetime_energy_kwh"] = ecu_info.get("lifetime_energy_kwh", 0.0)
        self.data["last_updated"] = now_time_str

        # Potência total atual do sistema
        current_system_power = sum(
            ch["power"] for inv in inverters_list for ch in inv.get("channels", [])
        )

        # Atualiza pico do sistema
        if current_system_power > self.data.get("system_peak_w", 0):
            self.data["system_peak_w"] = current_system_power
            self.data["system_peak_time"] = now_time_str

        # Atualiza inversores e canais
        invs_dict = self.data.setdefault("inverters", {})

        for inv in inverters_list:
            uid = inv["uid"]
            inv_stats = invs_dict.setdefault(uid, {
                "uid": uid,
                "online": False,
                "signal": 0,
                "freq": 0.0,
                "temp": 0,
                "current_power_w": 0,
                "peak_power_w": 0,
                "peak_time": "",
                "channels": {}
            })

            inv_stats["online"] = inv["online"]
            inv_stats["signal"] = inv["signal"]
            inv_stats["freq"] = inv["freq"]
            inv_stats["temp"] = inv["temp"]

            current_inv_power = sum(ch["power"] for ch in inv.get("channels", []))
            inv_stats["current_power_w"] = current_inv_power

            if current_inv_power > inv_stats.get("peak_power_w", 0):
                inv_stats["peak_power_w"] = current_inv_power
                inv_stats["peak_time"] = now_time_str

            channels_dict = inv_stats.setdefault("channels", {})
            for ch in inv.get("channels", []):
                ch_key = str(ch["channel"])
                ch_stats = channels_dict.setdefault(ch_key, {
                    "channel": ch["channel"],
                    "current_power_w": 0,
                    "voltage_v": 0,
                    "peak_power_w": 0
                })
                ch_stats["current_power_w"] = ch["power"]
                ch_stats["voltage_v"] = ch["voltage"]

                if ch["power"] > ch_stats.get("peak_power_w", 0):
                    ch_stats["peak_power_w"] = ch["power"]

        self.save()

    def mark_report_sent(self):
        """Marca que o relatório de hoje já foi enviado."""
        self.data["report_sent"] = True
        self.save()

    def is_report_sent(self) -> bool:
        """Verifica se o relatório do dia atual já foi enviado."""
        today_str = datetime.now().strftime("%Y-%m-%d")
        if self.data.get("date") != today_str:
            return False
        return self.data.get("report_sent", False)
