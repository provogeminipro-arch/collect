import subprocess
import threading
import socket
import time
import sys
import os
import re


def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def start_server():
    import uvicorn
    # Bind to 0.0.0.0 to accept connections from local network & tunnel
    uvicorn.run("main:app", host="0.0.0.0", port=8000, log_level="warning")


def main():
    local_ip = get_local_ip()

    print("\n" + "=" * 66)
    print(" 🚀  AVVIO COLLECT - SITO WEB & RADAR FINANZIARIO REMOTO")
    print("=" * 66)
    print(f" ⏳ 1. Avvio server FastAPI locale su porta 8000...")

    # Start FastAPI in a background daemon thread
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()
    time.sleep(2)

    print(f" 🌐 2. Generazione link pubblico sicuro (HTTPS) per accesso remoto...")

    # Launch SSH tunnel via localhost.run
    cmd = [
        "ssh",
        "-o", "StrictHostKeyChecking=no",
        "-o", "ServerAliveInterval=30",
        "-R", "80:localhost:8000",
        "nokey@localhost.run"
    ]

    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        public_url = None

        start_time = time.time()
        while time.time() - start_time < 12:
            line = proc.stdout.readline()
            if not line:
                continue
            match = re.search(r"https://[a-zA-Z0-9-]+\.lhr\.life", line)
            if match:
                public_url = match.group(0)
                break

        print("\n" + "=" * 66)
        print(" 🎉  SITO WEB ONLINE E PRONTO PER L'ACCESSO REMOTO!")
        print("=" * 66)
        if public_url:
            print(f" 📱 ACCESSO DA SMARTPHONE / QUALUNQUE DISPOSITIVO NEL MONDO:")
            print(f"    👉 {public_url}")
        else:
            print(f" 📱 ACCESSO REMOTO: Tunnel in fase di stabilizzazione...")

        print(f"\n 🏠 ACCESSO DA CASA / DISPOSITIVI CONNESSI AL TUO WI-FI:")
        print(f"    👉 http://{local_ip}:8000")
        print(f"    👉 http://localhost:8000")
        print("=" * 66)
        print(" Premi CTRL+C in qualsiasi momento per arrestare il server.\n")

        # Keep alive
        proc.wait()

    except KeyboardInterrupt:
        print("\nArresto del server e del tunnel in corso...")
    except Exception as e:
        print(f"\nErrore tunnel: {e}")
        print(f"Il server locale rimane comunque accessibile su: http://{local_ip}:8000")
        server_thread.join()


if __name__ == "__main__":
    main()
