import os, sys, time, hmac, requests
from datetime import date
from flask import Flask, request, jsonify, Response

def log(msg):
    print(msg, flush=True)

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
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
# Defina ADMIN_PASSWORD no Render para proteger o painel (usuário: admin)
ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")

log(f"ENV - PHONE:{PHONE_NUMBER_ID} GROQ:{bool(GROQ_API_KEY)} GEMINI:{bool(GEMINI_API_KEY)} WA:{bool(WHATSAPP_TOKEN)} ADMIN_PW:{bool(ADMIN_PASSWORD)}")

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

PAUSA_SEGUNDOS = 7200  # 2h de bot pausado depois que um humano assume

conversas = {}          # numero -> [{"role", "content", "autor", "ts"}]
conversas_pausadas = {} # numero -> timestamp do início da pausa
motivos_pausa = {}      # numero -> motivo da transferência
mensagens_vistas = {}   # id da mensagem Meta -> ts (evita responder duplicado)

# Datas das promoções (o "faltam X dias" é calculado na hora)
PROMO_OBRAS = date(2027, 1, 10)
PROMO_SOLAR = date(2027, 1, 31)

_SYSTEM_PROMPT = """Você é o especialista comercial do Obras Gestão, da WS Conecta Soluções Integradas LTDA.

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
0️⃣ Falar com atendente

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

Sempre termine com opções incluindo 0️⃣ Falar com atendente. Nunca vago. Curto, 2-3 linhas + opções. Emoji moderado. Nunca diga que é IA, você é da equipe. Sempre "um atendente da nossa equipe". Teste grátis sem cartão em obrasgestao.com. Se pedir atendente 2x, transfere e avisa 31 98431-1221 e 27 99201-2689.
"""


def get_system_prompt():
    """Calcula os 'faltam X dias' na hora, para nunca ficar desatualizado."""
    hoje = date.today()
    d_obras = max((PROMO_OBRAS - hoje).days, 0)
    d_solar = max((PROMO_SOLAR - hoje).days, 0)
    return (_SYSTEM_PROMPT
            .replace("54 dias", f"{d_obras} dias")
            .replace("75 dias", f"{d_solar} dias"))


# --------------------------------------------------------------------------
# IA
# --------------------------------------------------------------------------
def _msgs_limpas(historico, n=12):
    """Só role/content — campos extras (autor, ts) quebram a API da Groq."""
    return [{"role": m["role"], "content": m["content"]} for m in historico[-n:]]

def gerar_com_groq_http(historico):
    if not GROQ_API_KEY:
        raise Exception("GROQ_API_KEY vazio")
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    messages = [{"role": "system", "content": get_system_prompt()}] + _msgs_limpas(historico)
    modelos = ["openai/gpt-oss-20b", "openai/gpt-oss-120b", "qwen/qwen3-32b", "llama-3.3-70b-versatile"]
    last_error = ""
    for modelo in modelos:
        try:
            log(f">>> Tentando Groq modelo: {modelo}")
            data = {"model": modelo, "messages": messages, "temperature": 0.7, "max_tokens": 600}
            r = requests.post(url, headers=headers, json=data, timeout=25)
            log(f">>> Groq {modelo} status={r.status_code}")
            if r.status_code == 200:
                return r.json()["choices"][0]["message"]["content"]
            last_error = f"{r.status_code}: {r.text[:400]}"
            log(f">>> Falhou {modelo}: {last_error[:200]}")
        except Exception as e:
            last_error = str(e)
            log(f">>> Erro {modelo}: {e}")
    raise Exception(f"Todos modelos Groq falharam. Ultimo: {last_error}")

def gerar_com_gemini(historico):
    if not gemini_client:
        raise Exception("Gemini não configurado")
    last_msg = historico[-1]["content"]
    chat_hist = ""
    for m in historico[:-1][-6:]:
        role = "Cliente" if m["role"] == "user" else "Você"
        chat_hist += f"{role}: {m['content']}\n"
    prompt = f"{get_system_prompt()}\n\nHistórico:\n{chat_hist}\nCliente: {last_msg}\nVocê:"
    response = gemini_client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
    return response.text

FALLBACK = ("Tive um problema momentâneo aqui, mas você já pode começar seu teste grátis de 14 dias, "
            "sem cartão, em obrasgestao.com > Ver Planos. Se quiser, te passo para um atendente da nossa equipe.")

def gerar_resposta_ia(historico):
    if GROQ_API_KEY:
        try:
            resp = gerar_com_groq_http(historico)
            log(f">>> Groq OK: {resp[:150]}")
            return resp
        except Exception as e:
            log(f">>> Groq falhou: {e}")
    if gemini_client:
        try:
            resp = gerar_com_gemini(historico)
            log(f">>> Gemini OK: {resp[:150]}")
            return resp
        except Exception as e:
            log(f">>> Gemini falhou: {e}")
    return FALLBACK


# --------------------------------------------------------------------------
# WhatsApp
# --------------------------------------------------------------------------
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

def notificar_atendimento(numero):
    msg = f"🔔 Cliente +{numero} quer atendente"
    for destino in (NUMERO_ENGENHARIA, NUMERO_ATENDIMENTO):
        try:
            enviar_whatsapp(destino, msg)
        except Exception as e:
            log(f">>> Erro notificando {destino}: {e}")

def deve_transferir(texto):
    t = texto.lower().strip()
    gatilhos_diretos = ["atendente", "0", "falar com atendente", "quero atendente", "atendimento",
                        "humano", "pessoa", "falar com humano", "quero falar com humano"]
    if t in gatilhos_diretos:
        return True, f"Pediu atendente: {texto}"
    if ("atendente" in t or "humano" in t) and len(t) < 40:
        return True, f"Pediu atendente: {texto}"
    palavras_criticas = ["não consigo entrar", "sistema fora do ar", "perdi meus dados", "erro crítico",
                         "urgente", "não estou conseguindo acessar", "não funciona", "bug"]
    if any(p in t for p in palavras_criticas):
        return True, f"Suporte crítico: {texto}"
    return False, ""


# --------------------------------------------------------------------------
# Estado das conversas
# --------------------------------------------------------------------------
def add_msg(numero, role, content, autor):
    hist = conversas.setdefault(numero, [])
    hist.append({"role": role, "content": content, "autor": autor, "ts": time.time()})
    conversas[numero] = hist[-40:]

def esta_pausado(numero):
    ini = conversas_pausadas.get(numero)
    if ini is None:
        return False
    if time.time() - ini >= PAUSA_SEGUNDOS:
        conversas_pausadas.pop(numero, None)
        motivos_pausa.pop(numero, None)
        log(f">>> Pausa expirou para {numero}, bot voltou")
        return False
    return True

def pausar(numero, motivo=""):
    conversas_pausadas[numero] = time.time()
    if motivo:
        motivos_pausa[numero] = motivo


# --------------------------------------------------------------------------
# Webhook
# --------------------------------------------------------------------------
@app.route("/", methods=["GET"])
def home():
    return (f"Agente Obras Gestão no ar! Groq:{'OK' if GROQ_API_KEY else 'OFF'} "
            f"Gemini:{'OK' if gemini_client else 'OFF'} Phone:{PHONE_NUMBER_ID}")

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
    try:
        data = request.get_json(force=True, silent=True)
        if not data:
            return jsonify({"status": "empty"}), 200
        for entry in data.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                if "messages" not in value:
                    continue
                for msg in value["messages"]:
                    msg_id = msg.get("id")
                    if msg_id:
                        if msg_id in mensagens_vistas:
                            continue  # Meta reenviou o mesmo evento
                        mensagens_vistas[msg_id] = time.time()
                        if len(mensagens_vistas) > 2000:
                            for k in sorted(mensagens_vistas, key=mensagens_vistas.get)[:1000]:
                                mensagens_vistas.pop(k, None)

                    from_number = msg.get("from")
                    text_user = msg.get("text", {}).get("body", "") if msg.get("type") == "text" else ""
                    if not from_number or not text_user:
                        continue

                    log(f">>> MSG de {from_number}: {text_user}")
                    add_msg(from_number, "user", text_user, "cliente")

                    # Humano assumiu: o bot fica quieto, mas a mensagem aparece no painel
                    if esta_pausado(from_number):
                        log(f">>> {from_number} em atendimento humano, bot pausado")
                        continue

                    precisa, motivo = deve_transferir(text_user)
                    if precisa:
                        log(f">>> TRANSFERENCIA: {motivo}")
                        resposta = "Você será transferido para o atendente humano."
                        enviar_whatsapp(from_number, resposta)
                        add_msg(from_number, "assistant", resposta, "bot")
                        notificar_atendimento(from_number)
                        pausar(from_number, motivo)
                        continue

                    resposta_ia = gerar_resposta_ia(conversas[from_number])
                    add_msg(from_number, "assistant", resposta_ia, "bot")
                    enviar_whatsapp(from_number, resposta_ia)
    except Exception as e:
        import traceback
        log(f"Erro webhook: {e}\n{traceback.format_exc()}")
    return jsonify({"status": "ok"}), 200


# --------------------------------------------------------------------------
# PWA
# --------------------------------------------------------------------------
ICON = "https://cdn-icons-png.flaticon.com/512/1087/1087815.png"

@app.route("/static/manifest.json")
def manifest():
    return jsonify({
        "name": "Obras Gestão - Atendimento",
        "short_name": "Atendimento",
        "description": "Painel de atendimento do Obras Gestão",
        "start_url": "/admin",
        "scope": "/",
        "display": "standalone",
        "background_color": "#f3f1ec",
        "theme_color": "#f2a900",
        "orientation": "portrait",
        "icons": [{"src": ICON, "sizes": "512x512", "type": "image/png", "purpose": "any"}],
    })

# Service worker na raiz para poder controlar /admin
@app.route("/sw.js")
def sw():
    code = f"""
self.addEventListener('install', e => self.skipWaiting());
self.addEventListener('activate', e => e.waitUntil(clients.claim()));
self.addEventListener('notificationclick', e => {{
  e.notification.close();
  e.waitUntil(clients.matchAll({{type:'window'}}).then(list => {{
    for (const c of list) if (c.url.includes('/admin')) return c.focus();
    return clients.openWindow('/admin');
  }}));
}});
"""
    return Response(code, mimetype="application/javascript")


# --------------------------------------------------------------------------
# Painel admin
# --------------------------------------------------------------------------
@app.before_request
def proteger_admin():
    if not request.path.startswith("/admin"):
        return None
    if not ADMIN_PASSWORD:
        return None  # sem senha configurada = painel aberto (defina ADMIN_PASSWORD!)
    auth = request.authorization
    ok = (auth and hmac.compare_digest(auth.username or "", ADMIN_USER)
          and hmac.compare_digest(auth.password or "", ADMIN_PASSWORD))
    if ok:
        return None
    return Response("Acesso restrito", 401, {"WWW-Authenticate": 'Basic realm="Obras Gestão"'})

def _resumo(numero):
    hist = conversas.get(numero, [])
    ultimo = hist[-1] if hist else None
    pausado = esta_pausado(numero)
    return {
        "numero": numero,
        "pausado": pausado,
        "restante": int(PAUSA_SEGUNDOS - (time.time() - conversas_pausadas[numero])) if pausado else 0,
        "motivo": motivos_pausa.get(numero, ""),
        "total": len(hist),
        "ultimo": {"role": ultimo["role"], "autor": ultimo.get("autor", ""), "content": ultimo["content"]} if ultimo else None,
        "ts": ultimo["ts"] if ultimo else 0,
        # aguardando = humano assumiu e o cliente foi o último a falar
        "aguardando": bool(pausado and ultimo and ultimo["role"] == "user"),
    }

@app.route("/admin/api/conversas")
def api_conversas():
    itens = [_resumo(n) for n in conversas]
    itens.sort(key=lambda x: (not x["aguardando"], -x["ts"]))
    return jsonify(itens)

@app.route("/admin/api/conversa/<numero>")
def api_conversa(numero):
    r = _resumo(numero)
    r["mensagens"] = [{"role": m["role"], "autor": m.get("autor", ""), "content": m["content"], "ts": m["ts"]}
                      for m in conversas.get(numero, [])]
    return jsonify(r)

@app.route("/admin/api/responder", methods=["POST"])
def api_responder():
    d = request.get_json(silent=True) or {}
    numero, texto = d.get("numero"), (d.get("mensagem") or "").strip()
    if not numero or not texto:
        return jsonify({"erro": "numero e mensagem são obrigatórios"}), 400
    enviar_whatsapp(numero, texto)
    add_msg(numero, "assistant", texto, "humano")
    pausar(numero, motivos_pausa.get(numero, "Atendente respondeu pelo painel"))
    return jsonify({"ok": True})

@app.route("/admin/api/pausar", methods=["POST"])
def api_pausar():
    numero = (request.get_json(silent=True) or {}).get("numero")
    if numero in conversas:
        pausar(numero, "Assumido pelo painel")
    return jsonify({"ok": True})

@app.route("/admin/api/retomar", methods=["POST"])
def api_retomar():
    numero = (request.get_json(silent=True) or {}).get("numero")
    conversas_pausadas.pop(numero, None)
    motivos_pausa.pop(numero, None)
    return jsonify({"ok": True})

@app.route("/admin", methods=["GET"])
def admin_panel():
    return Response(ADMIN_HTML, mimetype="text/html")


ADMIN_HTML = r"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Atendimento · Obras Gestão</title>
<link rel="manifest" href="/static/manifest.json">
<meta name="theme-color" content="#f2a900">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="Atendimento">
<link rel="apple-touch-icon" href="https://cdn-icons-png.flaticon.com/512/1087/1087815.png">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='8' fill='%23f2a900'/%3E%3Cpath d='M7 15l9-7 9 7v9H7z' fill='%23fff'/%3E%3C/svg%3E">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Hanken+Grotesk:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
:root{
  --bg:#eceae4; --surface:#ffffff; --surface-2:#f6f5f1; --line:#dedbd2;
  --ink:#1f2630; --muted:#6b7280;
  --accent:#f2a900; --accent-ink:#2a1d00;
  --bot:#e4f3ea; --bot-ink:#123d27;
  --human:#fff1cf; --human-ink:#3a2a00;
  --client:#ffffff;
  --alert:#d92d20; --ok:#1f9d63;
  --radius:14px;
  color-scheme: light;
}
@media (prefers-color-scheme: dark){
  :root{
    --bg:#12161c; --surface:#1a2029; --surface-2:#212833; --line:#2c3541;
    --ink:#e8ecf1; --muted:#8d98a8;
    --accent:#f2b83a; --accent-ink:#2a1d00;
    --bot:#17382a; --bot-ink:#c9efdc;
    --human:#40320e; --human-ink:#ffe9b0;
    --client:#232b36;
    --alert:#f97066; --ok:#4cc38a;
    color-scheme: dark;
  }
}
*{box-sizing:border-box}
html,body{height:100%}
body{margin:0;font-family:"Hanken Grotesk",system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;
  background:var(--bg);color:var(--ink);font-size:15px;line-height:1.45;
  padding:env(safe-area-inset-top) env(safe-area-inset-right) env(safe-area-inset-bottom) env(safe-area-inset-left)}
button{font:inherit;cursor:pointer}
:focus-visible{outline:2px solid var(--accent);outline-offset:2px}

.app{display:grid;grid-template-rows:auto 1fr;height:100%}
.top{display:flex;align-items:center;gap:12px;padding:12px 18px;background:var(--surface);border-bottom:1px solid var(--line)}
.logo{width:34px;height:34px;border-radius:9px;background:var(--accent);display:grid;place-items:center;flex:none}
.logo svg{width:20px;height:20px}
.brand{font-weight:700;font-size:16px;letter-spacing:-.01em}
.brand small{display:block;font-weight:500;font-size:12px;color:var(--muted);letter-spacing:0}
.spacer{flex:1}
.pill{display:none;align-items:center;gap:6px;padding:6px 12px;border-radius:999px;background:var(--alert);color:#fff;font-weight:600;font-size:13px}
.pill.on{display:inline-flex}
.pill i{width:8px;height:8px;border-radius:50%;background:#fff;animation:blink 1.2s infinite}
@keyframes blink{50%{opacity:.25}}
.btn{border:1px solid var(--line);background:var(--surface);color:var(--ink);padding:8px 14px;border-radius:10px;font-weight:600;font-size:13px}
.btn:hover{background:var(--surface-2)}
.btn.primary{background:var(--accent);border-color:var(--accent);color:var(--accent-ink)}
.btn.primary:hover{filter:brightness(.96)}
.btn.good{background:var(--ok);border-color:var(--ok);color:#fff}
.btn[hidden]{display:none}

.main{display:grid;grid-template-columns:340px 1fr;min-height:0}
.side{display:flex;flex-direction:column;min-height:0;background:var(--surface);border-right:1px solid var(--line)}
.tools{padding:12px;display:grid;gap:10px;border-bottom:1px solid var(--line)}
.search{width:100%;padding:10px 12px;border-radius:10px;border:1px solid var(--line);background:var(--surface-2);color:var(--ink);font:inherit}
.tabs{display:grid;grid-template-columns:1fr 1fr;background:var(--surface-2);border-radius:10px;padding:3px}
.tab{border:0;background:transparent;color:var(--muted);padding:7px;border-radius:8px;font-weight:600;font-size:13px}
.tab[aria-selected=true]{background:var(--surface);color:var(--ink);box-shadow:0 1px 2px rgba(0,0,0,.12)}
.list{overflow-y:auto;flex:1}
.item{display:grid;grid-template-columns:42px 1fr auto;gap:12px;align-items:center;width:100%;text-align:left;
  padding:12px 14px;border:0;border-bottom:1px solid var(--line);background:transparent;color:inherit}
.item:hover{background:var(--surface-2)}
.item[aria-current=true]{background:var(--surface-2);box-shadow:inset 3px 0 0 var(--accent)}
.avatar{width:42px;height:42px;border-radius:50%;display:grid;place-items:center;font-weight:700;font-size:13px;
  background:var(--surface-2);border:1px solid var(--line);color:var(--muted)}
.item.wait .avatar{background:var(--alert);border-color:var(--alert);color:#fff}
.item .who{font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.item .prev{color:var(--muted);font-size:13px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.item .meta{display:grid;justify-items:end;gap:4px;font-size:12px;color:var(--muted)}
.tag{font-size:11px;font-weight:700;padding:2px 8px;border-radius:999px;background:var(--surface-2);border:1px solid var(--line);color:var(--muted)}
.tag.human{background:var(--human);border-color:transparent;color:var(--human-ink)}
.tag.wait{background:var(--alert);border-color:var(--alert);color:#fff}
.empty{padding:40px 24px;text-align:center;color:var(--muted)}
.empty b{display:block;color:var(--ink);margin-bottom:4px}

.chat{display:flex;flex-direction:column;min-height:0;min-width:0}
.chat-head{display:flex;align-items:center;gap:12px;padding:12px 18px;background:var(--surface);border-bottom:1px solid var(--line)}
.back{display:none;border:0;background:transparent;color:var(--ink);font-size:22px;padding:0 6px}
.chat-head h2{margin:0;font-size:16px;letter-spacing:-.01em}
.chat-head .sub{font-size:12px;color:var(--muted)}
.msgs{flex:1;overflow-y:auto;padding:18px;display:flex;flex-direction:column;gap:8px}
.row{display:flex}
.row.me{justify-content:flex-end}
.bubble{max-width:min(560px,82%);padding:9px 12px;border-radius:14px;white-space:pre-wrap;word-wrap:break-word;overflow-wrap:anywhere;
  box-shadow:0 1px 1px rgba(0,0,0,.06)}
.bubble.cliente{background:var(--client);border:1px solid var(--line);border-top-left-radius:4px}
.bubble.bot{background:var(--bot);color:var(--bot-ink);border-top-right-radius:4px}
.bubble.humano{background:var(--human);color:var(--human-ink);border-top-right-radius:4px}
.bubble .by{display:block;font-size:11px;font-weight:700;opacity:.75;margin-bottom:2px}
.bubble time{display:block;text-align:right;font-size:11px;opacity:.6;margin-top:3px}
.day{align-self:center;font-size:12px;color:var(--muted);background:var(--surface);border:1px solid var(--line);padding:3px 10px;border-radius:999px;margin:6px 0}
.composer{display:flex;gap:10px;align-items:flex-end;padding:12px 18px;background:var(--surface);border-top:1px solid var(--line)}
.composer textarea{flex:1;resize:none;max-height:140px;padding:10px 12px;border-radius:12px;border:1px solid var(--line);background:var(--surface-2);color:var(--ink);font:inherit}
.hint{padding:0 18px 10px;background:var(--surface);font-size:12px;color:var(--muted)}
.placeholder{flex:1;display:grid;place-items:center;text-align:center;color:var(--muted);padding:24px}
.toast{position:fixed;left:50%;bottom:24px;transform:translateX(-50%);background:var(--ink);color:var(--bg);padding:10px 16px;border-radius:10px;font-weight:600;font-size:13px;opacity:0;pointer-events:none;transition:opacity .2s}
.toast.on{opacity:1}

@media (max-width: 760px){
  .main{grid-template-columns:1fr}
  .chat{display:none}
  .main.open .side{display:none}
  .main.open .chat{display:flex}
  .back{display:block}
  .brand small,.hide-sm{display:none}
}
@media (prefers-reduced-motion: reduce){ .pill i{animation:none} }
</style>
</head>
<body>
<div class="app">
  <header class="top">
    <div class="logo"><svg viewBox="0 0 24 24" fill="#fff"><path d="M3 12l9-8 9 8v9h-6v-6H9v6H3z"/></svg></div>
    <div class="brand">Atendimento<small>Obras Gestão · WhatsApp</small></div>
    <div class="spacer"></div>
    <span id="pill" class="pill"><i></i><span id="pillTxt"></span></span>
    <button id="installBtn" class="btn hide-sm" hidden>Instalar app</button>
    <button id="notifBtn" class="btn primary" hidden>Ativar avisos</button>
  </header>

  <div id="main" class="main">
    <aside class="side">
      <div class="tools">
        <input id="busca" class="search" type="search" placeholder="Buscar número ou mensagem" aria-label="Buscar conversas">
        <div class="tabs" role="tablist">
          <button class="tab" role="tab" data-f="todos" aria-selected="true">Todas</button>
          <button class="tab" role="tab" data-f="aguardando" aria-selected="false">Aguardando <span id="cntWait"></span></button>
        </div>
      </div>
      <div id="lista" class="list"></div>
    </aside>

    <section class="chat">
      <div id="vazio" class="placeholder"><div><b style="color:var(--ink)">Selecione uma conversa</b><br>As mensagens aparecem aqui em tempo real.</div></div>
      <div id="conv" style="display:none;flex-direction:column;flex:1;min-height:0">
        <div class="chat-head">
          <button id="back" class="back" aria-label="Voltar">‹</button>
          <div>
            <h2 id="hNum"></h2>
            <div id="hSub" class="sub"></div>
          </div>
          <div class="spacer"></div>
          <a id="hWa" class="btn hide-sm" target="_blank" rel="noopener" style="text-decoration:none">Abrir no WhatsApp</a>
          <button id="btnAssumir" class="btn primary" hidden>Assumir conversa</button>
          <button id="btnRetomar" class="btn good" hidden>Devolver ao bot</button>
        </div>
        <div id="msgs" class="msgs"></div>
        <div class="composer">
          <textarea id="txt" rows="1" placeholder="Escreva como atendente. Ao enviar, o bot pausa por 2h." aria-label="Mensagem"></textarea>
          <button id="send" class="btn primary">Enviar</button>
        </div>
        <div class="hint">Enter envia · Shift+Enter quebra a linha</div>
      </div>
    </section>
  </div>
</div>
<div id="toast" class="toast" role="status"></div>

<script>
const $ = s => document.querySelector(s);
let lista = [], atual = null, filtro = 'todos', busca = '', vistos = null, ultimaAssin = '';

const fmtNum = n => {
  const m = n.match(/^55(\d{2})(\d{4,5})(\d{4})$/);
  return m ? `+55 ${m[1]} ${m[2]}-${m[3]}` : '+' + n;
};
const hhmm = ts => new Date(ts * 1000).toLocaleTimeString('pt-BR', {hour: '2-digit', minute: '2-digit'});
const curto = ts => {
  if (!ts) return '';
  const d = new Date(ts * 1000), hoje = new Date();
  return d.toDateString() === hoje.toDateString() ? hhmm(ts)
    : d.toLocaleDateString('pt-BR', {day: '2-digit', month: '2-digit'});
};
const diaLabel = ts => {
  const d = new Date(ts * 1000), hoje = new Date(), ont = new Date(Date.now() - 864e5);
  if (d.toDateString() === hoje.toDateString()) return 'Hoje';
  if (d.toDateString() === ont.toDateString()) return 'Ontem';
  return d.toLocaleDateString('pt-BR', {day: '2-digit', month: 'long'});
};
const el = (tag, cls, txt) => { const e = document.createElement(tag); if (cls) e.className = cls; if (txt != null) e.textContent = txt; return e; };
const api = (url, body) => fetch(url, body ? {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)} : {}).then(r => r.json());
function toast(t){ const x = $('#toast'); x.textContent = t; x.classList.add('on'); setTimeout(() => x.classList.remove('on'), 2200); }

/* ---------- lista ---------- */
function renderLista() {
  const box = $('#lista'); box.replaceChildren();
  const q = busca.toLowerCase();
  const itens = lista.filter(c => (filtro === 'todos' || c.aguardando) &&
    (!q || c.numero.includes(q) || (c.ultimo && c.ultimo.content.toLowerCase().includes(q))));
  if (!itens.length) {
    const e = el('div', 'empty');
    e.append(el('b', '', filtro === 'aguardando' ? 'Ninguém aguardando' : 'Nenhuma conversa ainda'),
             document.createTextNode(filtro === 'aguardando' ? 'Quando um cliente pedir atendente, ele aparece aqui.' : 'Envie um "Oi" para o número do bot para testar.'));
    box.append(e); return;
  }
  for (const c of itens) {
    const b = el('button', 'item' + (c.aguardando ? ' wait' : ''));
    if (c.numero === atual) b.setAttribute('aria-current', 'true');
    b.append(el('div', 'avatar', c.numero.slice(-2)));
    const mid = el('div');
    mid.append(el('div', 'who', fmtNum(c.numero)));
    const quem = c.ultimo ? (c.ultimo.autor === 'cliente' ? '' : (c.ultimo.autor === 'humano' ? 'Você: ' : 'Bot: ')) : '';
    mid.append(el('div', 'prev', c.ultimo ? quem + c.ultimo.content.replace(/\s+/g, ' ') : ''));
    const meta = el('div', 'meta');
    meta.append(el('span', '', curto(c.ts)));
    if (c.aguardando) meta.append(el('span', 'tag wait', 'Aguardando'));
    else if (c.pausado) meta.append(el('span', 'tag human', 'Humano'));
    b.append(mid, meta);
    b.onclick = () => abrir(c.numero);
    box.append(b);
  }
}

/* ---------- conversa ---------- */
function renderConversa(d, forcarScroll) {
  const box = $('#msgs');
  const colado = box.scrollHeight - box.scrollTop - box.clientHeight < 80;
  box.replaceChildren();
  let ultimoDia = '';
  for (const m of d.mensagens) {
    const dia = diaLabel(m.ts);
    if (dia !== ultimoDia) { box.append(el('div', 'day', dia)); ultimoDia = dia; }
    const row = el('div', 'row' + (m.autor === 'cliente' ? '' : ' me'));
    const bb = el('div', 'bubble ' + (m.autor || 'bot'));
    if (m.autor !== 'cliente') bb.append(el('span', 'by', m.autor === 'humano' ? 'Atendente' : 'Bot'));
    bb.append(document.createTextNode(m.content), el('time', '', hhmm(m.ts)));
    row.append(bb); box.append(row);
  }
  if (forcarScroll || colado) box.scrollTop = box.scrollHeight;
  $('#hNum').textContent = fmtNum(d.numero);
  $('#hSub').textContent = d.pausado
    ? `Atendimento humano · bot volta em ${Math.max(1, Math.ceil(d.restante / 60))} min${d.motivo ? ' · ' + d.motivo : ''}`
    : 'Bot respondendo automaticamente';
  $('#hWa').href = 'https://wa.me/' + d.numero;
  $('#btnAssumir').hidden = d.pausado;
  $('#btnRetomar').hidden = !d.pausado;
}

async function abrir(numero) {
  atual = numero;
  $('#vazio').style.display = 'none'; $('#conv').style.display = 'flex';
  $('#main').classList.add('open');
  renderLista();
  renderConversa(await api('/admin/api/conversa/' + numero), true);
  if (matchMedia('(min-width:761px)').matches) $('#txt').focus();
}

async function enviar() {
  const t = $('#txt').value.trim();
  if (!t || !atual) return;
  $('#send').disabled = true;
  try {
    await api('/admin/api/responder', {numero: atual, mensagem: t});
    $('#txt').value = ''; $('#txt').style.height = 'auto';
    await atualizar(true);
  } catch (e) { toast('Não foi possível enviar. Tente de novo.'); }
  $('#send').disabled = false;
}

/* ---------- polling + avisos ---------- */
function beep() {
  try {
    const a = new (window.AudioContext || window.webkitAudioContext)(), o = a.createOscillator(), g = a.createGain();
    o.connect(g); g.connect(a.destination); o.frequency.value = 880; g.gain.value = .08;
    o.start(); o.stop(a.currentTime + .18);
  } catch (e) {}
}
async function avisar(c) {
  beep();
  if (!('Notification' in window) || Notification.permission !== 'granted') return;
  const opts = {body: `${fmtNum(c.numero)} quer falar com um atendente`, icon: 'https://cdn-icons-png.flaticon.com/512/1087/1087815.png', tag: c.numero, requireInteraction: true, vibrate: [200, 100, 200]};
  try { const reg = await navigator.serviceWorker.ready; reg.showNotification('Novo atendimento', opts); }
  catch (e) { new Notification('Novo atendimento', opts); }
}

async function atualizar(forcarScroll) {
  try {
    lista = await api('/admin/api/conversas');
    const esperando = lista.filter(c => c.aguardando);
    if (vistos !== null) esperando.filter(c => !vistos.has(c.numero)).forEach(avisar);
    vistos = new Set(esperando.map(c => c.numero));
    $('#pill').classList.toggle('on', esperando.length > 0);
    $('#pillTxt').textContent = `${esperando.length} aguardando atendimento`;
    $('#cntWait').textContent = esperando.length ? `(${esperando.length})` : '';
    document.title = (esperando.length ? `(${esperando.length}) ` : '') + 'Atendimento · Obras Gestão';
    renderLista();
    if (atual) renderConversa(await api('/admin/api/conversa/' + atual), forcarScroll === true);
  } catch (e) { /* tenta de novo no próximo ciclo */ }
}

/* ---------- eventos ---------- */
$('#busca').oninput = e => { busca = e.target.value; renderLista(); };
document.querySelectorAll('.tab').forEach(t => t.onclick = () => {
  filtro = t.dataset.f;
  document.querySelectorAll('.tab').forEach(x => x.setAttribute('aria-selected', x === t));
  renderLista();
});
$('#send').onclick = enviar;
$('#txt').addEventListener('keydown', e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); enviar(); } });
$('#txt').addEventListener('input', e => { e.target.style.height = 'auto'; e.target.style.height = Math.min(e.target.scrollHeight, 140) + 'px'; });
$('#back').onclick = () => { $('#main').classList.remove('open'); atual = null; renderLista(); };
$('#btnAssumir').onclick = async () => { await api('/admin/api/pausar', {numero: atual}); toast('Bot pausado nesta conversa'); atualizar(); };
$('#btnRetomar').onclick = async () => { await api('/admin/api/retomar', {numero: atual}); toast('Bot reativado'); atualizar(); };

/* PWA */
let promptInstalar;
addEventListener('beforeinstallprompt', e => { e.preventDefault(); promptInstalar = e; $('#installBtn').hidden = false; });
$('#installBtn').onclick = async () => { if (!promptInstalar) return; promptInstalar.prompt(); await promptInstalar.userChoice; promptInstalar = null; $('#installBtn').hidden = true; };
if ('serviceWorker' in navigator) navigator.serviceWorker.register('/sw.js').catch(() => {});
if ('Notification' in window && Notification.permission === 'default') $('#notifBtn').hidden = false;
$('#notifBtn').onclick = async () => { const p = await Notification.requestPermission(); if (p === 'granted') { $('#notifBtn').hidden = true; toast('Avisos ativados'); } };

atualizar();
setInterval(atualizar, 4000);
</script>
</body>
</html>
"""

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
