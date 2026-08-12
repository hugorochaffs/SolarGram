import socket
import time
import re
import logging

logger = logging.getLogger("APsystemsECU")

class APsystemsECUClient:
    """
    Cliente para comunicação local via TCP socket com ECU APsystems (ECU-R, ECU-R-PRO, ECU-B, ECU-C).
    Utiliza o protocolo binário local na porta 8899.
    """

    def __init__(self, ip: str = "192.168.1.253", port: int = 8899, ecu_id: str = ""):
        self.ip = ip
        self.port = port
        self.ecu_id = ecu_id.strip()

    def _send_cmd(self, cmd_bytes: bytes, timeout: float = 8.0) -> bytes:
        """Abre socket TCP, envia o comando e lê a resposta até o marcador 'END'."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            s.connect((self.ip, self.port))
            s.sendall(cmd_bytes)
            time.sleep(0.3)
            
            response = b""
            while True:
                data = s.recv(1024)
                if not data:
                    break
                response += data
                if response.endswith(b"END\n") or response.endswith(b"END"):
                    break
            return response

    def get_ecu_info(self) -> dict:
        """
        Consulta informações gerais da ECU (Comando 0001).
        Retorna ID da ECU, energia diária (kWh), energia acumulada (kWh), potência atual (W), versão de firmware e fuso horário.
        """
        cmd_str = f"APS1200280001{self.ecu_id}END" if self.ecu_id else "APS1100160001END"
        resp = self._send_cmd(cmd_str.encode("utf-8"))

        if not resp.startswith(b"APS"):
            raise ValueError(f"Resposta inválida recebida da ECU ({len(resp)} bytes).")

        # Extrai ECU ID da resposta se não tínhamos configurado
        extracted_ecu_id = resp[13:25].decode(errors="ignore").strip()
        if not self.ecu_id and extracted_ecu_id:
            self.ecu_id = extracted_ecu_id

        # Campos numéricos
        lifetime_energy = int.from_bytes(resp[27:31], "big") / 100.0  # kWh
        current_power = int.from_bytes(resp[31:35], "big")            # W
        today_energy = int.from_bytes(resp[35:39], "big") / 100.0     # kWh

        # Firmware e Fuso Horário
        firmware = "Desconhecido"
        timezone = "Desconhecido"
        if len(resp) > 40:
            raw_text = resp[40:-4].decode(errors="ignore")
            fw_match = re.search(r"(ECU_[A-Z0-9_]+[\d\.]+)", raw_text)
            if fw_match:
                firmware = fw_match.group(1)
            tz_match = re.search(r"([A-Za-z]+/[A-Za-z_]+)", raw_text)
            if tz_match:
                timezone = tz_match.group(1)

        return {
            "ecu_id": self.ecu_id or extracted_ecu_id,
            "lifetime_energy_kwh": lifetime_energy,
            "current_power_w": current_power,
            "today_energy_kwh": today_energy,
            "firmware": firmware,
            "timezone": timezone
        }

    def get_realtime_data(self) -> tuple[str, list[dict]]:
        """
        Consulta os dados em tempo real dos microinversores e módulos (Comando 0002).
        Retorna (timestamp_str, lista_de_microinversores).
        """
        if not self.ecu_id:
            # Tenta auto-detectar o ECU ID se ainda não possuir
            self.get_ecu_info()
            if not self.ecu_id:
                raise ValueError("ECU_ID não informado e não foi possível auto-detectá-lo.")

        cmd_str = f"APS1200280002{self.ecu_id}END"
        resp = self._send_cmd(cmd_str.encode("utf-8"))

        if not resp.startswith(b"APS") or not (resp.endswith(b"END\n") or resp.endswith(b"END")):
            raise ValueError("Resposta malformada ou incompleta da ECU para dados em tempo real.")

        cmd_type = resp[9:13].decode(errors="ignore")
        if cmd_type != "0002":
            raise ValueError(f"Código de resposta inesperado: {cmd_type} (esperado 0002)")

        # Timestamp dos dados (Bytes 19..25 em formato BCD Hex: YY MM DD HH MM SS)
        ts_bytes = resp[19:26]
        timestamp = f"20{ts_bytes[0]:02x}-{ts_bytes[2]:02x}-{ts_bytes[3]:02x} {ts_bytes[4]:02x}:{ts_bytes[5]:02x}:{ts_bytes[6]:02x}"

        idx = 26
        inverters = []
        end_idx = len(resp) - 4 if resp.endswith(b"END\n") else len(resp) - 3

        while idx < end_idx:
            uid = resp[idx:idx+6].hex()
            online = (resp[idx+6] == 1)
            signal_str = resp[idx+7:idx+9].decode(errors="ignore")
            signal = int(signal_str) if signal_str.isdigit() else 0

            # Caso de microinversor offline com bloco curto (9 bytes)
            if not online and signal_str == "00":
                inverters.append({
                    "uid": uid,
                    "online": False,
                    "signal": 0,
                    "freq": 0.0,
                    "temp": 0,
                    "channels": []
                })
                idx += 9
                continue

            # Inversores iniciados por 40 são 2 canais (YC600, DS3-L), demais costumam ser 4 canais (QS1, QT2)
            num_channels = 2 if uid.startswith("40") else 4

            freq = int.from_bytes(resp[idx+9:idx+11], "big") / 10.0
            raw_temp = int.from_bytes(resp[idx+11:idx+13], "big")
            temp = (raw_temp - 100) if raw_temp > 0 else 0

            channels = []
            if num_channels == 2:
                p1 = int.from_bytes(resp[idx+13:idx+15], "big")
                v1 = int.from_bytes(resp[idx+15:idx+17], "big")
                p2 = int.from_bytes(resp[idx+17:idx+19], "big")
                v2 = int.from_bytes(resp[idx+19:idx+21], "big")
                channels = [
                    {"channel": 1, "power": p1, "voltage": v1},
                    {"channel": 2, "power": p2, "voltage": v2}
                ]
                idx += 21
            else:  # 4 canais
                p1 = int.from_bytes(resp[idx+13:idx+15], "big")
                v1 = int.from_bytes(resp[idx+15:idx+17], "big")
                p2 = int.from_bytes(resp[idx+17:idx+19], "big")
                p3 = int.from_bytes(resp[idx+19:idx+21], "big")
                p4 = int.from_bytes(resp[idx+21:idx+23], "big")
                channels = [
                    {"channel": 1, "power": p1, "voltage": v1},
                    {"channel": 2, "power": p2, "voltage": v1},
                    {"channel": 3, "power": p3, "voltage": v1},
                    {"channel": 4, "power": p4, "voltage": v1}
                ]
                idx += 23

            inverters.append({
                "uid": uid,
                "online": online,
                "signal": signal,
                "freq": freq,
                "temp": temp,
                "channels": channels
            })

        return timestamp, inverters
