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

class MinecraftHandler(http.server.SimpleHTTPRequestHandler):
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

class MCRoot:
    def __init__(self, root):
        self.root = root
        self.root.title("MINECRAFT SERVER PANEL")
        self.root.geometry("400x500")
        self.root.configure(bg="#484848") # Stone Gray

        # Baslik
        tk.Label(root, text="AERO CRAFT", font=("Courier", 30, "bold"), bg="#484848", fg="#55FF55").pack(pady=20)
        
        # Panel
        panel = tk.Frame(root, bg="#8B4513", padx=20, pady=20, highlightbackground="#000", highlightthickness=3)
        panel.pack(padx=30, fill="x")

        style = {"bg": "#8B4513", "fg": "#FFFFFF", "font": ("Courier", 10, "bold")}
        
        tk.Label(panel, text="BAGLANTI ADRESI (IP)", **style).pack(anchor="w")
        self.ip_in = tk.Entry(panel, bg="#333", fg="#55FFFF", insertbackground="white", relief="flat", font=("Consolas", 12))
        self.ip_in.insert(0, "0.0.0.0")
        self.ip_in.pack(pady=(5, 15), fill="x")

        tk.Label(panel, text="PORT", **style).pack(anchor="w")
        self.port_in = tk.Entry(panel, bg="#333", fg="#55FFFF", insertbackground="white", relief="flat", font=("Consolas", 12))
        self.port_in.insert(0, "80")
        self.port_in.pack(pady=(5, 15), fill="x")

        self.btn = tk.Button(root, text="DUNYAYI OLUSTUR", command=self.start, bg="#55FF55", fg="#000", 
                             font=("Courier", 14, "bold"), relief="raised", bd=5, cursor="hand2")
        self.btn.pack(pady=30, fill="x", padx=60, ipady=10)

        self.status = tk.Label(root, text="DURUM: KAPALI", bg="#484848", fg="#FF5555", font=("Courier", 10, "bold"))
        self.status.pack()

    def start(self):
        ip, port = self.ip_in.get(), int(self.port_in.get())
        threading.Thread(target=lambda: asyncio.run(start_ws(ip, port)), daemon=True).start()
        
        def run_http():
            try:
                server = http.server.HTTPServer((ip, port), MinecraftHandler)
                self.root.after(0, lambda: self.status.config(text=f"AKTIF: {ip}:{port}", fg="#55FF55"))
                server.serve_forever()
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("HATA", str(e)))

        threading.Thread(target=run_http, daemon=True).start()
        self.btn.config(state="disabled", text="CALISIYOR...", bg="#7D7D7D")

if __name__ == "__main__":
    root = tk.Tk()
    MCRoot(root)
    root.mainloop()