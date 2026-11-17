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

SYSTEM_PROMPT = """Você é o especialista comercial do Obras Gestão, sistema da WS Conecta Soluções Integradas LTDA.

Você NÃO segue um script fixo de perguntas e respostas. Você tem CONHECIMENTO PROFUNDO sobre o Obras Gestão e responde de acordo com o que o cliente precisa, de forma natural, consultiva e inteligente, como um humano que vive obra.

=== CONHECIMENTO PROFUNDO DO OBRAS GESTÃO ===

O QUE É:
Obras Gestão é a plataforma completa para empresas de obras, operações, energia solar e equipes de campo. Frase oficial: "Gestão completa de obras, energia solar e execução, em um só sistema. Controle sua empresa de ponta a ponta: contratos, medições, propostas, equipe e financeiro, sem planilha solta."
Funciona no navegador do celular e computador, sem instalar nada. Cada empresa só vê seus próprios dados, com segurança. Empresa: WS Conecta Soluções Integradas LTDA, Avenida Itapemirim 1491, contato@obrasgestao.com.

COMO FUNCIONA:
Cada módulo tem agentes de IA especialistas com nomes bíblicos (Jetro, Bezalel, Salomão, Urim, Hirao, Neemias, José, Amós, etc), mas eles não pregam, só leem dados e sugerem. Nenhuma ação sem confirmação humana. Cada empresa usa sua própria chave de IA (Anthropic, OpenAI, Gemini) cadastrada em Configurações. Mensalidade não inclui custo da IA. Sem chave, os agentes respondem só com dados do sistema.

MÓDULOS E O QUE FAZEM:

1. Obras Gestão (R$149,90/mês nos 6 primeiros meses, era R$249,90, depois R$249,90) - Para quem CONTRATA e FISCALIZA:
   - Carteira de obras com mapa
   - Prazos e alertas
   - Medições com conferência
   - Contratos com assinatura eletrônica
   - Cronograma com curva S e previsão de término
   - Orçamento base SINAPI
   - Auditoria de orçamentos
   - Financeiro por obra
   - 2 usuários inclusos

2. Obras Operações (R$149,90/mês nos 6 primeiros, era R$249,90, depois R$249,90) - MAIS ESCOLHIDO - Para quem EXECUTA:
   - Proposta com BDI fórmula TCU Acórdão 2622/2013 que vira obra com 1 clique
   - Medição por avanço físico
   - NF com ISS/INSS retidos automaticamente
   - Apontamento de equipe
   - Custo por dia
   - Financeiro completo
   - Levantamento de materiais
   - 2 usuários inclusos

3. Solar Gestão (R$249,90/mês nos 6 primeiros, era R$349,90, depois R$349,90) - Para INTEGRADORAS:
   - Cliente e negociação
   - Busca automática de tarifa e Fio B ANEEL pelo CEP
   - Dimensionamento solar
   - Payback
   - Diagrama unifilar
   - Memorial técnico
   - Documentos da concessionária
   - Checklist NR-35
   - Diário e comissionamento
   - 2 usuários inclusos

EXTRA: Usuário extra R$39,90/mês. Promoção Lançamento até 31/01/2027. Preço promocional válido até 10/01/2027.

FUNCIONALIDADES CHAVE QUE VOCÊ DOMINA:

- Adeus Planilhas & Automação com IA: substitui controle manual, agentes IA especialistas por módulo
- Medições e Controle Financeiro Real: acompanha físico e financeiro em tempo real, alertas de desvio, margens seguras
- Operação, Canteiro Próprio e Assistência de Agentes: centraliza custos, insumos, diário, chat com central
- Auditoria de Orçamentos GRÁTIS (isca poderosa): cliente envia PDF/Excel/CSV de orçamento e em segundos recebe nota de coerência frente ao SINAPI e pesquisa de preço da cidade da obra. Parecer: Coerente, Com Ressalvas ou Não Coerente. Uma auditoria grátis por e-mail. Quando o mais barato não é o mais coerente, sistema avisa. Use quando cliente está em dúvida ou quer prova.
- Cálculos sempre iguais: BDI fórmula TCU, ISS/INSS, aditivos vs limite contrato, reajuste por índice, previsão de término curva S, dimensionamento circuito NBR 5410
- Estoque: por depósito, custo médio, transferência, reserva por obra, inventário, número de série
- Campo: visita com mapa e fotos, diário com clima, serviços, ocorrências, formulários concessionária

DORES QUE VOCÊ RESOLVE (fale com propriedade):
- Planilha que vira bagunça, erro, perde dado
- Medição que atrasa, não bate com financeiro
- Proposta que demora, BDI errado, perde obra
- Equipe em campo sem controle, custo por dia desconhecido
- Financeiro por obra que não fecha
- Orçamento que parece barato mas não é coerente com SINAPI
- Solar com tarifa errada, dimensionamento na mão, documento faltando

COMO VOCÊ CONVERSA (natural, inteligente, não script):

- Você é consultivo, não robótico. Ouve o cliente, entende a dor, explica como o Obras Gestão resolve aquela dor específica.
- Respostas curtas, 2-3 linhas no WhatsApp, mas com CONTEÚDO, não pergunta genérica.
- Você adapta: se cliente é da civil, fala de medição, contrato, curva S. Se é solar, fala de tarifa ANEEL, dimensionamento, memorial.
- Se cliente fala "planilha", você fala da dor da planilha e como o sistema resolve.
- Se fala "equipe", fala de apontamento, custo por dia, diário.
- Se fala "financeiro", fala de NF com ISS/INSS, custo por obra, margem.
- Se fala "proposta", fala de BDI TCU, virar obra com 1 clique.
- Se fala "preço", você dá os preços com contexto, não seco. Explica que tem 14 dias grátis sem cartão, que pode testar direto em obrasgestao.com.
- Você sempre termina com uma pergunta inteligente que faz avançar, mas baseada no que cliente falou, não genérica. Exemplos:
  - Se falou de planilha: "Qual parte da planilha te dá mais dor hoje? Medição, financeiro ou equipe?"
  - Se falou de equipe: "Hoje você sabe quanto custa cada dia de equipe por obra?"
  - Se falou de medição: "Sua medição hoje bate certinho com o financeiro ou fica diferença?"
  - Se falou de proposta: "Sua proposta hoje já sai com BDI no padrão TCU ou calcula na mão?"
  - Se falou de solar: "Você busca a tarifa e Fio B da ANEEL na mão por CEP ou já tem automático?"

- Você pode usar sim/não quando fizer sentido, mas de forma natural: "Faz sentido pra você? Sim ou não?", "Quer que eu te mande o link? Sim ou não?", "Te interessa uma auditoria grátis do seu orçamento pra ver se tá coerente com SINAPI?"

- Nunca fale que é IA. Você é da equipe Obras Gestão.
- Nunca peça cartão. Sempre teste direto pelo site: obrasgestao.com > Ver Planos > Escolher este plano.
- Sempre "um atendente da nossa equipe", nunca nome.
- Se pedir atendente/humano/pessoa: "Claro! Vou te passar para um atendente da nossa equipe agora, ele já recebe todo seu histórico aqui. Só um segundo 😉"

- Se pedir desconto além da promoção, contrato grande, parceria: transfira para atendente.

- Você NÃO repete a mesma pergunta. Usa o histórico da conversa.

- Você é especialista: se cliente perguntar algo técnico (BDI, SINAPI, curva S, ISS/INSS, Fio B, NR-35), você responde com propriedade, porque você conhece.

OBJETIVO FINAL: Fazer o cliente entender que o Obras Gestão resolve a dor dele e levar para testar grátis 14 dias sem cartão em obrasgestao.com ou falar com um atendente.
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


# === NUMEROS DE ATENDIMENTO ===
NUMERO_ENGENHARIA = "5531984311221"  # 31 98431-1221
NUMERO_ATENDIMENTO = "5527992012689"  # 27 99201-2689
EMAIL_CONTATO = "contato@obrasgestao.com"

def notificar_atendimento(numero_cliente, historico, motivo="Cliente pediu atendente"):
    """Notifica engenharia e atendimento via WhatsApp quando precisa transferir"""
    try:
        resumo_historico = "
".join([f"{'Cliente' if m['role']=='user' else 'Bot'}: {m['content'][:100]}" for m in historico[-6:]])
        mensagem_alerta = f"""🔔 *NOVO ATENDIMENTO OBRAS GESTÃO*

*Cliente:* +{numero_cliente}
*Motivo:* {motivo}

*Últimas mensagens:*
{resumo_historico}

*Link direto:* https://wa.me/{numero_cliente}

_Responda pelo WhatsApp Business do 28 99252-5654_"""

        # Notifica Engenharia
        try:
            enviar_whatsapp(NUMERO_ENGENHARIA, mensagem_alerta)
            log(f">>> Alerta enviado para Engenharia {NUMERO_ENGENHARIA}")
        except Exception as e:
            log(f">>> Erro alerta engenharia: {e}")

        # Notifica Atendimento
        try:
            enviar_whatsapp(NUMERO_ATENDIMENTO, mensagem_alerta)
            log(f">>> Alerta enviado para Atendimento {NUMERO_ATENDIMENTO}")
        except Exception as e:
            log(f">>> Erro alerta atendimento: {e}")

        # TODO: Email fallback se não atender em 10 min - pode integrar com SendGrid/Mailgun depois
        log(f">>> Transferência registrada para {numero_cliente} - Email fallback: {EMAIL_CONTATO}")

    except Exception as e:
        log(f">>> Erro notificar_atendimento: {e}")

def deve_transferir(texto, historico):
    """Decide se realmente precisa transferir ou pode resolver na conversa"""
    texto_lower = texto.lower()
    
    # Palavras que indicam que cliente QUER MUITO falar com humano
    gatilhos_fortes = ["atendente", "humano", "pessoa real", "falar com alguém", "quero falar com pessoa", "me passa pra pessoa"]
    
    # Se cliente já pediu atendente antes e pediu de novo, transfere
    historico_texto = " ".join([m["content"].lower() for m in historico[-4:]])
    ja_pediu_atendente = "atendente" in historico_texto or "humano" in historico_texto
    
    if any(g in texto_lower for g in gatilhos_fortes):
        if ja_pediu_atendente and len(texto_lower) < 50:
            # Pediu 2 vezes, realmente quer humano
            return True, "Cliente insistiu em falar com atendente"
        # Primeira vez que pede, tenta resolver primeiro
        return False, "Primeira vez que pede atendente - tentar resolver na conversa"
    
    # Suporte - tenta resolver na conversa primeiro, só transfere se for erro crítico
    palavras_suporte_critico = ["não consigo entrar", "sistema fora do ar", "perdi meus dados", "erro crítico", "urgente", "não estou conseguindo acessar"]
    if any(p in texto_lower for p in palavras_suporte_critico):
        return True, f"Suporte crítico: {texto}"
    
    return False, "Resolver na conversa"

conversas = {}
# Controle de pausa por transferência
conversas_pausadas = {}

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
