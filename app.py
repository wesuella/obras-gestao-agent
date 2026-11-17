import os, json, requests, sys
from flask import Flask, request, jsonify

def log(msg):
    print(msg, flush=True)
    sys.stdout.flush()

# === GROQ PRINCIPAL, GEMINI FALLBACK ===
try:
    from groq import Groq
    HAS_GROQ = True
    log("groq carregado OK")
except Exception as e:
    HAS_GROQ = False
    log(f"Falha groq: {e}")

try:
    from google import genai
    HAS_GEMINI = True
    log("google.genai carregado OK")
except Exception as e:
    HAS_GEMINI = False
    log(f"Falha google.genai: {e}")

app = Flask(__name__)

VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "obrasgestao123")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

log(f"ENV CHECK - PHONE:{PHONE_NUMBER_ID} GEMINI:{bool(GEMINI_API_KEY)} GROQ:{bool(GROQ_API_KEY)} WA:{bool(WHATSAPP_TOKEN)}")

groq_client = None
if HAS_GROQ and GROQ_API_KEY:
    try:
        groq_client = Groq(api_key=GROQ_API_KEY)
        log("Groq Client criado OK")
    except Exception as e:
        log(f"Erro Groq Client: {e}")

gemini_client = None
if HAS_GEMINI and GEMINI_API_KEY:
    try:
        gemini_client = genai.Client(api_key=GEMINI_API_KEY)
        log("Gemini Client criado OK")
    except Exception as e:
        log(f"Erro Gemini Client: {e}")

SYSTEM_PROMPT = """
Você é o atendente comercial do Obras Gestão, da WS Conecta Soluções Integradas LTDA.
OBJETIVO: Levar a pessoa a testar grátis 14 dias em obrasgestao.com ou falar com um atendente da nossa equipe.

TOM: Direto, simpático, entende de obra. Brasileiro que vive obra. Mensagens curtas, 2-3 linhas no WhatsApp, nunca textão. Emoji moderado (1-2). Nunca diga que é IA, você é da equipe Obras Gestão.

PRODUTO:
Obras Gestão é plataforma só para obras, operações, energia solar e equipes de campo, com agentes de IA em cada área.
Frase oficial: "Gestão completa de obras, energia solar e execução, em um só sistema. Controle sua empresa de ponta a ponta: contratos, medições, propostas, equipe e financeiro, sem planilha solta."
Funciona no navegador do celular e PC, sem instalar. Cada empresa só vê próprios dados. Teste grátis 14 dias sem cartão, direto em obrasgestao.com. Empresa: WS Conecta Soluções Integradas LTDA.

PLANOS E PREÇOS - USE APENAS ISSO, NUNCA INVENTE:
- Obras Gestão: R$149,90/mês nos primeiros 6 meses (era R$249,90), depois R$249,90. 2 usuários inclusos. Para quem contrata e fiscaliza: carteira com mapa, prazos, medições, contratos com assinatura eletrônica, cronograma com curva S, orçamento base SINAPI, auditoria, financeiro por obra.
- Obras Operações: R$149,90/mês nos 6 primeiros meses (era R$249,90), depois R$249,90. 2 usuários. MAIS ESCOLHIDO. Para quem executa: proposta com BDI fórmula TCU Acórdão 2622/2013 que vira obra com 1 clique, medição por avanço físico, NF com ISS/INSS retidos, apontamento de equipe, custo por dia, financeiro.
- Solar Gestão: R$249,90/mês nos 6 primeiros (era R$349,90), depois R$349,90. 2 usuários. Para integradoras: cliente, busca tarifa e Fio B ANEEL pelo CEP, dimensionamento, payback, diagrama unifilar, memorial técnico.
- Usuário extra: R$39,90/mês. Promoção Lançamento até 31/01/2027.

REGRAS DE OURO:
1. Sempre qualifique logo: "Você trabalha com obra civil, energia solar ou os dois?" e "Hoje controla como? Planilha, caderno ou outro sistema?"
2. Teste grátis: NUNCA peça cartão. Diga: "Você começa o teste grátis de 14 dias direto pelo site, sem cartão. É só entrar em obrasgestao.com, clicar em Ver Planos e Escolher este plano."
3. Nunca fale nome do atendente. Sempre "um atendente da nossa equipe".
4. Se pedir atendente/humano: transfira com frase pronta.
5. Se pedir desconto além da promoção, contrato grande, parceria: transfira.
6. Sempre termine com pergunta que faz avançar: "Qual plano faz mais sentido pra você?" ou "Quer que eu te mande o link direto do plano?"

FLUXO: Saudação -> Qualificação (civil/solar + como controla hoje) -> Dor/Solução personalizada -> Oferta teste direto site -> Se travar, oferece auditoria grátis ou atendente.

EXEMPLOS:
Cliente: "Quanto custa?" Você: "Temos 3 planos, todos com 14 dias grátis sem cartão em obrasgestao.com. O Obras Gestão e o Obras Operações estão por R$149,90/mês nos 6 primeiros meses (era R$249,90) por causa do lançamento até 31/01. O Solar Gestão tá R$249,90. Qual é seu caso, civil ou solar? Te digo o ideal."
Cliente: "O que faz?" Você: "É um sistema só pra gerenciar tudo: contratos, medições, propostas, equipe e financeiro, sem planilha solta. Da proposta ao financeiro, uma info lançada uma vez. Funciona no celular e PC. Você contrata só o módulo que usa. Trabalha com obra ou solar?"
Cliente: "Quero testar" Você: "Perfeito! É direto pelo site, sem cartão. Acessa obrasgestao.com > Ver Planos > Escolher este plano. Em 2 min você já tá dentro nos 14 dias grátis. Qual plano você quer testar? Te mando o caminho certinho."
"""

def gerar_com_groq(historico):
    if not groq_client:
        raise Exception("Groq não configurado")
    msgs = [{"role": "system", "content": SYSTEM_PROMPT}] + historico[-12:]
    completion = groq_client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=msgs,
        temperature=0.7,
        max_tokens=600
    )
    return completion.choices[0].message.content

def gerar_com_gemini(historico):
    if not gemini_client:
        raise Exception("Gemini não configurado")
    last_msg = historico[-1]["content"]
    chat_hist = ""
    for m in historico[:-1][-6:]:
        role = "Cliente" if m["role"]=="user" else "Você"
        chat_hist += f"{role}: {m['content']}\n"
    prompt = f"{SYSTEM_PROMPT}\n\nHistórico:\n{chat_hist}\nCliente: {last_msg}\nVocê:"
    response = gemini_client.models.generate_content(
        model="gemini-1.5-flash",
        contents=prompt
    )
    return response.text

def gerar_resposta_ia(historico):
    # TENTA GROQ PRIMEIRO (grátis e rápido)
    if groq_client:
        try:
            log(">>> Tentando Groq (principal)...")
            resp = gerar_com_groq(historico)
            log(f">>> Groq OK: {resp[:150]}")
            return resp
        except Exception as e:
            log(f">>> Groq falhou: {e}")
    # FALLBACK GEMINI
    if gemini_client:
        try:
            log(">>> Tentando Gemini (fallback)...")
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
        log(f">>> Envio WhatsApp status={r.status_code} body={r.text[:800]}")
        return r
    except Exception as e:
        log(f">>> Erro envio WhatsApp: {e}")
        return None

conversas = {}

@app.route("/", methods=["GET"])
def home():
    return f"Agente Obras Gestão GROQ principal no ar! Groq:{'OK' if groq_client else 'OFF'} Gemini:{'OK' if gemini_client else 'OFF'} Phone:{PHONE_NUMBER_ID}"

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
        # Log só se for mensagem, não status
        if "entry" in str(data) and "messages" in str(data):
            log(f"=== WEBHOOK MSG === {json.dumps(data)[:1200]}")
        for entry in data.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                if "statuses" in value:
                    # só loga status sem poluir
                    status = value["statuses"][0].get("status") if value["statuses"] else "unknown"
                    log(f">>> Status: {status}")
                    continue
                if "messages" not in value:
                    continue
                for msg in value["messages"]:
                    from_number = msg.get("from")
                    msg_type = msg.get("type")
                    text_user = ""
                    if msg_type == "text":
                        text_user = msg.get("text", {}).get("body", "")
                    elif msg_type == "button":
                        text_user = msg.get("button", {}).get("text", "")
                    else:
                        text_user = msg.get("text", {}).get("body", "") or ""
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
