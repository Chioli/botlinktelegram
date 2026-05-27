import os
import re
import logging
import threading
import asyncio
from urllib.parse import urlparse
from http.server import HTTPServer, BaseHTTPRequestHandler
import aiohttp
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# ── Configurações ────────────────────────────────────────────────────────────
TOKEN = os.environ.get("TELEGRAM_TOKEN")
AFILIADO_ID = os.environ.get("AFILIADO_ID", "chioli")
ML_COOKIE = os.environ.get("ML_COOKIE", "")
PORT = int(os.environ.get("PORT", 8080))

if not TOKEN:
    raise ValueError("Configure TELEGRAM_TOKEN nas variáveis de ambiente!")
if not ML_COOKIE:
    raise ValueError("Configure ML_COOKIE nas variáveis de ambiente!")

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)

ML_API = "https://www.mercadolivre.com.br/affiliate-program/api/v2/affiliates/createLink"

def extrair_csrf(cookie):
    for parte in cookie.split(";"):
        parte = parte.strip()
        if parte.startswith("_csrf="):
            return parte.split("=", 1)[1]
    return ""

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
    csrf = extrair_csrf(ML_COOKIE)
    headers = {
        "Cookie": ML_COOKIE,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36 Edg/148.0.0.0",
        "Content-Type": "application/json",
        "Referer": "https://www.mercadolivre.com.br/afiliados/linkbuilder",
        "Origin": "https://www.mercadolivre.com.br",
        "X-Csrf-Token": csrf,
    }
    # Limpar URL removendo parâmetros de rastreamento desnecessários
    from urllib.parse import urlparse, urlunparse
    parsed = urlparse(url)
    url_limpa = urlunparse(parsed._replace(query="", fragment=""))
    payload = {"urls": [url_limpa], "tag": AFILIADO_ID}
    async with session.post(ML_API, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as r:
        if r.status == 200:
            data = await r.json()
            urls = data.get("urls", [])
            if urls and urls[0].get("short_url"):
                logging.info("Link gerado com sucesso!")
                return urls[0]["short_url"], None
        logging.warning(f"API retornou status {r.status}")
        return None, f"⚠️ Cookie expirado ou inválido (status {r.status}). Atualize ML_COOKIE no Render!"

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

# ── Handlers do bot ──────────────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Olá! Sou seu bot de links afiliados do Mercado Livre.\n\n"
        "Envie qualquer link de produto do ML e eu converto para seu link de afiliado.\n\n"
        "Use /ajuda para mais informações."
    )

async def ajuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Ajuda — Bot de Afiliado ML\n\n"
        "• Envie um link do Mercado Livre e receba o link com seu ID de afiliado\n"
        "• Pode enviar texto completo com vários links — todos serão convertidos\n"
        "• Links de outros sites são ignorados\n"
        "• Se o cookie expirar você receberá um aviso aqui"
    )

async def processar_mensagem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text or ""
    if not texto.strip():
        return

    async with aiohttp.ClientSession() as session:
        texto_convertido, links, erro = await converter_links(session, texto)

    if erro:
        await update.message.reply_text(erro)
        return

    if not links:
        await update.message.reply_text(
            "⚠️ Nenhum link do Mercado Livre encontrado.\n"
            "Envie um link válido do ML para eu converter!"
        )
        return

    qtd = len(links)
    plural = "link convertido" if qtd == 1 else "links convertidos"
    await update.message.reply_text(f"✅ {qtd} {plural}!\n\n{texto_convertido}")

# ── Inicialização ────────────────────────────────────────────────────────────
async def main():
    threading.Thread(target=iniciar_servidor, daemon=True).start()
    print(f"🌐 Servidor HTTP iniciado na porta {PORT}")

    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ajuda", ajuda))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, processar_mensagem))

    print("🤖 Bot Telegram rodando...")
    async with app:
        await app.start()
        await app.updater.start_polling()
        await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
