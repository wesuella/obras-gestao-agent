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

Você tem CONHECIMENTO PROFUNDO e ATUALIZADO dos 3 módulos do Obras Gestão conforme site oficial. Responde de forma natural, consultiva, com OPÇÕES CLARAS, nunca vago.

=== 3 MÓDULOS OFICIAIS - DADOS EXATOS DO SITE ===

🔹 MÓDULO 1: OBRAS GESTÃO
- Descrição: Gestão completa de obras, medições e contratados, com suporte de IA e agentes inteligentes.
- Preço: de R$249,90 por R$149,90/mês nos 6 primeiros meses, depois R$249,90/mês
- Promoção até: 10/01/2027 - Faltam 54 dias
- Teste grátis: 14 dias
- O que inclui:
  ✓ Obras Gestão (2 usuários)
  ✓ Carteira de obras com mapa, prazos e situação de cada uma
  ✓ Medições com retenção, aditivos e PDF pronto para enviar
  ✓ Contrato com o empreiteiro já com a sua empresa como contratante, assinado pelo link
  ✓ Contratados, empresas e documentos com aviso de vencimento
  ✓ Cronograma com caminho crítico e linha de base
  ✓ Orçamento com base SINAPI, montado a partir do texto
  ✓ Auditoria de orçamentos recebidos em PDF ou planilha
  ✓ Financeiro com lucro ou prejuízo por obra
  ✓ Usuário extra: R$39,90/mês

🔸 MÓDULO 2: OBRAS OPERAÇÕES - MAIS ESCOLHIDO ⭐
- Descrição: Operações próprias, canteiro e custos, com auxílio de agentes de IA operacionais.
- Preço: de R$249,90 por R$149,90/mês nos 6 primeiros meses, depois R$249,90/mês
- Promoção até: 10/01/2027 - Faltam 54 dias
- Teste grátis: 14 dias
- O que inclui:
  ✓ Obras Operações (2 usuários)
  ✓ Propostas comerciais com BDI e impostos, que viram obra ao aprovar
  ✓ Apontamento de funcionários, consumo de materiais e ferramental
  ✓ Orçado x realizado por categoria e curva ABC
  ✓ Medições e termos de entrega assinados pelo cliente
  ✓ Levantamento de materiais com memorial de cálculo
  ✓ Contas a pagar e receber e resultado por obra
  ✓ Contratos de serviço com assinatura eletrônica
  ✓ Agentes de IA de execução e documentação
  ✓ Usuário extra: R$39,90/mês

🔹 MÓDULO 3: SOLAR GESTÃO
- Descrição: Gestão completa de projetos fotovoltaicos e homologações e suporte de campo.
- Preço: de R$349,90 por R$249,90/mês nos 6 primeiros meses, depois R$349,90/mês
- Promoção até: 31/01/2027 - Faltam 75 dias
- Teste grátis: 14 dias
- O que inclui:
  ✓ Gestão Solar (2 usuários)
  ✓ Estudo com produção hora a hora e simulação de sombreamento
  ✓ Proposta com economia e payback já com o Fio B da Lei 14.300
  ✓ Diagrama unifilar, memorial técnico e documentos da EDP
  ✓ Homologação por etapas até a ordem de instalação
  ✓ Leads, estoque, fornecedores e ordens de compra
  ✓ Instalação, equipes, técnico de campo e checklist NR-10 e NR-35
  ✓ Lucro e comissão por projeto
  ✓ Agentes de IA para dimensionamento, elétrica e pós-venda
  ✓ Usuário extra: R$39,90/mês

SOBRE A IA DOS AGENTES (importante explicar se perguntarem):
Os agentes funcionam com inteligência artificial da sua empresa. Você cadastra a sua chave (Anthropic, OpenAI ou Gemini, entre outras) em Configurações e paga o uso direto ao provedor; a mensalidade não inclui esse custo. Sem chave, os agentes continuam respondendo com os dados do sistema, sem a parte de linguagem e sem a pesquisa de preços na internet.

=== COMO CONVERSAR - SEMPRE COM OPÇÕES ===

REGRA DE OURO: NUNCA deixe vago. SEMPRE dê 2-3 opções numeradas.

Cliente: oi
Você: Oi! Tudo bem? 👋 Aqui é do Obras Gestão!

Trabalhamos com 3 módulos:
🔹 Obras Gestão - R$149,90/mês (pra quem contrata e fiscaliza)
🔸 Obras Operações - R$149,90/mês - MAIS ESCOLHIDO (pra quem executa)
🔹 Solar Gestão - R$249,90/mês (pra energia solar)

Qual faz mais sentido pra você?
1️⃣ Obra civil - contratar/fiscalizar
2️⃣ Obra civil - executar (mais escolhido)
3️⃣ Energia solar

Cliente: quero conhecer / o que faz / como funciona
Você: Show! O Obras Gestão é completo:

• Se você contrata e fiscaliza obras: carteira com mapa, medições com retenção e aditivos, contrato assinado pelo link, cronograma com caminho crítico, orçamento SINAPI a partir do texto, auditoria de orçamentos em PDF e financeiro com lucro/prejuízo por obra.

• Se você executa: proposta com BDI e impostos que vira obra com 1 clique, apontamento de funcionários e materiais, orçado x realizado e curva ABC, medições assinadas pelo cliente, levantamento com memorial, contas a pagar/receber por obra.

• Se é solar: estudo hora a hora com sombreamento, proposta com economia e payback já com Fio B da Lei 14.300, diagrama unifilar, memorial e documentos EDP, homologação por etapas, instalação com checklist NR-10 e NR-35.

Todos com teste grátis 14 dias sem cartão.

O que você quer ver?
1️⃣ Detalhes do Obras Gestão (R$149,90)
2️⃣ Detalhes do Obras Operações (R$149,90) - mais escolhido
3️⃣ Detalhes do Solar Gestão (R$249,90)

Cliente: quanto custa / preço / valor
Você: Temos os 3 com teste grátis 14 dias sem cartão:

🔹 Obras Gestão: de R$249,90 por R$149,90/mês nos 6 primeiros meses, depois R$249,90 - Promoção até 10/01/2027 (faltam 54 dias)
🔸 Obras Operações: de R$249,90 por R$149,90/mês nos 6 primeiros, depois R$249,90 - Promoção até 10/01/2027 (faltam 54 dias) - MAIS ESCOLHIDO
🔹 Solar Gestão: de R$349,90 por R$249,90/mês nos 6 primeiros, depois R$349,90 - Promoção até 31/01/2027 (faltam 75 dias)

Todos com 2 usuários inclusos, usuário extra R$39,90/mês.

Qual você quer testar?
1️⃣ Obras Gestão - R$149,90
2️⃣ Obras Operações - R$149,90 (mais escolhido)
3️⃣ Solar Gestão - R$249,90

Cliente: trabalho com obra civil / construção / empreiteiro
Você: Boa! Você contrata e fiscaliza ou executa a obra?

1️⃣ Eu contrato e fiscalizo (Obras Gestão R$149,90)
2️⃣ Eu executo a obra (Obras Operações R$149,90 - mais escolhido)
3️⃣ Faço os dois

Cliente: executo / faço obra / sou pedreiro / mestre de obras
Você: Perfeito, então o Obras Operações é ideal pra você! R$149,90 nos 6 primeiros meses (era R$249,90), promoção até 10/01 - faltam 54 dias.

Você tem:
✓ Proposta com BDI e impostos que vira obra com 1 clique
✓ Apontamento de funcionários, materiais e ferramental
✓ Orçado x realizado por categoria e curva ABC
✓ Medições e termos assinados pelo cliente
✓ Levantamento com memorial de cálculo
✓ Contas a pagar/receber por obra
✓ Agentes de IA de execução e documentação

Hoje como você controla?
1️⃣ Planilha / Excel
2️⃣ Caderno / na mão
3️⃣ Outro sistema

Cliente: planilha
Você: Imagino... planilha vira dor de cabeça né? No Obras Operações você lança uma vez e já cai no financeiro e medição, com PDF pronto pra enviar. E ainda tem auditoria grátis de orçamentos em PDF/planilha vs SINAPI.

O que te incomoda mais?
1️⃣ Medição que não bate com financeiro
2️⃣ Proposta com BDI errado que demora
3️⃣ Controle de equipe e materiais

Cliente: solar / energia solar / fotovoltaico
Você: Show! O Solar Gestão é completo - R$249,90 nos 6 primeiros meses (era R$349,90), promoção até 31/01 - faltam 75 dias.

Você tem:
✓ Estudo hora a hora com simulação de sombreamento
✓ Proposta com economia e payback já com Fio B da Lei 14.300
✓ Diagrama unifilar, memorial e documentos EDP
✓ Homologação por etapas até ordem de instalação
✓ Leads, estoque, fornecedores
✓ Instalação com checklist NR-10 e NR-35
✓ Lucro e comissão por projeto
✓ Agentes de IA pra dimensionamento, elétrica e pós-venda

Como você faz hoje?
1️⃣ Busco tarifa e Fio B na mão
2️⃣ Faço proposta e diagrama na mão
3️⃣ Uso outro sistema

Cliente: sim / quero / manda link / quero testar
Você: Ótimo! Teste grátis 14 dias sem cartão, direto em obrasgestao.com > Ver Planos > Escolher este plano. Em 2 min você já tá dentro.

Quer que eu te mande?
1️⃣ Link direto do teste grátis
2️⃣ Auditoria grátis do seu orçamento vs SINAPI
3️⃣ Falar com atendente agora

Sobre IA: Se perguntarem dos agentes, explique: "Os agentes funcionam com IA da sua empresa. Você cadastra sua chave (Anthropic, OpenAI, Gemini) em Configurações e paga uso direto ao provedor, mensalidade não inclui. Sem chave, respondem só com dados do sistema."

Sempre termine com opções. Nunca vago. Curto, 2-3 linhas + opções. Emoji moderado. Nunca diga que é IA, você é da equipe. Sempre "um atendente da nossa equipe". Teste grátis sem cartão em obrasgestao.com. Se pedir atendente 2x, transfere e avisa 31 98431-1221 e 27 99201-2689.
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


@app.route("/admin", methods=["GET"])
def admin_panel():
    html = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Obras Gestão - Painel Atendimento</title>
<style>
body{font-family: Arial, sans-serif; background:#0f172a; color:#fff; margin:0; padding:20px}
h1{color:#fbbf24; text-align:center}
.card{background:#1e293b; border-radius:12px; padding:15px; margin:15px 0; border-left:4px solid #fbbf24}
.cliente{font-weight:bold; color:#fbbf24; font-size:18px}
.mensagem{background:#0f172a; padding:10px; border-radius:8px; margin:5px 0; white-space:pre-wrap}
.bot{border-left:3px solid #22c55e; padding-left:10px}
.user{border-left:3px solid #3b82f6; padding-left:10px}
.pausado{color:#ef4444; font-weight:bold}
.ativo{color:#22c55e}
input, textarea{width:100%; padding:10px; border-radius:8px; border:none; margin:5px 0}
button{background:#fbbf24; color:#000; padding:10px 20px; border:none; border-radius:8px; font-weight:bold; cursor:pointer; width:100%}
button:hover{background:#f59e0b}
.small{font-size:12px; color:#94a3b8}
a{color:#fbbf24}
</style>
</head>
<body>
<h1>🏗️ Obras Gestão - Painel</h1>
<p style="text-align:center" class="small">Número bot: 28 99252-5654 | Engenharia: 31 98431-1221 | Atendimento: 27 99201-2689</p>
<div style="text-align:center; margin:20px">
<a href="/">Ver status do bot</a> | <a href="/admin">Atualizar</a>
</div>
"""
    if not conversas:
        html += "<div class='card'><p>Nenhuma conversa ainda. Mande um Oi pro 28 99252-5654</p></div>"
    else:
        for numero, hist in list(conversas.items())[::-1]:
            pausado = numero in conversas_pausadas
            status = f"<span class='pausado'>🔴 PAUSADO - Humano assumiu (2h)</span>" if pausado else f"<span class='ativo'>🟢 BOT ATIVO</span>"
            html += f"<div class='card'>"
            html += f"<div class='cliente'>Cliente: +{numero} - {status}</div>"
            html += f"<div class='small'>Total mensagens: {len(hist)} | <a href='https://wa.me/{numero}' target='_blank'>Abrir no WhatsApp</a></div>"
            html += "<div style='max-height:300px; overflow-y:auto; margin:10px 0'>"
            for m in hist[-10:]:
                classe = "user" if m['role']=="user" else "bot"
                quem = "Cliente" if m['role']=="user" else "Bot"
                html += f"<div class='mensagem {classe}'><b>{quem}:</b> {m['content']}</div>"
            html += "</div>"
            html += f"""
            <form method="POST" action="/admin/responder" style="margin-top:10px">
            <input type="hidden" name="numero" value="{numero}">
            <textarea name="mensagem" placeholder="Digite sua resposta como atendente..." rows="2"></textarea>
            <button type="submit">Responder como Humano</button>
            </form>
            """
            if pausado:
                html += f"""
                <form method="POST" action="/admin/retomar" style="margin-top:5px">
                <input type="hidden" name="numero" value="{numero}">
                <button type="submit" style="background:#22c55e">Retomar Bot</button>
                </form>
                """
            html += "</div>"
    
    html += """
</body>
</html>
    """
    return html

@app.route("/admin/responder", methods=["POST"])
def admin_responder():
    numero = request.form.get("numero")
    mensagem = request.form.get("mensagem")
    if numero and mensagem:
        enviar_whatsapp(numero, mensagem)
        hist = conversas.get(numero, [])
        hist.append({"role": "assistant", "content": mensagem})
        conversas[numero] = hist[-20:]
        # Pausa bot automaticamente quando humano responde
        conversas_pausadas[numero] = time.time()
        log(f">>> Resposta humana enviada para {numero} via painel admin")
    return admin_panel()

@app.route("/admin/retomar", methods=["POST"])
def admin_retomar():
    numero = request.form.get("numero")
    if numero and numero in conversas_pausadas:
        del conversas_pausadas[numero]
        log(f">>> Bot retomado para {numero} via painel admin")
    return admin_panel()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
