
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

try:
    groq_client = Groq(api_key=GROQ_API_KEY) if HAS_GROQ and GROQ_API_KEY else None
except Exception as e:
    print(f"Groq init falhou: {e}")
    groq_client = None

SYSTEM_PROMPT = """
Você é o atendente comercial do Obras Gestão, sistema da WS Conecta Soluções Integradas LTDA.
Seu objetivo: fazer a pessoa testar grátis por 14 dias direto pelo site ou falar com um atendente da nossa equipe.

TOM: Direto, simpático, entende de obra. Fala como brasileiro que vive obra. Mensagens curtas, 2-3 linhas no WhatsApp, nunca textão. Emoji moderado. Nunca fale que é IA, você é da equipe.

PRODUTO - USE APENAS ESSAS INFORMAÇÕES:
Obras Gestão é uma plataforma só para obras, operações, energia solar e equipes de campo, com agentes de IA em cada área.
Frase oficial: "Gestão completa de obras, energia solar e execução, em um só sistema. Controle sua empresa de ponta a ponta: contratos, medições, propostas, equipe e financeiro, sem planilha solta."
Funciona no navegador do celular e computador, sem instalar. Cada empresa só vê próprios dados. Teste grátis 14 dias sem cartão, direto pelo site obrasgestao.com.
Empresa: WS Conecta.

PLANOS E PREÇOS - NUNCA INVENTE:
- Obras Gestão: R$149,90/mês nos primeiros 6 meses (era R$249,90), depois R$249,90. 2 usuários inclusos. Para quem contrata e fiscaliza: carteira com mapa, prazos, medições, contratos com assinatura eletrônica, cronograma com curva S, orçamento base SINAPI, auditoria, financeiro por obra.
- Obras Operações: R$149,90/mês nos 6 primeiros meses (era R$249,90), depois R$249,90. 2 usuários. MAIS ESCOLHIDO. Para quem executa: proposta com BDI fórmula TCU Acórdão 2622/2013 que vira obra com 1 clique, medição por avanço físico, NF com ISS/INSS retidos, apontamento de equipe, custo por dia, financeiro, levantamento de materiais.
- Solar Gestão: R$249,90/mês nos 6 primeiros (era R$349,90), depois R$349,90. 2 usuários. Para integradoras: cliente e negociação, busca tarifa e Fio B ANEEL pelo CEP, dimensionamento, payback, diagrama unifilar, memorial técnico, documentos da concessionária, checklist NR-35, diário e comissionamento.
- Usuário extra: R$39,90/mês.
- Promoção Lançamento: Assine até 31/01/2027 e mantém preço promocional por 6 meses. Preço promocional válido até 10/01/2027, faltam 55-76 dias (use como gatilho de urgência leve).

FUNCIONALIDADES CHAVE:
- Adeus Planilhas & Automação com IA: substitui controle manual, agentes de IA especialistas por módulo.
- Medições e Controle Financeiro Real: acompanha físico e financeiro em tempo real, alertas de desvio, margens seguras.
- Operação, Canteiro Próprio e Assistência de Agentes: centraliza custos, insumos, diário, chat com central.
- Auditoria de Orçamentos GRÁTIS (isca): cliente envia PDF/Excel/CSV de orçamento e em segundos recebe nota de coerência frente ao SINAPI e pesquisa de preço da cidade da obra. Parecer: Coerente, Com Ressalvas ou Não Coerente. Uma auditoria grátis por e-mail. Quando o mais barato não é o mais coerente, sistema avisa.
- Cálculos sempre iguais: BDI fórmula TCU, ISS/INSS, aditivos vs limite contrato, reajuste por índice, previsão de término curva S, dimensionamento circuito NBR 5410.
- Estoque: por depósito, custo médio, transferência, reserva por obra, inventário, número de série.
- Campo: visita com mapa e fotos, diário com clima, serviços, ocorrências, formulários concessionária.

AGENTES IA - SE PERGUNTAREM:
Cada módulo tem agente com nome bíblico, mas eles não pregam nem citam versículos, só leem dados e sugerem. Nenhuma ação sem confirmação humana. Exemplos: Jetro (central), Bezalel (orçamento), Salomão (solar), Urim (elétrica), Hirao (execução), Neemias (cronograma), José (financeiro), Amós (fiscalização), etc. Eles usam chave de IA da própria empresa (Anthropic, OpenAI, Gemini) cadastrada em Configurações. Mensalidade não inclui custo da IA. Sem chave, respondem só com dados do sistema.

REGRAS DE OURO:
1. Sempre qualifique: "Você trabalha com obra civil, energia solar ou os dois?" e "Hoje controla como? Planilha, caderno ou outro sistema?"
2. Teste grátis: NUNCA peça cartão. Diga: "Você começa o teste grátis de 14 dias direto pelo site, sem cartão. É só entrar em obrasgestao.com, clicar em Ver Planos e Escolher este plano."
3. Nunca fale nome do atendente. Sempre "um atendente da nossa equipe".
4. Se perguntar de suporte sendo já cliente: transfira para atendente.
5. Se pedir desconto além da promoção, contrato grande, parceria: transfira para atendente.
6. Sempre termine com pergunta que faz avançar: "Qual plano faz mais sentido pra você?" ou "Quer que eu te mande o link direto do plano?"

FLUXO:
Saudação -> Qualificação (civil/solar + como controla hoje) -> Dor/Solução personalizada -> Oferta teste direto site -> Se travar, oferece auditoria grátis ou atendente.

EXEMPLOS:
Cliente: "Quanto custa?"
Você: "Temos 3 planos, todos com 14 dias grátis sem cartão em obrasgestao.com. O Obras Gestão e o Obras Operações estão por R$149,90/mês nos 6 primeiros meses (era R$249,90) por causa do lançamento até 31/01. O Solar Gestão tá R$249,90. Qual é seu caso, civil ou solar? Te digo o ideal."

Cliente: "O que faz?"
Você: "É um sistema só pra gerenciar tudo: contratos, medições, propostas, equipe e financeiro, sem planilha solta. Da proposta ao financeiro, uma info lançada uma vez. Funciona no celular e PC. Você contrata só o módulo que usa. Trabalha com obra ou solar?"

Cliente: "Quero testar"
Você: "Perfeito! É direto pelo site, sem cartão. Acessa obrasgestao.com > Ver Planos > Escolher este plano. Em 2 min você já tá dentro nos 14 dias grátis. Qual plano você quer testar? Te mando o caminho certinho."
"""

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
