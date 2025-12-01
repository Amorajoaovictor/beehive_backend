import socket
import time
import random
import requests

TARGETS = {
    "ssh": 2222,
    "telnet": 2323,
    "http": 8080
}

def attack_ssh(host="127.0.0.1", port=2222, attempts=5):
    print(f"[+] Simulating SSH brute force on {host}:{port}")

    for i in range(attempts):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(2)
            s.connect((host, port))

            fake_pass = random.choice(["root", "admin", "1234", "toor"])
            payload = f"SSH-2.0-OpenSSH_8.2\r\n{fake_pass}\r\n"

            s.send(payload.encode())
            time.sleep(0.5)
            s.close()

            print(f"  → Attempt {i+1}: password={fake_pass}")

        except Exception as e:
            print("  ! Error:", e)


def attack_telnet(host="127.0.0.1", port=2323, attempts=5):
    print(f"[+] Simulating Telnet brute force on {host}:{port}")

    for i in range(attempts):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(2)
            s.connect((host, port))

            payload = f"root:{random.randint(1000,9999)}\r\n"
            s.send(payload.encode())
            time.sleep(0.5)
            s.close()

            print(f"  → Attempt {i+1}: sent {payload.strip()}")

        except Exception as e:
            print("  ! Error:", e)


def attack_http(host="127.0.0.1", port=8080, attempts=5):
    url = f"http://{host}:{port}/wp-login.php?attempt="
    print(f"[+] Simulating HTTP malicious requests on {url}")

    for i in range(attempts):
        try:
            r = requests.get(url + str(i))
            print(f"  → Attempt {i+1}: HTTP {r.status_code}")
            time.sleep(0.4)
        except Exception as e:
            print("  ! Error:", e)


if __name__ == "__main__":
    print("\n=== Select attack type ===")
    print("1) SSH")
    print("2) Telnet")
    print("3) HTTP")
    choice = input("Choose (1/2/3): ").strip()

    if choice == "1":
        attack_ssh(port=TARGETS["ssh"])
    elif choice == "2":
        attack_telnet(port=TARGETS["telnet"])
    elif choice == "3":
        attack_http(port=TARGETS["http"])
    else:
        print("Invalid choice.")

