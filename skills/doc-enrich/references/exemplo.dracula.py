# -*- coding: utf-8 -*-
"""
Exemplo de configuração para o dracula_doc.py. Copiar para <nome>.dracula.py, ao lado do
documento, e ficar só com o que o documento pede. Tudo aqui é opcional.

O documento imaginado: "guia-integracao.md", com secções "## 1. …" a "## 12. …", marcas
[em produção] e [planeado] no texto, rótulos "**O quê:**", "**Como:**", "**Mudou em …:**",
"**A fazer:**", referências "secção 4" e identificadores "INT-12".
"""

# ---- página -------------------------------------------------------------------------------
IDIOMA = "pt"
TITULO_ABA = "Guia de integração"
SOBRETITULO = "Pagamentos · para quem integra"
VOLTAR = ("index.html", "← Documentação")

# ---- estrutura ----------------------------------------------------------------------------
NIVEL = 2
NOME_SECCAO = ("secção", "secções")
LEAD = False

# ---- estados: o que o documento marca entre parênteses rectos ------------------------------
ESTADOS = [
    {"marca": "em produção", "cor": "green", "forma": "cheio", "desc": "já responde assim hoje"},
    {"marca": "planeado", "cor": "orange", "forma": "oco", "desc": "desenho; pode mudar"},
]

# ---- rótulos: o que cada "**Rótulo:**" quer dizer neste documento --------------------------
ROTULOS = [
    ("o quê", "destaque"),
    ("como", "discreto"),
    ("mudou em", "mudou"),
    # "a fazer", "risco", "pergunta" e "em aberto" já são reconhecidos por omissão
]

# ---- referências e identificadores ---------------------------------------------------------
REFERENCIAS = [(r"[Ss]ecç(?:ão|ões)", "sec-{n}")]
IDS = [(r"INT-\d+", "pink")]

# ---- classificação escrita à mão, só com o que o texto diz ----------------------------------
TEMAS = [
    ("Primeiros passos", [1, 2, 3]),
    ("Cobrança", [4, 5, 9]),
    ("Erros e limites", [6, 7, 8]),
    ("Operação", [10, 11, 12]),
]
ETIQUETAS = {
    5: [("alerta", "Obrigatório antes de ir para produção")],   # a secção 5 di-lo por palavras suas
    11: [("calma", "Só para quem usa webhooks")],
}
FILTRO_ETIQUETA = "obrigatório antes de produção"
PONTEIROS = {4: ("fluxo", "O pagamento, passo a passo")}
GUIA_TITULO = "O essencial em duas figuras"


# ---- guia visual ---------------------------------------------------------------------------
def guia(m):
    passos = m.jornada([
        # (título, descrição em HTML, [códigos], [secções de onde saiu])
        ("Criar a sessão", "O servidor pede uma sessão de pagamento e recebe o endereço do checkout.",
         ["POST /sessions"], [4]),
        ("Pagar", "O cliente paga na página do fornecedor. Nada passa pelo teu servidor.", [], [4]),
        ("Confirmar", "O webhook chega com o resultado. Só aqui o pedido fica pago.",
         ["POST /webhooks/payment"], [5, 9]),
    ])

    svg = """
<svg class="dia" viewBox="0 0 800 110" role="img" aria-label="Uma sessão fica aberta 30 minutos; depois expira e é preciso criar outra.">
  <g class="guide"><line x1="180" y1="34" x2="180" y2="100"/><line x1="560" y1="34" x2="560" y2="100"/></g>
  <text class="tm" x="180" y="16" text-anchor="middle">createdAt</text>
  <text class="tm" x="560" y="16" text-anchor="middle">+ 30 min</text>
  <text class="tl" x="0" y="73">estado da sessão</text>
  <rect class="b b-green" x="180" y="54" width="380" height="30" rx="6"/>
  <text class="tb" x="370" y="73" text-anchor="middle">OPEN</text>
  <rect class="b b-off" x="560" y="54" width="220" height="30" rx="6"/>
  <text class="tb off" x="670" y="73" text-anchor="middle">EXPIRED</text>
</svg>"""
    validade = m.figura(svg, "Uma sessão fica aberta 30 minutos. Depois disso o checkout responde %s." % m.c("410 SESSION_EXPIRED"))

    return [
        # (âncora, título, html, subtítulo)
        ("fluxo", "O pagamento, passo a passo", passos, "As três chamadas e as secções que tratam de cada uma."),
        ("validade", "Quanto tempo vive uma sessão", validade, "Junta as %s." % m.refs_txt(4, 7)),
    ]


# ---- introdução à medida (rara; sem isto, a introdução é o texto antes da primeira secção) --
# def introducao(m, blocos):
#     return m.md("Texto de abertura em **Markdown**.") + m.legenda_estados()
