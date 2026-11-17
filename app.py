import os, json, requests, sys, time
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

# Numeros de atendimento
NUMERO_ENGENHARIA = "5531984311221"
NUMERO_ATENDIMENTO = "5527992012689"
EMAIL_CONTATO = "contato@obrasgestao.com"

conversas = {}
conversas_pausadas = {}

SYSTEM_PROMPT = """Você é o especialista comercial do Obras Gestão, da WS Conecta Soluções Integradas LTDA.

Você NÃO segue um script fixo de perguntas e respostas. Você tem CONHECIMENTO PROFUNDO sobre o Obras Gestão e responde de acordo com o que o cliente precisa, de forma natural, consultiva e inteligente, como um humano que vive obra.

=== CONHECIMENTO PROFUNDO DO OBRAS GESTÃO ===

O QUE É:
Obras Gestão é a plataforma completa para empresas de obras, operações, energia solar e equipes de campo. Frase oficial: "Gestão completa de obras, energia solar e execução, em um só sistema. Controle sua empresa de ponta a ponta: contratos, medições, propostas, equipe e financeiro, sem planilha solta."
Funciona no navegador do celular e computador, sem instalar nada. Cada empresa só vê seus próprios dados, com segurança. Empresa: WS Conecta Soluções Integradas LTDA, Avenida Itapemirim 1491, contato@obrasgestao.com.

PLANOS:
- Obras Gestão: R$149,90/mês nos primeiros 6 meses (era R$249,90), depois R$249,90. 2 usuários. Para quem contrata e fiscaliza: carteira com mapa, prazos, medições, contratos com assinatura eletrônica, cronograma com curva S, orçamento base SINAPI, auditoria, financeiro por obra.
- Obras Operações: R$149,90/mês nos 6 primeiros (era R$249,90), depois R$249,90. 2 usuários. MAIS ESCOLHIDO. Para quem executa: proposta com BDI fórmula TCU Acórdão 2622/2013 que vira obra com 1 clique, medição por avanço físico, NF com ISS/INSS retidos, apontamento de equipe, custo por dia, financeiro.
- Solar Gestão: R$249,90/mês nos 6 primeiros (era R$349,90), depois R$349,90. 2 usuários. Para integradoras: busca tarifa e Fio B ANEEL pelo CEP, dimensionamento, payback, diagrama unifilar, memorial técnico, checklist NR-35.
- Usuário extra: R$39,90/mês. Promoção Lançamento até 31/01/2027.

FUNCIONALIDADES:
- Adeus Planilhas: substitui controle manual, agentes IA especialistas
- Medições e Financeiro Real: físico e financeiro em tempo real, alertas de desvio
- Auditoria de Orçamentos GRÁTIS: cliente envia PDF/Excel/CSV e recebe nota de coerência vs SINAPI. Parecer: Coerente, Com Ressalvas ou Não Coerente. Uma grátis por e-mail.
- Cálculos: BDI TCU, ISS/INSS, aditivos, reajuste, curva S, dimensionamento NBR 5410
- Estoque, campo, visita com mapa e fotos, diário com clima

COMO CONVERSAR:
- Natural, humano, curto, 2-3 linhas, emoji moderado, nunca diga que é IA.
- Consultivo: entende a dor, explica como Obras Gestão resolve aquela dor específica.
- Se fala de equipe, fala de apontamento, custo por dia. Se financeiro, NF ISS/INSS, margem. Se proposta, BDI TCU. Se medição, avanço físico vs financeiro. Se solar, tarifa ANEEL por CEP.
- Se planilha, oferece auditoria grátis SINAPI.
- Nunca repita mesma pergunta, usa histórico.
- Termine com pergunta inteligente baseada no que cliente falou.
- Pode usar sim/não natural: "Faz sentido? Sim ou não?", "Quer link? Sim ou não?"
- Nunca peça cartão, sempre teste direto: obrasgestao.com > Ver Planos > Escolher este plano.
- Sempre "um atendente da nossa equipe".
- Se pedir atendente/humano, tente resolver primeiro, só transfere se insistir.
- Se pedir suporte crítico (não consigo entrar, sistema fora, perdi dados, urgente), transfere.
- Objetivo: levar para testar grátis 14 dias sem cartão ou falar com atendente.
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
            data = {"model": modelo, "messages": messages, "temperature": 0.7, "max_tokens": 600}
            r = requests.post(url, headers=headers, json=data, timeout=25)
            log(f">>> Groq {modelo} status={r.status_code}")
            if r.status_code == 200:
                j = r.json()
                return j["choices"][0]["message"]["content"]
            else:
                last_error = f"{r.status_code}: {r.text[:400]}"
                log(f">>> Falhou {modelo}: {last_error[:200]}")
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

def notificar_atendimento(numero_cliente, historico, motivo="Cliente pediu atendente"):
    try:
        resumo = ""
        for m in historico[-4:]:
            quem = "Cliente" if m["role"]=="user" else "Bot"
            resumo += f"{quem}: {m['content'][:80]} | "
        mensagem_alerta = f"🔔 NOVO ATENDIMENTO OBRAS GESTÃO - Cliente: +{numero_cliente} - Motivo: {motivo} - Historico: {resumo} - Link: https://wa.me/{numero_cliente} - Responda pelo WhatsApp Business do 28 99252-5654"
        try:
            enviar_whatsapp(NUMERO_ENGENHARIA, mensagem_alerta)
            log(f">>> Alerta enviado para Engenharia {NUMERO_ENGENHARIA}")
        except Exception as e:
            log(f">>> Erro alerta engenharia: {e}")
        try:
            enviar_whatsapp(NUMERO_ATENDIMENTO, mensagem_alerta)
            log(f">>> Alerta enviado para Atendimento {NUMERO_ATENDIMENTO}")
        except Exception as e:
            log(f">>> Erro alerta atendimento: {e}")
        log(f">>> Transferência registrada para {numero_cliente} - Email fallback: {EMAIL_CONTATO}")
    except Exception as e:
        log(f">>> Erro notificar_atendimento: {e}")

def deve_transferir(texto, historico):
    texto_lower = texto.lower()
    gatilhos_fortes = ["atendente", "humano", "pessoa real", "falar com alguém", "quero falar com pessoa", "me passa pra pessoa"]
    historico_texto = " ".join([m["content"].lower() for m in historico[-4:]])
    ja_pediu = "atendente" in historico_texto or "humano" in historico_texto
    if any(g in texto_lower for g in gatilhos_fortes):
        if ja_pediu and len(texto_lower) < 50:
            return True, "Cliente insistiu em falar com atendente"
        return False, "Primeira vez - tentar resolver"
    palavras_criticas = ["não consigo entrar", "sistema fora do ar", "perdi meus dados", "erro crítico", "urgente", "não estou conseguindo acessar"]
    if any(p in texto_lower for p in palavras_criticas):
        return True, f"Suporte critico: {texto}"
    return False, "Resolver na conversa"

@app.route("/", methods=["GET"])
def home():
    return f"Agente Obras Gestão no ar! Groq:{'OK' if GROQ_API_KEY else 'OFF'} Gemini:{'OK' if gemini_client else 'OFF'} Phone:{PHONE_NUMBER_ID}"

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
                    if from_number in conversas_pausadas:
                        pausa = conversas_pausadas[from_number]
                        if time.time() - pausa < 7200:
                            log(f">>> Cliente {from_number} em atendimento humano, bot pausado")
                            continue
                        else:
                            del conversas_pausadas[from_number]
                            log(f">>> Pausa expirou para {from_number}, bot voltou")
                    log(f">>> MSG de {from_number}: {text_user}")
                    hist = conversas.get(from_number, [])
                    hist.append({"role": "user", "content": text_user})
                    precisa, motivo = deve_transferir(text_user, hist)
                    if precisa:
                        log(f">>> TRANSFERENCIA: {motivo}")
                        resposta = f"Claro! Já avisei nosso atendimento (27 99201-2689) e engenharia. Eles vão te responder por aqui em poucos minutos. Enquanto isso, se quiser, já pode ver os planos em obrasgestao.com 😉 Se for urgente, chama direto no 27 99201-2689"
                        enviar_whatsapp(from_number, resposta)
                        notificar_atendimento(from_number, hist, motivo)
                        conversas_pausadas[from_number] = time.time()
                        conversas[from_number] = hist
                        continue
                    elif any(p in text_user.lower() for p in ["atendente", "humano", "pessoa"]) and len(text_user) < 35:
                        log(f">>> Pedido atendente primeira vez, tentando resolver")
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
