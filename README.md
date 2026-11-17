
# Agente DUAL Obras Gestão - Gemini + Groq

Configuração inteligente com failover automático.

## Como funciona:
1. Tenta responder com GEMINI (seu principal)
2. Se Gemini falhar, cair ou bater limite -> usa GROQ automaticamente
3. Se os dois falharem -> manda mensagem padrão com link do teste

## Vantagens:
- Nunca fica fora do ar
- Você usa cota grátis dos dois
- 100% grátis: Gemini grátis + Groq grátis + WhatsApp 1000 conversas grátis + Render grátis

## Setup na Render:
Variáveis:
- GEMINI_API_KEY (obrigatória - você já tem)
- GROQ_API_KEY (opcional mas recomendada - cria em groq.com em 1 min)
- WHATSAPP_TOKEN, PHONE_NUMBER_ID (quando liberar seu portfólio empresarial)
- VERIFY_TOKEN=obrasgestao123

## Teste:
GET / -> mostra status de cada provedor
