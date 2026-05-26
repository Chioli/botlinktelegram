import os
import re
import logging
import threading
import asyncio
from urllib.parse import urlparse, urlencode, urlunparse
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# ── Configurações ────────────────────────────────────────────────────────────
TOKEN = os.environ.get("TELEGRAM_TOKEN")
AFILIADO_ID = os.environ.get("AFILIADO_ID", "chioli")
PORT = int(os.environ.get("PORT", 8080))

if not TOKEN:
    raise ValueError("Configure TELEGRAM_TOKEN nas variáveis de ambiente!")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# ── Servidor HTTP (keep alive Render) ────────────────────────────────────────
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
DOMINIOS_ML = [
    "mercadolivre.com.br",
    "mercadolibre.com",
    "ml.com.br",
    "produto.mercadolivre.com.br",
]

def eh_link_ml(url):
    try:
        dominio = urlparse(url).netloc.lower().replace("www.", "")
        return any(dominio.endswith(d) for d in DOMINIOS_ML)
    except:
        return False

def adicionar_afiliado(url):
    try:
        parsed = urlparse(url)
        nova_query = urlencode({"matt_word": AFILIADO_ID})
        return urlunparse(parsed._replace(query=nova_query, fragment=""))
    except:
        return url

def converter_links(texto):
    links = re.findall(r"https?://[^\s<>\"']+", texto)
    texto_final = texto
    convertidos = []
    for link in links:
        if eh_link_ml(link):
            novo = adicionar_afiliado(link)
            texto_final = texto_final.replace(link, novo)
            convertidos.append(novo)
    return texto_final, convertidos

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
        "• Links de outros sites são ignorados"
    )

async def processar_mensagem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text or ""
    if not texto.strip():
        return
    texto_convertido, links = converter_links(texto)
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
