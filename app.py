import os, json, requests, sys
from flask import Flask, request, jsonify

def log(msg):
    print(msg, flush=True)
    sys.stdout.flush()

try:
    from google import genai
    HAS_GEMINI = True
    log("google.genai OK")
except Exception as e:
    HAS_GEMINI = False
    log(f"Falha genai: {e}")

app = Flask(__name__)

VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "obrasgestao123")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

log(f"ENV - PHONE:{PHONE_NUMBER_ID} GROQ:{bool(GROQ_API_KEY)} GEMINI:{bool(GEMINI_API_KEY)} WA:{bool(WHATSAPP_TOKEN)}")

gemini_client = None
if HAS_GEMINI and GEMINI_API_KEY:
    try:
        gemini_client = genai.Client(api_key=GEMINI_API_KEY)
        log("Gemini Client OK")
    except Exception as e:
        log(f"Erro Gemini: {e}")

SYSTEM_PROMPT = """Você é o atendente comercial do Obras Gestão, da WS Conecta. Fala como um brasileiro gente boa que entende de obra, conversa leve, natural, como se estivesse no WhatsApp com um amigo.

OBJETIVO: Fazer a pessoa se interessar e testar grátis 14 dias em obrasgestao.com ou falar com um atendente.

TOM - MUITO IMPORTANTE:
- Natural, humano, nada de robô. Frases curtas. 1-2 linhas no máximo por mensagem.
- Usa gírias leves de obra: "boa", "show", "entendi", "imagino", "faz sentido?"
- Emoji com moderação: 1 por mensagem, as vezes nenhum.
- Nunca diga que é IA. Você é da equipe Obras Gestão.
- Respostas DINÂMICAS, nunca repete a mesma pergunta.
- Se o cliente falar curto ("oi", "sim", "trabalho", "quero"), você entende e avança, não fica preso.

PRODUTO (fale com suas palavras, não copie):
Obras Gestão centraliza tudo da obra: contratos, medições, propostas, equipe, financeiro. Sem planilha solta. Funciona no celular e PC, sem instalar. Teste 14 dias grátis sem cartão em obrasgestao.com. WS Conecta.

PLANOS (só use esses preços):
- Obras Gestão: R$149,90/mês nos 6 primeiros meses (era R$249,90), depois R$249,90. 2 usuários. Pra quem contrata e fiscaliza.
- Obras Operações: R$149,90/mês nos 6 primeiros (era R$249,90), depois R$249,90. 2 usuários. MAIS ESCOLHIDO. Pra quem executa obra.
- Solar Gestão: R$249,90/mês nos 6 primeiros (era R$349,90), depois R$349,90. 2 usuários. Pra integradora solar.
- Usuário extra: R$39,90. Promoção até 31/01/2027.

COMO CONVERSAR - FLUXO NATURAL COM SIM/NÃO:

1. PRIMEIRO CONTATO:
Cliente: oi / olá / tudo bem
Você: Oi! 👋 Tudo bem? Aqui é do Obras Gestão. Você trabalha com obra civil, energia solar ou os dois?

2. SE RESPONDER "quero conhecer", "o que é", "como funciona":
Você: Show! É um sistema que junta tudo da obra num lugar só - contrato, medição, proposta, equipe e financeiro. Sem planilha solta. Funciona no celular e no PC. Você é mais da civil ou solar?

3. SE RESPONDER "civil", "obra civil", "trabalho com obra", "sim, civil", "construção":
Você: Boa! E hoje como você controla a obra? É mais na planilha, caderno ou já tem algum sistema?

4. SE RESPONDER "solar", "energia solar", "os dois", "civil e solar":
Você: Legal! Solar dá um trabalhão de controle né? E hoje como você controla? Planilha, caderno ou sistema?

5. SE RESPONDER "planilha", "caderno", "Excel", "no caderno", "na mão":
Você: Imagino... planilha vira dor de cabeça né? Erro, perde coisa, retrabalho. No Obras Gestão você lança uma vez e já cai no financeiro e na medição. Faz sentido pra você? Me responde com sim ou não.

6. SE RESPONDER "sim", "faz", "faz sentido", "sim faz", "claro":
Você: Ótimo! Então você já pode testar 14 dias grátis, sem cartão, direto pelo site obrasgestao.com > Ver Planos > Escolher este plano. Quer que eu te mande o link direto do plano ideal pra você? Sim ou não?

7. SE RESPONDER "quanto custa", "preço", "valor", "qual valor":
Você: Temos 3 planos, todos com 14 dias grátis sem cartão. O Obras Gestão e o Obras Operações estão por R$149,90/mês nos 6 primeiros meses (era R$249,90) por causa do lançamento até 31/01. O Solar tá R$249,90. Pelo que você me falou, o Obras Operações é o mais escolhido. Quer testar? Sim ou não?

8. SE RESPONDER "sim", "quero", "manda", "manda o link", "quero testar":
Você: Perfeito! Acessa obrasgestao.com > Ver Planos > Escolher este plano. Em 2 min você já tá dentro. Qualquer coisa me chama aqui que eu te ajudo. Posso te mandar pra um atendente da nossa equipe também, quer? Sim ou não?

9. SE RESPONDER "não", "agora não", "depois", "tô só vendo":
Você: Tranquilo! Sem pressa. Quando quiser, o teste tá lá em obrasgestao.com, 14 dias grátis sem cartão. Se quiser, te mando uma auditoria grátis do seu orçamento também. Quer? Sim ou não?

10. SE PEDIR "atendente", "humano", "pessoa", "falar com alguém":
Você: Claro! Vou te passar para um atendente da nossa equipe agora, ele já recebe todo seu histórico aqui. Só um segundinho 😉

REGRAS DE OURO:
- NUNCA repita a mesma pergunta. Use o histórico.
- Se cliente fala curto ("sim", "trabalho", "oi"), interprete e avance, não repita.
- Sempre termine com pergunta, mas VARIE: "faz sentido?", "sim ou não?", "quer?", "posso mandar?", "qual faz mais sentido pra você?"
- Use chamadas de sim/não pra facilitar resposta: "Me responde com sim ou não", "Quer? Sim ou não?", "Faz sentido? Sim ou não?"
- Respostas curtas, naturais, como humano.
- Nunca peça cartão. Sempre teste direto pelo site.
- Sempre "um atendente da nossa equipe".
- Seja simpático, não robótico.
"""

def gerar_com_groq_http(historico):
    if not GROQ_API_KEY:
        raise Exception("GROQ_API_KEY vazio")
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + historico[-12:]
    
    modelos = ["openai/gpt-oss-20b", "openai/gpt-oss-120b", "qwen/qwen3-32b", "llama-3.3-70b-versatile"]
    last_error = ""
    for modelo in modelos:
        try:
            log(f">>> Tentando Groq modelo: {modelo}")
            data = {
                "model": modelo,
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 600
            }
            r = requests.post(url, headers=headers, json=data, timeout=25)
            log(f">>> Groq {modelo} status={r.status_code} body={r.text[:600]}")
            if r.status_code == 200:
                j = r.json()
                return j["choices"][0]["message"]["content"]
            else:
                last_error = f"{r.status_code}: {r.text[:400]}"
                continue
        except Exception as e:
            last_error = str(e)
            log(f">>> Erro {modelo}: {e}")
            continue
    raise Exception(f"Todos modelos Groq falharam. Ultimo: {last_error}")

def gerar_com_gemini(historico):
    if not gemini_client:
        raise Exception("Gemini não configurado")
    last_msg = historico[-1]["content"]
    chat_hist = ""
    for m in historico[:-1][-6:]:
        role = "Cliente" if m["role"]=="user" else "Você"
        chat_hist += f"{role}: {m['content']}\n"
    prompt = f"{SYSTEM_PROMPT}\n\nHistórico:\n{chat_hist}\nCliente: {last_msg}\nVocê:"
    response = gemini_client.models.generate_content(model="gemini-1.5-flash", contents=prompt)
    return response.text

def gerar_resposta_ia(historico):
    if GROQ_API_KEY:
        try:
            log(">>> Tentando Groq HTTP...")
            resp = gerar_com_groq_http(historico)
            log(f">>> Groq OK: {resp[:150]}")
            return resp
        except Exception as e:
            log(f">>> Groq falhou: {e}")
    if gemini_client:
        try:
            log(">>> Tentando Gemini...")
            resp = gerar_com_gemini(historico)
            log(f">>> Gemini OK: {resp[:150]}")
            return resp
        except Exception as e:
            log(f">>> Gemini falhou: {e}")
    return "Tive um problema momentâneo aqui, mas você já pode começar seu teste grátis de 14 dias, sem cartão, em obrasgestao.com > Ver Planos. Se quiser, te passo para um atendente da nossa equipe."

def enviar_whatsapp(to, text):
    if not WHATSAPP_TOKEN or not PHONE_NUMBER_ID:
        log(f"[SIMULACAO] Para {to}: {text}")
        return None
    url = f"https://graph.facebook.com/v20.0/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}", "Content-Type": "application/json"}
    payload = {"messaging_product": "whatsapp", "to": to, "type": "text", "text": {"body": text[:4000]}}
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=20)
        log(f">>> Envio WhatsApp status={r.status_code}")
        return r
    except Exception as e:
        log(f">>> Erro envio WhatsApp: {e}")
        return None

conversas = {}

@app.route("/", methods=["GET"])
def home():
    return f"Agente Obras Gestão GROQ HTTP no ar! Groq:{'OK' if GROQ_API_KEY else 'OFF'} Gemini:{'OK' if gemini_client else 'OFF'} Phone:{PHONE_NUMBER_ID}"

@app.route("/webhook", methods=["GET"])
def verify():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    log(f"Verify - mode:{mode} token:{token}")
    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge, 200
    return "Verification failed", 403

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.get_json(force=True, silent=True)
        if not data:
            return jsonify({"status": "empty"}), 200
        for entry in data.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                if "statuses" in value:
                    continue
                if "messages" not in value:
                    continue
                for msg in value["messages"]:
                    from_number = msg.get("from")
                    msg_type = msg.get("type")
                    text_user = msg.get("text", {}).get("body", "") if msg_type == "text" else ""
                    if not text_user:
                        continue
                    log(f">>> MSG de {from_number}: {text_user}")
                    hist = conversas.get(from_number, [])
                    hist.append({"role": "user", "content": text_user})
                    if any(p in text_user.lower() for p in ["atendente", "humano", "pessoa"]) and len(text_user) < 35:
                        resposta = "Claro! Vou te passar para um atendente da nossa equipe agora, ele já vai receber todo o seu histórico aqui, só um segundo. 😉 Enquanto isso, você já pode ver os planos em obrasgestao.com"
                        enviar_whatsapp(from_number, resposta)
                        conversas[from_number] = hist
                        continue
                    resposta_ia = gerar_resposta_ia(hist)
                    hist.append({"role": "assistant", "content": resposta_ia})
                    conversas[from_number] = hist[-20:]
                    enviar_whatsapp(from_number, resposta_ia)
                    log(f">>> Resposta enviada para {from_number}")
    except Exception as e:
        import traceback
        log(f"Erro webhook: {e}\n{traceback.format_exc()}")
    return jsonify({"status": "ok"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
