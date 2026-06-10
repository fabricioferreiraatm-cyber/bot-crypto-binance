import requests
import pandas as pd
import time
import os
from datetime import datetime

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

ARQUIVO_SINAIS = "sinais_enviados.txt"


def enviar_telegram(msg):
    if not BOT_TOKEN or not CHAT_ID:
        return

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    payload = {
        "chat_id": CHAT_ID,
        "text": msg,
        "parse_mode": "HTML"
    }

    try:
        requests.post(url, json=payload, timeout=15)
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
        f"https://data-api.binance.vision/api/v3/klines"
        f"?symbol={symbol}&interval=1h&limit=200"
    )

    try:
        r = requests.get(
            url,
            timeout=20,
            headers={"User-Agent": "Mozilla/5.0"}
        )

        r.raise_for_status()

        dados = r.json()

        if not isinstance(dados, list):
            return None

        if len(dados) < 50:
            return None

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

    except Exception as e:
        print(f"Erro em {symbol}: {e}")
        return None


def score_moeda(df):
    score = 0

    close = df["close"].iloc[-1]

    ema20 = df["close"].ewm(span=20).mean().iloc[-1]
    ema50 = df["close"].ewm(span=50).mean().iloc[-1]
    ema200 = df["close"].ewm(span=200).mean().iloc[-1]

    rsi = calcular_rsi(df).iloc[-1]

    volume_atual = df["volume"].tail(24).mean()
    volume_antigo = df["volume"].tail(168).mean()

    if volume_atual > volume_antigo * 2.5:
        score += 25

    if close > ema20:
        score += 15

    if close > ema50:
        score += 15

    if close > ema200:
        score += 15

    if ema20 > ema50:
        score += 10

    if ema50 > ema200:
        score += 10

    if 55 <= rsi <= 70:
        score += 10

    variacao = (
        (close - df["close"].iloc[-24])
        / df["close"].iloc[-24]
    ) * 100

    if 2 <= variacao <= 15:
        score += 15

    return {
        "score": score,
        "close": round(close, 8),
        "rsi": round(rsi, 2),
        "variacao": round(variacao, 2)
    }


def obter_moedas():
    url = "https://data-api.binance.vision/api/v3/exchangeInfo"

    try:
        r = requests.get(
            url,
            timeout=20,
            headers={"User-Agent": "Mozilla/5.0"}
        )

        data = r.json()

        if "symbols" not in data:
            print("Resposta Binance:")
            print(data)

            enviar_telegram(
                f"⚠️ Binance erro:\n{str(data)[:300]}"
            )

            return []

        moedas = []

        for s in data["symbols"]:
            if (
                s.get("quoteAsset") == "USDT"
                and s.get("status") == "TRADING"
            ):
                stablecoins = [
                    "TUSDUSDT","USDCUSDT","FDUSDUSDT",
                    "USDPUSDT","DAIUSDT","BUSDUSDT","USDSUSDT"
                ]

                if s["symbol"] not in stablecoins:
                    moedas.append(s["symbol"])

        return moedas

    except Exception as e:
        print(f"Erro obter_moedas: {e}")

        enviar_telegram(
            f"⚠️ Falha obter moedas:\n{e}"
        )

        return []


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

    if not moedas:
        print("Nenhuma moeda encontrada")
        time.sleep(300)
        return

    print(f"Analisando {len(moedas)} moedas")

    for symbol in moedas:
        try:
            df = obter_klines(symbol)

            if df is None:
                continue

            resultado = score_moeda(df)

            if resultado["score"] >= 85:

                if symbol in enviados:
                    continue

                mensagem = f"""
🚀 FORTE PROBABILIDADE DE ALTA

🪙 Moeda: {symbol}

💰 Preço: {resultado['close']}

📈 RSI: {resultado['rsi']}

🔥 Variação 24h: {resultado['variacao']}%

📊 Tendência: ALTA

🎯 Score: {resultado['score']}/100

⏰ {datetime.now().strftime('%d/%m/%Y %H:%M')}
"""

                enviar_telegram(mensagem)

                salvar_sinal(symbol)

                print(f"Sinal enviado: {symbol}")

            time.sleep(0.5)

        except Exception as e:
            print(f"Erro em {symbol}: {e}")
            continue


if __name__ == "__main__":

    print("BOT_TOKEN:", BOT_TOKEN is not None)
    print("CHAT_ID:", CHAT_ID is not None)

    enviar_telegram(
        "🤖 Bot de projeções iniciado com sucesso."
    )

    while True:
        try:
            analisar()

            print("Nova análise em 30 minutos")

            time.sleep(1800)

        except Exception as e:
            print(f"Erro geral: {e}")

            enviar_telegram(
                f"⚠️ Erro geral:\n{e}"
            )

            time.sleep(30)
