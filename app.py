
import os, requests
from flask import Flask, request, jsonify
from groq import Groq

app = Flask(__name__)

# CONFIG - Preencha seu .env
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "obrasgestao123")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

SYSTEM_PROMPT = open(os.path.join(os.path.dirname(__file__), "prompt.txt"), encoding="utf-8").read()

def gerar_resposta_ia(historico_mensagens):
    """historico_mensagens = lista de dicts {role, content}"""
    if not client:
        return "Olá! Aqui é da Obras Gestão 👋 No momento nosso agente de IA está em configuração. Enquanto isso, você pode começar seu teste grátis de 14 dias direto em obrasgestao.com > Ver Planos. Posso te passar para um atendente da nossa equipe?"
    
    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": SYSTEM_PROMPT}] + historico_mensagens,
            temperature=0.7,
            max_tokens=800
        )
        return completion.choices[0].message.content
    except Exception as e:
        print(f"Erro Groq: {e}")
        return "Tive um problema momentâneo aqui, mas você já pode começar seu teste grátis de 14 dias, sem cartão, em obrasgestao.com > Ver Planos. Se quiser, te passo para um atendente da nossa equipe."

def enviar_whatsapp(to, text):
    if not WHATSAPP_TOKEN or not PHONE_NUMBER_ID:
        print(f"[SIMULAÇÃO] Para {to}: {text}")
        return
    url = f"https://graph.facebook.com/v20.0/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}", "Content-Type": "application/json"}
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": text}
    }
    r = requests.post(url, headers=headers, json=payload)
    print(f"Envio WhatsApp status {r.status_code}: {r.text}")

# Memória simples em RAM (para produção use Redis/Banco)
conversas = {}

@app.route("/", methods=["GET"])
def home():
    return "Agente Obras Gestão no ar! Use /webhook"

@app.route("/webhook", methods=["GET"])
def verify():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge, 200
    return "Verification failed", 403

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    try:
        entry = data["entry"][0]["changes"][0]["value"]
        if "messages" in entry:
            msg = entry["messages"][0]
            from_number = msg["from"]
            text_user = msg.get("text", {}).get("body", "")
            if not text_user:
                return jsonify({"status": "no text"}), 200

            # Histórico
            hist = conversas.get(from_number, [])
            hist.append({"role": "user", "content": text_user})

            # Detecta pedido de atendente humano
            palavras_humano = ["humano", "atendente", "pessoa", "falar com alguém", "suporte"]
            if any(p in text_user.lower() for p in palavras_humano) and len(text_user) < 30:
                resposta = "Claro! Vou te passar para um atendente da nossa equipe agora, ele já vai receber todo o seu histórico aqui, só um segundo. 😉 Enquanto isso, você já pode ver os planos em obrasgestao.com"
                enviar_whatsapp(from_number, resposta)
                # Aqui você pode integrar: enviar e-mail, Slack, etc com o lead
                conversas[from_number] = hist
                return jsonify({"status": "transferido"}), 200

            resposta_ia = gerar_resposta_ia(hist)
            hist.append({"role": "assistant", "content": resposta_ia})
            conversas[from_number] = hist[-20:]  # mantém últimas 20

            enviar_whatsapp(from_number, resposta_ia)

    except Exception as e:
        print(f"Erro webhook: {e}")

    return jsonify({"status": "ok"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 3000)))
