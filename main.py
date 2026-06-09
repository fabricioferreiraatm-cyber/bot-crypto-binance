import os
import json
import time
import requests
from datetime import datetime

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

ARQUIVO_SINAIS = "sinais_enviados.json"


def carregar_sinais():
    try:
        with open(ARQUIVO_SINAIS, "r") as f:
            return json.load(f)
    except:
        return {}


def salvar_sinais(sinais):
    with open(ARQUIVO_SINAIS, "w") as f:
        json.dump(sinais, f)


def enviar_telegram(texto):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

        requests.post(
            url,
            data={
                "chat_id": CHAT_ID,
                "text": texto
            },
            timeout=20
        )

    except Exception as erro:
        print("Erro Telegram:", erro)


def calcular_score(moeda):

    score = 0

    variacao = float(moeda["priceChangePercent"])
    volume = float(moeda["quoteVolume"])

    if variacao > 3:
        score += 15

    if variacao > 5:
        score += 15

    if variacao > 10:
        score += 20

    if volume > 10000000:
        score += 15

    if volume > 50000000:
        score += 20

    if volume > 100000000:
        score += 15

    return min(score, 100)


def classificar_risco(score):

    if score >= 90:
        return "🔥 MUITO ALTO"

    if score >= 70:
        return "🚀 ALTO"

    if score >= 50:
        return "⚠️ MODERADO"

    return "❌ BAIXO"


def gerar_probabilidade(score):
    return min(95, score)


def scanner():

    sinais_enviados = carregar_sinais()

    print(f"[{datetime.now()}] Iniciando scanner...")

    url = "https://api.binance.com/api/v3/ticker/24hr"

    resposta = requests.get(url, timeout=30)
    moedas = resposta.json()

    oportunidades = []

    for moeda in moedas:

        try:

            symbol = moeda["symbol"]

            if not symbol.endswith("USDT"):
                continue

            score = calcular_score(moeda)

            if score < 70:
                continue

            oportunidades.append((score, moeda))

        except:
            pass

    oportunidades.sort(reverse=True, key=lambda x: x[0])

    for score, moeda in oportunidades[:5]:

        symbol = moeda["symbol"]

        if symbol in sinais_enviados:
            continue

        preco = float(moeda["lastPrice"])
        variacao = float(moeda["priceChangePercent"])
        volume = float(moeda["quoteVolume"])

        risco = classificar_risco(score)
        probabilidade = gerar_probabilidade(score)

        mensagem = f"""
🚀 OPORTUNIDADE DETECTADA

Moeda: {symbol}

💰 Preço: ${preco:.6f}

⭐ Score: {score}/100
📈 Probabilidade: {probabilidade}%

⚠️ Risco: {risco}

📊 Alta 24h: {variacao:.2f}%
💵 Volume: US$ {volume:,.0f}

🎯 Alvo 1: +5%
🎯 Alvo 2: +10%
🎯 Alvo 3: +20%

🛑 Stop sugerido: -4%

🕒 Horário: {datetime.now().strftime('%H:%M')}
"""

        enviar_telegram(mensagem)

        sinais_enviados[symbol] = datetime.now().strftime("%Y-%m-%d")

        print("Sinal enviado:", symbol)

    salvar_sinais(sinais_enviados)


if not BOT_TOKEN or not CHAT_ID:

    print("BOT_TOKEN ou CHAT_ID não configurados.")

else:

    enviar_telegram("✅ Scanner Binance iniciado com sucesso!")

    while True:

        try:

            scanner()

        except Exception as erro:

            print("ERRO:", erro)

        print("⏳ Aguardando 5 minutos...")
        time.sleep(300)