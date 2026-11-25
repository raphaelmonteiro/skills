# Configuração e peças do guia visual

A configuração é um ficheiro Python, `<nome>.dracula.py`, ao lado do documento. O motor
carrega-o sozinho quando existe. Tudo é opcional: o que não for declarado fica com a regra por
omissão. Exemplo completo em `exemplo.dracula.py`.

Índice: [Página](#página) · [Estrutura](#estrutura) · [Estados](#estados) · [Rótulos](#rótulos) ·
[Referências e identificadores](#referências-e-identificadores) · [Classificação](#classificação) ·
[Funções](#funções) · [Peças do guia](#peças-do-guia-visual) · [SVG](#diagramas-em-svg) ·
[Classes úteis](#classes-úteis)

## Página

| Chave | Valor | Por omissão |
|---|---|---|
| `IDIOMA` | `"pt"` ou `"en"`: língua dos textos da interface (filtro, índice, rodapé) | `"pt"` |
| `TITULO_ABA` | nome da página no separador e na barra lateral; 2 a 4 palavras | o `# título` |
| `SOBRETITULO` | linha pequena por cima do título ("Pagamentos · guia da API") | nenhuma |
| `VOLTAR` | `("ficheiro.html", "← Texto do link")`: link de volta; só existe no ficheiro local | nenhum |
| `FACTOS` | lista de frases em HTML para a linha de factos por baixo do título | n.º de secções, data e nome da fonte |
| `INTRO_TITULO` | nome da introdução na barra lateral | "Introdução" |

## Estrutura

| Chave | Valor | Por omissão |
|---|---|---|
| `NIVEL` | nível de cabeçalho que vira painel (2 = `##`, 3 = `###`). Os níveis acima viram divisórias e grupos na barra lateral; os de baixo, subtítulos dentro do painel | 2 se houver dois ou mais `##` |
| `NOME_SECCAO` | `("nota", "notas")`: como se chama cada painel. Entra nas âncoras (`nota-12`), no contador e nas referências | `("secção", "secções")`, âncoras `sec-12` |
| `PREFIXO` | prefixo das âncoras, se não for o nome | o nome, sem acentos |
| `OMITIR` | lista de títulos de secção que não entram na página | "Sumário", "Índice", "Contents" e parecidos |
| `LEAD` | `True`: o primeiro parágrafo de cada painel fica mais discreto (bom quando é sempre "Origem: …") | `False` |
| `CARTOES` | `{secção: "prefixo"}`: a lista numerada dessa secção vira cartões com âncoras `prefixo-N` | nenhum |

Uma secção identifica-se, em todas as chaves, pelo número (`12`) ou pela âncora (`"req-7"`,
`"contexto"`). O título "## 12. Nome" dá o número 12; "## §3. Nome" dá 3; um título que começa por
um identificador declarado em `IDS` ("### REQ-7 · Nome") usa-o como âncora e como etiqueta do painel.
Secções sem número recebem como âncora o título sem acentos.

## Estados

Para documentos que marcam no texto em que pé está cada coisa.

```python
ESTADOS = [
    {"marca": "existente", "cor": "green", "forma": "cheio", "desc": "já está em produção"},
    {"marca": "implementado, não publicado", "cor": "cyan", "forma": "meio", "curto": "implementado"},
    {"marca": "proposto", "cor": "orange", "forma": "oco"},
    {"id": "aberta", "rotulo": "aberta", "padrao": r"· aberta\s*$", "onde": "titulo", "cor": "pink"},
]
```

- `marca`: o texto dentro de parênteses rectos. `[proposto]` e `[proposto, v2]` viram uma pílula;
  o que vem depois da vírgula fica na pílula, mais discreto.
- `padrao` em vez de `marca`: expressão regular para estados que não estão entre parênteses
  rectos. Não muda o texto; só marca a secção (pontos na barra lateral, filtro). `onde`:
  `"titulo"` ou `"texto"`.
- `cor`: `green`, `cyan`, `orange`, `pink`, `purple`, `red`, `yellow`, `muted`.
- `forma`: `cheio`, `meio`, `oco`. Dar formas diferentes a estados diferentes, para não depender só da cor.
- `curto`: rótulo no botão do filtro. `desc`: frase para a legenda (`m.legenda_estados()`).

Cada painel mostra os estados que contém, a barra lateral mostra um ponto por estado e o filtro
ganha um botão por estado.

## Rótulos

Um item de lista que começa por negrito terminado em dois pontos (`- **Decisão:** texto`) tem um
rótulo. `ROTULOS` diz o que cada rótulo quer dizer:

```python
ROTULOS = [
    ("o quê", "destaque"),
    ("como", "discreto"),
    ("revista a", "mudou"),
    ("o que o cliente tem de fazer", "fazer"),
]
```

A chave é o **início** do rótulo, em minúsculas. Tipos:

| Tipo | Aspeto | Para |
|---|---|---|
| `mudou` | caixa amarela, ↻ | o que mudou numa revisão |
| `fazer` | caixa roxa, ✓ | trabalho a fazer, próximos passos |
| `pergunta` | caixa rosa, ? | perguntas a quem lê |
| `aberto` | caixa laranja tracejada, ◇ | em decisão, pendente |
| `risco` | caixa vermelha, ! | riscos, avisos, o que bloqueia |
| `info` | caixa ciano, i | notas, contexto |
| `ok` | caixa verde, ◆ | decisões tomadas, respostas |
| `destaque` | rótulo pequeno em maiúsculas, texto mais claro | o resumo da secção |
| `discreto` | rótulo pequeno em maiúsculas, a roxo | o corpo normal da secção |
| `titulo` | subtítulo simples | tudo o resto; serve também para **desligar** um destaque por omissão |

Já vêm reconhecidos, sem configurar: revista/atualização/updated → `mudou`; a fazer/próximos
passos/todo/next steps → `fazer`; pergunta/dúvida/question → `pergunta`; em decisão/em
aberto/pendente/pending → `aberto`; risco/atenção/aviso/cuidado/bloqueia/warning → `risco`;
nota/dica/contexto/note/tip → `info`; decisão/resposta/resolvido/feito/done → `ok`. A
configuração vem primeiro. `ROTULOS_PADRAO = False` desliga a lista por omissão.

Quando, na lista de cima de uma secção, pelo menos um item tem rótulo conhecido ou é grande
(mais de um bloco, ou mais de 220 caracteres), a lista toda vira blocos com título em vez de
marcas. Em listas aninhadas só os tipos com caixa mudam de aspeto. Citações (`> **Nota:** …`) e
alertas do GitHub (`> [!WARNING]`) seguem as mesmas regras.

## Referências e identificadores

```python
REFERENCIAS = [
    (r"[Nn]otas?", "nota-{n}"),              # "nota 12", "notas 1, 2 e 5", "notas 30 a 34"
    (r"[Pp]erguntas?", "pergunta-{n}"),      # âncoras criadas por CARTOES
    {"palavra": "§", "ancora": "sec-{n}", "sep": ""},   # "§13", colado ao número
]
IDS = [(r"REQ-\d+", "pink"), (r"ADR-\d+", "orange"), (r"(?:BUG|TASK)-\d+", "muted")]
```

- `REFERENCIAS`: palavra (expressão regular) seguida de um número ou de uma lista de números. Só
  vira link o que tiver âncora na página; o resto fica como texto. Por omissão, com secções
  numeradas, o nome da secção já funciona ("secção 3", ou "nota 3" com `NOME_SECCAO`).
- `IDS`: identificadores que ganham forma de etiqueta. Quando um identificador **abre** um título
  de secção, um subtítulo ou o título de um cartão, esse sítio passa a ser a definição dele e
  todas as outras menções ligam para lá.

Cada painel lista, em "Liga com", as secções que cita e as que o citam.

## Classificação

Escrita por ti, não vem do Markdown. Só com base no que o texto diz.

```python
TEMAS = [("Primeiros passos", [1, 2, 3, 29]), ("Cobrança", [11, 22])]
ETIQUETAS = {
    30: [("alerta", "Bloqueia a publicação")],
    14: [("calma", "Nenhuma ação necessária")],
}
FILTRO_ETIQUETA = "bloqueia a publicação"     # botão do filtro para as secções com "alerta"
PONTEIROS = {2: ("fluxo", "O caminho, passo a passo")}   # secção -> figura do guia que a resume
FIGURAS = {34: "<figure class='fig'>…</figure>"}    # HTML posto a seguir ao 1.º parágrafo da secção
TEMAS_TITULO, TEMAS_NOTA = "Notas por tema", "As notas estão numeradas pela ordem em que foram escritas…"
GUIA_TITULO = "O essencial em quatro figuras"
```

`TEMAS` cria a figura "Por tema" no guia e uma etiqueta com o tema em cada painel. O gerador
avisa de nada se uma secção ficar sem tema: conferir à mão quando o documento crescer.

## Funções

```python
def introducao(m, blocos):
    """Substitui a introdução (o que vem antes da primeira secção). Devolve HTML."""
    return '<p class="intro-lead">' + m.inline(blocos[0]["text"]) + "</p>" + m.legenda_estados()

def guia(m):
    """Devolve as figuras do guia: [(âncora, título, html, subtítulo opcional)]."""
    return [("jornada", "O caminho, passo a passo", m.jornada([...]), "Uma frase a dizer o que a figura mostra.")]
```

`blocos` é a árvore do Markdown: dicionários com `t` igual a `p` (`text`), `list` (`ordered`,
`items` com `blocks`), `quote` (`blocks`), `code`, `table`, `h`. Sem `introducao`, a introdução é
o texto antes da primeira secção seguido da legenda dos estados.

Âncoras das figuras: letras minúsculas, algarismos e hífenes. Evitar `settings`, `sidebar`,
`customize`, `upgrade`, `downloads`.

## Peças do guia visual

Todas devolvem HTML. `m` é o motor.

| Peça | Para | Argumentos |
|---|---|---|
| `m.jornada(passos)` | sequência de passos com linha de ligação | `[(título, descrição_html, [códigos], [secções])]` |
| `m.escada(linhas, alternativa=False)` | ordem de decisão "se isto → aquilo" | `[(marca, condição_html, resultado, detalhe_html)]`; `alternativa=True` para os casos à parte, a tracejado |
| `m.fluxo_cartoes(cartoes)` | 2 a 4 etapas lado a lado, com setas | `[(título, corpo_html, destaque)]`; o último costuma ser o destaque |
| `m.pares(linhas)` | condições soltas, chave e valor | `[(chave, valor_html)]` |
| `m.tabela(cabecalho, linhas)` | tabela de consulta | células já em HTML |
| `m.linha_tempo(entradas)` | histórico em lista | `[(data, html)]` |
| `m.figura(conteudo, legenda, rolavel=True)` | moldura com legenda, para SVG | o `<svg>` e a legenda |
| `m.callout(tipo, titulo, corpo_html)` | caixa de destaque | tipos da tabela de rótulos |
| `m.legenda_estados()` | cartões com cada estado, a descrição e em quantas secções aparece | |

Para escrever o conteúdo:

| Função | Devolve |
|---|---|
| `m.c("GET /rota")` | código em linha, com o método HTTP colorido; `m.c("409 NOME")` separa o status do código |
| `m.ref(12)` / `m.ref(12, "texto")` | link para a secção: "nota 12" |
| `m.refs_txt(1, 2, 5)` | "notas 1, 2 e 5", cada número com link |
| `m.inline("texto **md** com `código`")` | Markdown em linha → HTML, com estados, referências e identificadores |
| `m.md("parágrafos e listas em md")` | Markdown em bloco → HTML |
| `m.pilula("proposto", "v2")` | uma pílula de estado |
| `m.sec(12)` | a secção: `.key`, `.chip`, `.titulo`, `.estados`, `.refs` |
| `m.seccoes` | todas as secções, pela ordem do documento |

Dentro de `fluxo_cartoes`, o corpo aceita `<ul>`, `<p class="gate-l gate-block">Bloqueia</p>`,
`<p class="gate-l gate-rec">Recomendado</p>` e `<p class="gate-n">` para a nota de rodapé.

## Diagramas em SVG

Escrever o `<svg>` à mão e embrulhar em `m.figura(svg, legenda)`. As cores vêm de classes, para
seguirem o tema:

```html
<svg class="dia" viewBox="0 0 800 200" role="img" aria-label="O que a figura mostra, numa frase.">
  <g class="guide"><line x1="180" y1="40" x2="180" y2="190"/></g>      <!-- guias verticais tracejadas -->
  <text class="tm" x="180" y="18" text-anchor="middle">requestedAt</text>  <!-- marco, mono forte -->
  <text class="ts" x="180" y="34" text-anchor="middle">o pedido nasce</text> <!-- legenda pequena -->
  <text class="tl" x="0" y="83">o que o cliente vê</text>                  <!-- nome de pista -->
  <rect class="b b-purple" x="180" y="64" width="300" height="30" rx="6"/> <!-- barra -->
  <text class="tb" x="330" y="83" text-anchor="middle">PENDING ou READY</text> <!-- texto na barra -->
</svg>
```

- Texto: `tm` (marco, mono 12 px forte), `ts` (11 px discreto), `tl` (12,5 px discreto), `tl2`
  (13 px forte), `tk` (mono 11 px discreto), `tb` (mono 11,5 px, dentro de barras), `tb off`.
- Barras: `b` com `b-purple`, `b-green`, `b-orange`, `b-cyan`, `b-yellow`, `b-pink`, `b-red`,
  `b-plain` (neutra) ou `b-off` (tracejada, "nada aqui").
- Linhas: `axis`, `axis axis-dash`, `arrow` (com `arrow-head` para o triângulo), grupo `guide`.
- Marcos: `mk-push` (círculo rosa), `mk-chat` (quadrado ciano); servem para dois tipos de evento.
- `viewBox` até 800 de largura. A figura tem largura mínima de 640 px e desliza de lado no
  telemóvel, por isso o texto nunca encolhe abaixo do legível.
- Uma figura, uma afirmação. A legenda diz o que a figura mostra; o `aria-label` diz o mesmo.
- Antes de gerar, fazer as contas: largura do texto ≈ n.º de caracteres × 7 (mono 12 px) ou × 6
  (texto 11 px); tem de caber na barra e não tocar no rótulo vizinho. Usar uma cor só onde ela
  quer dizer alguma coisa.

## Classes úteis

Para HTML escrito à mão em `introducao`, `guia` ou `FIGURAS`:

- `.latest` com `.latest-k`: cartão "última atualização"; `<details class="older">` para o resto.
- `.kinds` > `.kind.c-yellow` (`<i>↻</i><span><b>Nome</b> explicação</span>`): legenda de tipos de bloco.
- `.conv`: parágrafo discreto de convenções.
- `.fig.fig-inline` > `.half` > `.half-row` com `.half-dots` (`<i class="on">`), texto e
  `.half-v.half-ok` / `.half-no`: comparação "conta / não conta" com pontos.
- `.fig-note`: nota por baixo de uma figura.
- `.tag.tag-gate`, `.tag.tag-calm`, `.tag.tag-theme`: etiquetas soltas.
- Cores em qualquer elemento: `c-green`, `c-cyan`, `c-orange`, `c-pink`, `c-purple`, `c-red`,
  `c-yellow`, `c-muted` definem `--c`.
