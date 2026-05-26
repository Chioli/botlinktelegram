import os
import re
import asyncio
import logging
import threading
from urllib.parse import urlparse
from http.server import HTTPServer, BaseHTTPRequestHandler
import aiohttp

# ── Configurações ────────────────────────────────────────────────────────────
TOKEN = os.environ.get("DISCORD_TOKEN")
AFILIADO_ID = os.environ.get("AFILIADO_ID", "chioli")
ML_COOKIE = os.environ.get("ML_COOKIE", "")
PORT = int(os.environ.get("PORT", 8080))

if not TOKEN:
    raise ValueError("Configure DISCORD_TOKEN nas variáveis de ambiente!")
if not ML_COOKIE:
    raise ValueError("Configure ML_COOKIE nas variáveis de ambiente!")

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)

DISCORD_API = "https://discord.com/api/v10"
ML_API = "https://www.mercadolivre.com.br/afiliados/link"

# ── Servidor HTTP keep alive ──────────────────────────────────────────────────
class KeepAlive(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Bot rodando!")
    def do_HEAD(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
    def do_POST(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"ok")
    def log_message(self, format, *args):
        pass

def iniciar_servidor():
    HTTPServer(("0.0.0.0", PORT), KeepAlive).serve_forever()

# ── Funções de link ──────────────────────────────────────────────────────────
DOMINIOS_ML = ["mercadolivre.com.br", "mercadolibre.com", "ml.com.br", "produto.mercadolivre.com.br"]

def eh_link_ml(url):
    try:
        dominio = urlparse(url).netloc.lower().replace("www.", "")
        return any(dominio.endswith(d) for d in DOMINIOS_ML)
    except:
        return False

async def gerar_link_com_cookie(session, url):
    headers = {
        "Cookie": ML_COOKIE,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
        "Content-Type": "application/json",
        "Referer": "https://www.mercadolivre.com.br/",
        "Origin": "https://www.mercadolivre.com.br",
    }
    async with session.post(ML_API, json={"url": url}, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as r:
        if r.status == 200:
            data = await r.json()
            link = data.get("shortUrl") or data.get("url") or data.get("link")
            if link:
                logging.info(f"Link gerado com sucesso via cookie")
                return link, None
        logging.warning(f"Cookie retornou status {r.status}")
        return None, f"⚠️ Cookie expirado ou inválido (status {r.status}). Atualize a variável ML_COOKIE no Render!"

async def converter_links(session, texto):
    links = re.findall(r"https?://[^\s<>\"']+", texto)
    texto_final = texto
    convertidos = []
    erro = None
    for link in links:
        if eh_link_ml(link):
            novo, err = await gerar_link_com_cookie(session, link)
            if novo:
                texto_final = texto_final.replace(link, novo)
                convertidos.append(novo)
            else:
                erro = err
                break
    return texto_final, convertidos, erro

# ── Gateway Discord ───────────────────────────────────────────────────────────
async def enviar_mensagem(session, channel_id, conteudo):
    url = f"{DISCORD_API}/channels/{channel_id}/messages"
    headers = {"Authorization": f"Bot {TOKEN}", "Content-Type": "application/json"}
    async with session.post(url, json={"content": conteudo}, headers=headers) as r:
        if r.status not in (200, 201):
            logging.error(f"Erro ao enviar: {r.status}")

async def conectar_gateway():
    headers = {"Authorization": f"Bot {TOKEN}"}
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{DISCORD_API}/gateway", headers=headers) as r:
            gateway_url = (await r.json())["url"] + "?v=10&encoding=json"

        async with session.ws_connect(gateway_url) as ws:
            heartbeat_interval = None
            sequence = None

            async def heartbeat():
                while True:
                    await asyncio.sleep(heartbeat_interval / 1000)
                    await ws.send_json({"op": 1, "d": sequence})

            async for msg in ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    data = msg.json()
                    op = data.get("op")
                    t = data.get("t")
                    if data.get("s"):
                        sequence = data["s"]

                    if op == 10:
                        heartbeat_interval = data["d"]["heartbeat_interval"]
                        asyncio.create_task(heartbeat())
                        await ws.send_json({
                            "op": 2,
                            "d": {
                                "token": TOKEN,
                                "intents": 33280,
                                "properties": {"os": "linux", "browser": "bot", "device": "bot"}
                            }
                        })
                        logging.info("Bot Discord conectado!")

                    elif op == 0 and t == "MESSAGE_CREATE":
                        if data["d"].get("author", {}).get("bot"):
                            continue
                        conteudo = data["d"].get("content", "")
                        channel_id = data["d"]["channel_id"]

                        texto_convertido, links, erro = await converter_links(session, conteudo)

                        if erro:
                            await enviar_mensagem(session, channel_id, erro)
                        elif links:
                            qtd = len(links)
                            plural = "link convertido" if qtd == 1 else "links convertidos"
                            await enviar_mensagem(session, channel_id, f"🛒 {qtd} {plural} com afiliado:\n\n{texto_convertido}")

                elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                    logging.warning("WebSocket desconectado...")
                    break

async def main():
    threading.Thread(target=iniciar_servidor, daemon=True).start()
    logging.info(f"Servidor HTTP na porta {PORT}")
    while True:
        try:
            await conectar_gateway()
        except Exception as e:
            logging.error(f"Erro: {e}")
        logging.info("Reconectando em 5s...")
        await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(main())
