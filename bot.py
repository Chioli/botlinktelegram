import os
import re
import logging
import threading
import asyncio
from urllib.parse import urlparse, urlencode, parse_qs, urlunparse
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

# ── Servidor HTTP (keep alive para Render gratuito) ──────────────────────────
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
    server = HTTPServer(("0.0.0.0", PORT), KeepAlive)
    server.serve_forever()

# ── Funções de link ──────────────────────────────────────────────────────────
DOMINIOS_ML = [
    "mercadolivre.com.br",
    "mercadolibre.com",
    "ml.com.br",
    "mlm.net.br",
    "produto.mercadolivre.com.br",
]

def eh_link_ml(url: str) -> bool:
    try:
        dominio = urlparse(url).netloc.lower().replace("www.", "")
        return any(dominio.endswith(d) for d in DOMINIOS_ML)
    except Exception:
        return False

def adicionar_afiliado(url: str, afiliado_id: str) -> str:
    try:
        parsed = urlparse(url)
        params = parse_qs(parsed.query, keep_blank_values=True)
        for p in ["affId", "matt_word", "matt_tool", "matt_source", "matt_campaign", "ref", "forceInApp"]:
            params.pop(p, None)
        params["matt_word"] = [afiliado_id]
        nova_query = urlencode({k: v[0] for k, v in params.items()})
        return urlunparse(parsed._replace(query=nova_query))
    except Exception:
        return url

def extrair_e_converter_links(texto: str, afiliado_id: str):
    regex = r"https?://[^\s<>\"']+"
    links_encontrados = re.findall(regex, texto)
    texto_final = texto
    links_convertidos = []
    for link in links_encontrados:
        if eh_link_ml(link):
            novo_link = adicionar_afiliado(link, afiliado_id)
            texto_final = texto_final.replace(link, novo_link)
            links_convertidos.append((link, novo_link))
    return texto_final, links_convertidos

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
    texto_convertido, links = extrair_e_converter_links(texto, AFILIADO_ID)
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
    # Servidor HTTP em thread separada
    t = threading.Thread(target=iniciar_servidor, daemon=True)
    t.start()
    print(f"🌐 Servidor HTTP iniciado na porta {PORT}")

    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ajuda", ajuda))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, processar_mensagem))

    print("🤖 Bot rodando...")
    async with app:
        await app.start()
        await app.updater.start_polling()
        await asyncio.Event().wait()  # Mantém rodando indefinidamente

if __name__ == "__main__":
    asyncio.run(main())
