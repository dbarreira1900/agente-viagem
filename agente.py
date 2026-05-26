import os, re, json, requests
from groq import Groq

# Pega chaves do ambiente (Streamlit Secrets ou .env local)
GROQ_KEY         = os.environ.get("GROQ_API_KEY", "")
EXCHANGERATE_KEY = os.environ.get("EXCHANGERATE_KEY", "")

client = Groq(api_key=GROQ_KEY)
MODELO = "llama-3.3-70b-versatile"

# ── Helpers LLM ──────────────────────────────────────
def llm_json(prompt: str, max_tokens=2048):
    resp = client.chat.completions.create(
        model=MODELO,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3, max_tokens=max_tokens
    )
    texto = re.sub(r"```json|```", "", resp.choices[0].message.content).strip()
    return json.loads(texto)

def llm_texto(prompt: str, max_tokens=4096):
    resp = client.chat.completions.create(
        model=MODELO,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5, max_tokens=max_tokens
    )
    return resp.choices[0].message.content.strip()

# ── Ferramentas ──────────────────────────────────────
_cache_cambio = {}

def obter_cambio(moedas=["EUR","USD","GBP"]):
    chave = "_".join(sorted(moedas))
    if chave in _cache_cambio:
        return _cache_cambio[chave]
    try:
        url = f"https://v6.exchangerate-api.com/v6/{EXCHANGERATE_KEY}/latest/BRL"
        resp = requests.get(url, timeout=8).json()
        taxas = {m: round(resp["conversion_rates"][m], 4) for m in moedas}
    except:
        taxas = {"EUR": 0.17, "USD": 0.19, "GBP": 0.15}
    _cache_cambio[chave] = taxas
    return taxas

def converter_brl(valor, moeda="EUR"):
    return round(valor * obter_cambio().get(moeda, 0.17), 2)

def buscar_atracoes(cidade, perfil, limite=6):
    prompt = f"""
Liste as {limite} melhores atrações em {cidade} para: {perfil}.
Responda SOMENTE JSON: [{{"nome":"...","tipo":"...","descricao":"...","tempo_sugerido_horas":2,"custo_entrada_eur":0,"dica":"..."}}]
Responda em português do Brasil.
"""
    try:
        r = llm_json(prompt)
        return r if isinstance(r, list) else []
    except:
        return []

def estimar_transportes(origem, destinos, adultos, mes):
    roteiro = " → ".join([origem] + destinos + [origem])
    prompt = f"""
Estime transportes REALISTAS para: {roteiro} | {adultos} adulto(s) | {mes}
Responda SOMENTE JSON:
{{"voo_ida":{{"trecho":"GRU→LIS","duracao":"11h40min","escalas":0,"companhias_recomendadas":["TAP"],"preco_por_pessoa_brl":2800,"preco_total_brl":5600,"dica":"..."}},"voo_volta":{{"trecho":"LIS→GRU","duracao":"10h50min","escalas":0,"companhias_recomendadas":["TAP"],"preco_por_pessoa_brl":2600,"preco_total_brl":5200,"dica":"..."}},"transportes_internos":[{{"trecho":"Lisboa→Porto","meio":"Trem","duracao":"3h","frequencia":"várias/dia","preco_por_pessoa_eur":25,"preco_total_eur":50,"preco_total_brl":293,"dica":"..."}}],"total_voos_brl":10800,"total_internos_brl":293,"total_geral_brl":11093,"observacao":"..."}}
Use 1 EUR = 5.85 BRL. Responda em português.
"""
    try:
        return llm_json(prompt)
    except:
        return {}

# ── Função principal ─────────────────────────────────
def gerar_roteiro(origem, destinos, qtd_viajantes, perfil,
                   duracao, mes, orcamento):
    cambio       = obter_cambio()
    orcamento_eur = converter_brl(orcamento, "EUR")
    atracoes      = {c: buscar_atracoes(c, perfil) for c in destinos}
    transportes   = estimar_transportes(origem, destinos, qtd_viajantes, mes)

    # Montar textos para o prompt
    at_texto = ""
    for cidade, lista in atracoes.items():
        at_texto += f"\n{cidade}:\n"
        for a in lista:
            custo = f"€{a.get('custo_entrada_eur',0)}" if a.get('custo_entrada_eur',0) > 0 else "Grátis"
            at_texto += f"  - {a.get('nome')} ({a.get('tipo')}) | {custo} | {a.get('descricao','')}\n"

    tr = transportes
    prompt_roteiro = f"""
Crie roteiro completo de viagem:
Origem: {origem} | Destinos: {', '.join(destinos)}
Viajantes: {qtd_viajantes} — {perfil}
Duração: {duracao} dias | Período: {mes}
Orçamento: R$ {orcamento:,.0f} (≈ €{orcamento_eur:,.0f})
Voo ida: {tr.get('voo_ida',{}).get('trecho','?')} | R$ {tr.get('voo_ida',{}).get('preco_total_brl',0):,.0f}
Voo volta: {tr.get('voo_volta',{}).get('trecho','?')} | R$ {tr.get('voo_volta',{}).get('preco_total_brl',0):,.0f}
Total transportes: R$ {tr.get('total_geral_brl',0):,.0f}
Atrações disponíveis:{at_texto}

Inclua: cronograma dia a dia com horários, café/almoço/jantar com sugestões,
logística interna, bairro para hospedagem, estimativa de custos.
Use emojis. Responda em português do Brasil.
"""
    roteiro   = llm_texto(prompt_roteiro, max_tokens=4096)

    prompt_custos = f"""
Resumo financeiro: orçamento R$ {orcamento:,.0f}, {qtd_viajantes} pessoa(s), {duracao} dias.
Transportes: R$ {tr.get('total_geral_brl',0):,.0f}.
Com base no roteiro, estime hospedagem, alimentação, experiências, imprevistos.
Monte tabela com total geral e compare com orçamento. Português do Brasil.
Roteiro: {roteiro[:1500]}
"""
    custos = llm_texto(prompt_custos, max_tokens=1000)

    return roteiro, custos, transportes, cambio
