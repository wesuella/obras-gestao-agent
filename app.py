
import os, requests
from flask import Flask, request, jsonify

# Tenta importar os dois provedores
try:
    import google.generativeai as genai
    HAS_GEMINI = True
except:
    HAS_GEMINI = False

try:
    from groq import Groq
    HAS_GROQ = True
except:
    HAS_GROQ = False

app = Flask(__name__)

VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "obrasgestao123")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Configura clientes
if HAS_GEMINI and GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

groq_client = Groq(api_key=GROQ_API_KEY) if HAS_GROQ and GROQ_API_KEY else None

SYSTEM_PROMPT = open(os.path.join(os.path.dirname(__file__), "prompt.txt"), encoding="utf-8").read()

def gerar_com_gemini(historico):
    if not HAS_GEMINI or not GEMINI_API_KEY:
        raise Exception("Gemini não configurado")
    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        system_instruction=SYSTEM_PROMPT
    )
    chat_history = []
    for m in historico[:-1]:
        role = "user" if m["role"] == "user" else "model"
        chat_history.append({"role": role, "parts": [m["content"]]})
    chat = model.start_chat(history=chat_history)
    response = chat.send_message(historico[-1]["content"])
    return response.text

def gerar_com_groq(historico):
    if not groq_client:
        raise Exception("Groq não configurado")
    completion = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "system", "content": SYSTEM_PROMPT}] + historico,
        temperature=0.7,
        max_tokens=800
    )
    return completion.choices[0].message.content

def gerar_resposta_ia(historico):
    # TENTA GEMINI PRIMEIRO
    if GEMINI_API_KEY:
        try:
            print("Tentando Gemini...")
            resp = gerar_com_gemini(historico)
            print("Gemini OK")
            return resp
        except Exception as e:
            print(f"Gemini falhou: {e} - tentando Groq...")

    # FALLBACK GROQ
    if GROQ_API_KEY:
        try:
            print("Tentando Groq...")
            resp = gerar_com_groq(historico)
            print("Groq OK")
            return resp
        except Exception as e:
            print(f"Groq falhou: {e}")

    return "Tive um problema momentâneo aqui, mas você já pode começar seu teste grátis de 14 dias, sem cartão, em obrasgestao.com > Ver Planos. Se quiser, te passo para um atendente da nossa equipe."

def enviar_whatsapp(to, text):
    if not WHATSAPP_TOKEN or not PHONE_NUMBER_ID:
        print(f"[SIMULAÇÃO] Para {to}: {text}")
        return
    url = f"https://graph.facebook.com/v20.0/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}", "Content-Type": "application/json"}
    payload = {"messaging_product": "whatsapp", "to": to, "type": "text", "text": {"body": text[:4000]}}
    r = requests.post(url, headers=headers, json=payload)
    print(f"Envio WhatsApp {r.status_code}")

conversas = {}

@app.route("/", methods=["GET"])
def home():
    status = []
    status.append(f"Gemini: {'✅' if GEMINI_API_KEY else '❌'}")
    status.append(f"Groq: {'✅' if GROQ_API_KEY else '❌'}")
    status.append(f"WhatsApp: {'✅' if WHATSAPP_TOKEN else '❌'}")
    return f"Agente Obras Gestão DUAL no ar! {' | '.join(status)}"

@app.route("/webhook", methods=["GET"])
def verify():
    if request.args.get("hub.mode") == "subscribe" and request.args.get("hub.verify_token") == VERIFY_TOKEN:
        return request.args.get("hub.challenge"), 200
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

            hist = conversas.get(from_number, [])
            hist.append({"role": "user", "content": text_user})

            # Transferência
            if any(p in text_user.lower() for p in ["atendente", "humano", "pessoa"]) and len(text_user) < 35:
                resposta = "Claro! Vou te passar para um atendente da nossa equipe agora, ele já vai receber todo o seu histórico aqui, só um segundo. 😉 Enquanto isso, você já pode ver os planos em obrasgestao.com"
                enviar_whatsapp(from_number, resposta)
                conversas[from_number] = hist
                return jsonify({"status": "transferido"}), 200

            resposta_ia = gerar_resposta_ia(hist)
            hist.append({"role": "assistant", "content": resposta_ia})
            conversas[from_number] = hist[-20:]
            enviar_whatsapp(from_number, resposta_ia)
    except Exception as e:
        print(f"Erro webhook: {e}")
    return jsonify({"status": "ok"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 3000)))
