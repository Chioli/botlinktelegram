# 🤖 Bot de Afiliado Mercado Livre — Telegram

Converte automaticamente links do Mercado Livre para links de afiliado (mlm.net.br).

---

## 📋 Pré-requisitos

- Python 3.10+
- Conta no [mlm.net.br](https://mlm.net.br) (programa de afiliados do ML)
- Um bot criado no [@BotFather](https://t.me/BotFather) do Telegram

---

## 🚀 Como configurar

### 1. Criar o bot no Telegram

1. Abra o Telegram e acesse **@BotFather**
2. Envie `/newbot`
3. Escolha um nome e um username para o bot
4. Copie o **Token** que o BotFather gerar

### 2. Pegar seu ID de afiliado

1. Acesse [mlm.net.br](https://mlm.net.br) e crie sua conta
2. No painel, vá em **Meus links** e copie seu ID de afiliado

### 3. Configurar o projeto

```bash
# Clone ou baixe os arquivos
cd bot_afiliado_ml

# Instale as dependências
pip install -r requirements.txt

# Configure as variáveis
cp .env.example .env
# Edite o arquivo .env com seu TOKEN e ID de afiliado
```

### 4. Rodar localmente

```bash
python bot.py
```

---

## ☁️ Deploy gratuito no Railway

1. Acesse [railway.app](https://railway.app) e crie uma conta
2. Clique em **New Project → Deploy from GitHub Repo**
3. Suba os arquivos para um repositório no GitHub
4. No Railway, vá em **Variables** e adicione:
   - `TELEGRAM_TOKEN` = seu token
   - `AFILIADO_ID` = seu ID do mlm.net.br
5. O bot ficará online 24h por dia!

---

## 💬 Como usar o bot

Após iniciar, envie qualquer mensagem ao bot com links do Mercado Livre.

**Exemplo:**
```
Confira esse produto incrível:
https://www.mercadolivre.com.br/produto/MLB-123456
```

**O bot responde:**
```
✅ 1 link convertido!

Confira esse produto incrível:
https://www.mercadolivre.com.br/produto/MLB-123456?affId=SEU_ID
```

---

## 📁 Estrutura do projeto

```
bot_afiliado_ml/
├── bot.py            # Código principal do bot
├── requirements.txt  # Dependências Python
├── .env.example      # Modelo de variáveis de ambiente
└── README.md         # Este arquivo
```
