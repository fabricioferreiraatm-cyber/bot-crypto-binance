import requests
import pandas as pd
import time
import os
from datetime import datetime

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

ARQUIVO_SINAIS = "sinais_enviados.txt"


def enviar_telegram(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    payload = {
        "chat_id": CHAT_ID,
        "text": msg,
        "parse_mode": "HTML"
    }

    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Erro Telegram: {e}")


def calcular_rsi(df, periodo=14):
    delta = df["close"].diff()

    ganho = delta.where(delta > 0, 0)
    perda = -delta.where(delta < 0, 0)

    media_ganho = ganho.rolling(periodo).mean()
    media_perda = perda.rolling(periodo).mean()

    rs = media_ganho / media_perda

    return 100 - (100 / (1 + rs))


def obter_klines(symbol):
    url = (
        f"https://api.binance.com/api/v3/klines"
        f"?symbol={symbol}&interval=1h&limit=200"
    )

    r = requests.get(url, timeout=10)

    dados = r.json()

    df = pd.DataFrame(dados)

    df = df.iloc[:, :6]

    df.columns = [
        "time",
        "open",
        "high",
        "low",
        "close",
        "volume"
    ]

    df["close"] = df["close"].astype(float)
    df["volume"] = df["volume"].astype(float)

    return df


def score_moeda(df):
    score = 0

    close = df["close"].iloc[-1]

    ema20 = df["close"].ewm(span=20).mean().iloc[-1]
    ema50 = df["close"].ewm(span=50).mean().iloc[-1]

    rsi = calcular_rsi(df).iloc[-1]

    volume_atual = df["volume"].tail(24).mean()
    volume_antigo = df["volume"].tail(168).mean()

    if volume_atual > volume_antigo * 2:
        score += 30

    if close > ema20:
        score += 15

    if close > ema50:
        score += 15

    if ema20 > ema50:
        score += 10

    if 50 <= rsi <= 70:
        score += 20

    variacao = (
        (close - df["close"].iloc[-24])
        / df["close"].iloc[-24]
    ) * 100

    if 0 < variacao < 10:
        score += 10

    return {
        "score": score,
        "close": close,
        "rsi": round(rsi, 2),
        "variacao": round(variacao, 2)
    }


def obter_moedas():
    url = "https://api.binance.com/api/v3/exchangeInfo"

    data = requests.get(url).json()

    moedas = []

    for s in data["symbols"]:
        if (
            s["quoteAsset"] == "USDT"
            and s["status"] == "TRADING"
        ):
            moedas.append(s["symbol"])

    return moedas


def carregar_enviados():
    if not os.path.exists(ARQUIVO_SINAIS):
        return set()

    with open(ARQUIVO_SINAIS, "r") as f:
        return set(f.read().splitlines())


def salvar_sinal(symbol):
    with open(ARQUIVO_SINAIS, "a") as f:
        f.write(symbol + "\n")


def analisar():
    enviados = carregar_enviados()

    moedas = obter_moedas()

    print(f"Analisando {len(moedas)} moedas")

    for symbol in moedas:

        try:
            df = obter_klines(symbol)

            resultado = score_moeda(df)

            if resultado["score"] >= 75:

                if symbol in enviados:
                    continue

                mensagem = f"""
🚀 <b>POSSÍVEL OPORTUNIDADE</b>

🪙 Moeda: <b>{symbol}</b>

💰 Preço: {resultado['close']}

📈 RSI: {resultado['rsi']}

🔥 Variação 24h: {resultado['variacao']}%

🎯 Score: {resultado['score']}/100

⏰ {datetime.now().strftime('%d/%m/%Y %H:%M')}
"""

                enviar_telegram(mensagem)

                salvar_sinal(symbol)

                print(f"Sinal enviado: {symbol}")

        except Exception as e:
            print(symbol, e)


if __name__ == "__main__":

    enviar_telegram(
        "🤖 Bot de projeções iniciado com sucesso."
    )

    while True:

        analisar()

        print("Nova análise em 30 minutos")

        time.sleep(1800)