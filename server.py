import http.server
import os
import cgi
import threading
import asyncio
import websockets
import json
import tkinter as tk
from tkinter import messagebox

# Klasor Ayari
UPLOAD_DIR = "yuklenenler"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

connected_clients = set()
ws_loop = None

class ATPHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.path = 'index.html'
            return super().do_GET()
        
        # API: Dosya Listesi
        if self.path == '/api/files':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            files = os.listdir(UPLOAD_DIR)
            self.wfile.write(json.dumps(files).encode())
            return

        # API: Dosya Sil
        if self.path.startswith('/api/delete/'):
            import urllib.parse
            filename = urllib.parse.unquote(self.path.replace('/api/delete/', ''))
            filepath = os.path.join(UPLOAD_DIR, filename)
            if os.path.exists(filepath):
                os.remove(filepath)
                self.notify_clients()
            self.send_response(200)
            self.end_headers()
            return

        return super().do_GET()

    def do_POST(self):
        form = cgi.FieldStorage(fp=self.rfile, headers=self.headers, environ={'REQUEST_METHOD': 'POST'})
        if 'file' in form and form['file'].filename:
            fn = os.path.basename(form['file'].filename)
            with open(os.path.join(UPLOAD_DIR, fn), 'wb') as f:
                f.write(form['file'].file.read())
            self.notify_clients()
        
        self.send_response(200)
        self.end_headers()

    def notify_clients(self):
        if ws_loop and connected_clients:
            for client in list(connected_clients):
                asyncio.run_coroutine_threadsafe(client.send("update"), ws_loop)

async def ws_logic(websocket):
    connected_clients.add(websocket)
    try:
        async for _ in websocket: pass
    finally:
        connected_clients.remove(websocket)

async def start_ws(ip, port):
    global ws_loop
    ws_loop = asyncio.get_running_loop()
    async with websockets.serve(ws_logic, ip, port + 1):
        await asyncio.Future()

class ATPRoot:
    def __init__(self, root):
        self.root = root
        self.root.title("ATP CRAFT SUNUCU PANELI")
        self.root.geometry("400x520")
        self.root.configure(bg="#313131") # Koyu Tas Rengi

        # Logo/Baslik
        tk.Label(root, text="ATP CRAFT", font=("Courier", 34, "bold"), bg="#313131", fg="#FFFF55").pack(pady=20)
        
        # Kontrol Paneli
        panel = tk.Frame(root, bg="#4A321F", padx=20, pady=20, highlightbackground="#000", highlightthickness=4)
        panel.pack(padx=30, fill="x")

        lbl_style = {"bg": "#4A321F", "fg": "#E0E0E0", "font": ("Courier", 10, "bold")}
        
        tk.Label(panel, text="SUNUCU IP ADRESI", **lbl_style).pack(anchor="w")
        self.ip_in = tk.Entry(panel, bg="#1E1E1E", fg="#55FF55", insertbackground="white", relief="flat", font=("Consolas", 12))
        self.ip_in.insert(0, "0.0.0.0")
        self.ip_in.pack(pady=(5, 15), fill="x")

        tk.Label(panel, text="PORT (VARSAYILAN 80)", **lbl_style).pack(anchor="w")
        self.port_in = tk.Entry(panel, bg="#1E1E1E", fg="#55FF55", insertbackground="white", relief="flat", font=("Consolas", 12))
        self.port_in.insert(0, "80")
        self.port_in.pack(pady=(5, 15), fill="x")

        # Baslat Butonu
        self.btn = tk.Button(root, text="DUNYAYI YUKLE", command=self.start, bg="#3FB33F", fg="#FFF", 
                             font=("Courier", 14, "bold"), relief="raised", bd=6, cursor="hand2", activebackground="#2D802D")
        self.btn.pack(pady=30, fill="x", padx=60, ipady=10)

        self.status = tk.Label(root, text="DURUM: BEKLENIYOR...", bg="#313131", fg="#AAAAAA", font=("Courier", 10))
        self.status.pack()

    def start(self):
        ip, port = self.ip_in.get(), int(self.port_in.get())
        threading.Thread(target=lambda: asyncio.run(start_ws(ip, port)), daemon=True).start()
        
        def run_http():
            try:
                server = http.server.HTTPServer((ip, port), ATPHandler)
                self.root.after(0, lambda: self.status.config(text=f"AKTIF: {ip}:{port}", fg="#55FF55"))
                server.serve_forever()
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("HATA", str(e)))

        threading.Thread(target=run_http, daemon=True).start()
        self.btn.config(state="disabled", text="SUNUCU ACIK", bg="#555555")

if __name__ == "__main__":
    root = tk.Tk()
    ATPRoot(root)
    root.mainloop()
