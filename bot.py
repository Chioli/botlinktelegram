import os
import re
import logging
import threading
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
        self.end_headers()
        self.wfile.write(b"Bot rodando!")

    def log_message(self, format, *args):
        pass  # Silencia os logs do servidor HTTP

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

        # Remove parâmetros de afiliado antigos
        for p in ["affId", "matt_word", "matt_tool", "matt_source", "matt_campaign", "ref", "forceInApp"]:
            params.pop(p, None)

        # Adiciona o ID de afiliado no formato do ML
        params["matt_word"] = [afiliado_id]

        nova_query = urlencode({k: v[0] for k, v in params.items()})
        novo_link = urlunparse(parsed._replace(query=nova_query))
        return novo_link
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
    mensagem = (
        "👋 Olá! Sou seu bot de links afiliados do Mercado Livre.\n\n"
        "Como usar:\n"
        "Envie qualquer texto ou link de produto do ML e eu converto automaticamente para seu link de afiliado.\n\n"
        "Use /ajuda para mais informações."
    )
    await update.message.reply_text(mensagem)

async def ajuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mensagem = (
        "Ajuda — Bot de Afiliado ML\n\n"
        "• Envie um link do Mercado Livre e receba o link com seu ID de afiliado\n"
        "• Pode enviar texto completo com vários links — todos serão convertidos\n"
        "• Links de outros sites são ignorados"
    )
    await update.message.reply_text(mensagem)

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
    resposta = f"✅ {qtd} {plural}!\n\n{texto_convertido}"

    await update.message.reply_text(resposta)

# ── Inicialização ────────────────────────────────────────────────────────────
def main():
    # Inicia servidor HTTP em thread separada (keep alive para Render)
    t = threading.Thread(target=iniciar_servidor, daemon=True)
    t.start()
    print(f"🌐 Servidor HTTP iniciado na porta {PORT}")

    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ajuda", ajuda))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, processar_mensagem))

    print("🤖 Bot rodando...")
    app.run_polling()

if __name__ == "__main__":
    main()
