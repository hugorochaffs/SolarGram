import socket
import time

ECU_IP = "192.168.1.253"  # Coloque o IP da sua ECU
PORT = 8899
CMD = b"APS1100160001END" # Testando primeiro o comando de Info Geral

try:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(8.0)
        s.connect((ECU_IP, PORT))
        
        # Envia o comando
        s.sendall(CMD)
        time.sleep(0.5) # Pequena pausa para a ECU processar
        
        # Loop para escutar a resposta completa até vir o "END" no final do byte
        response = b""
        while True:
            data = s.recv(1024)
            if not data:
                break
            response += data
            if response.endswith(b"END"):
                break
                
        if len(response) == 0:
            print("A ECU fechou a conexão sem responder. Verifique se está usando Wi-Fi em vez de cabo.")
        else:
            print(f"Sucesso! Resposta recebida ({len(response)} bytes):")
            print(response.hex())
            
except Exception as e:
    print(f"Erro: {e}")
