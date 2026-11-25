---
name: doc-enrich
description: Enriquece um documento Markdown ou HTML, transformando-o numa página HTML profissional em tema Dracula, confortável de ler — barra lateral com índice, um painel por secção, estados e avisos coloridos, referências clicáveis, filtro e, quando ajuda, um guia visual com diagramas — sem reescrever uma palavra do texto. Use sempre que o utilizador pedir para "enriquecer" um documento ou deixá-lo "bonito", "rico", "profissional", "apresentável", "confortável de ler", "em Dracula", pedir uma versão HTML de um .md para mandar ao time, ou chamar /doc-enrich, mesmo que não diga a palavra Dracula. Não usar para escrever um documento novo do zero, para slides, nem para landing pages.
argument-hint: <caminho do documento> [o que destacar ou para quem é]
---

# Documento em tema Dracula

Objetivo: pegar num documento que já existe e entregar uma página que se lê bem, sem mudar o que
ele diz. **O texto é do autor; a página é tua.** Quem lê a versão bonita tem de poder confiar que
ela diz exatamente o mesmo que o original, porque estes documentos costumam ser contratos entre
equipas. Por isso o trabalho não é reescrever: é organizar, pintar e ligar.

Responder na língua do utilizador.

## O que sai

- `<nome>-dracula.html`, ao lado do documento. Abre sozinho num browser, sem servidor.
- `<nome>.dracula.py`, ao lado do documento, só quando o documento precisar de configuração.
  Fica lá para que da próxima vez baste um comando.
- O original não se toca, nem outros ficheiros com o mesmo nome (`<nome>.html` pode já existir e
  outras páginas podem ligar para ele).
- **Não publicar como artifact por iniciativa própria.** Gravar o ficheiro e, no fim, dizer numa
  linha que dá para publicar. Só publicar se o utilizador pedir (ver "Publicar").

## Ferramentas da skill

- `scripts/dracula_doc.py`: o motor. Lê o Markdown, monta a página e confere que nenhuma palavra se
  perdeu. Não o copies para o projeto; chama-o pelo caminho da skill.
- `scripts/html2md.py`: converte HTML em Markdown, para quando não existe fonte em Markdown.
- `references/configuracao.md`: todas as chaves da configuração e as peças para o guia visual.
  Ler antes de escrever a primeira configuração.
- `references/exemplo.dracula.py`: uma configuração completa e comentada, para copiar e adaptar.

## Passos

### 1. Encontrar a fonte

O motor trabalha a partir de Markdown. Se o utilizador apontar para um HTML, procurar primeiro a
fonte dele: um `.md` com o mesmo nome na mesma pasta, ou um nome citado no próprio HTML ("versão
HTML de x.md"). Um HTML gerado costuma ter pior estrutura do que a fonte (blocos de código
partidos, listas achatadas), por isso a fonte vale sempre mais.

Só se não houver Markdown, converter:

```bash
python3 <skill>/scripts/html2md.py doc.html <scratchpad>/doc.md
```

e seguir a partir desse `.md`, com `--saida` e `--config` a apontar para a pasta do documento.
Dizer ao utilizador, no fim, que a página saiu do HTML e não de uma fonte em Markdown.

### 2. Ler o documento inteiro

Ler tudo, não só o início. A classificação das secções e o guia visual dependem de perceber o
conteúdo; a análise automática do passo seguinte só conta padrões, não percebe o que eles querem
dizer. Num documento grande, ler por partes até ao fim.

### 3. Tirar o retrato e gerar sem configuração

```bash
python3 <skill>/scripts/dracula_doc.py doc.md --analisar
python3 <skill>/scripts/dracula_doc.py doc.md
```

O retrato mostra o que se repete no documento: níveis de cabeçalho, rótulos em negrito, marcas
entre parênteses rectos, identificadores, referências do tipo "nota 12". A geração sem
configuração já dá uma página completa: painéis, índice, tabelas, código, listas de tarefas,
destaques para rótulos comuns ("Decisão:", "Risco:", "Pergunta:") e filtro por texto.

Abrir o resultado antes de configurar. Para um documento curto e simples isto pode ser o fim: não
inventar configuração que o documento não pede.

### 4. Escrever a configuração

Criar `<nome>.dracula.py` com o que o retrato e a leitura mostraram. Cada chave responde a uma
pergunta sobre este documento:

| Pergunta | Chave |
|---|---|
| Os painéis são os `##` ou os `###`? Como se chama cada um ("nota", "decisão")? | `NIVEL`, `NOME_SECCAO` |
| O documento marca estados no texto, como `[existente]` ou "· aberta" no título? | `ESTADOS` |
| Que rótulos em negrito se repetem e o que querem dizer (mudou, a fazer, pergunta, em aberto, risco)? | `ROTULOS` |
| O texto refere outras secções por número ("nota 12", "§13")? | `REFERENCIAS` |
| Há identificadores que se repetem (`REQ-7`, `BUG-42`)? | `IDS` |
| As secções agrupam-se por assunto de forma diferente da ordem em que estão? | `TEMAS` |
| Há secções de que depende alguma coisa, ou que dizem que não há nada a fazer? | `ETIQUETAS` |
| Uma lista numerada merece cartões (perguntas, passos)? | `CARTOES` |

Os detalhes e os valores possíveis estão em `references/configuracao.md`.

Duas regras para a configuração:

- **Classificar só com o que o texto diz.** Uma etiqueta "bloqueia o lançamento" só entra se a
  secção o disser por palavras suas. A classificação é tua e fica à vista de quem lê; se for
  inventada, a página passa a dizer mais do que o documento.
- **Declarar só o que existe.** Um estado ou um rótulo que aparece uma vez não precisa de cor.
- **Ligar só o que aponta para dentro.** O retrato mostra "nota 12" ou "§13" muitas vezes, mas
  isso pode ser uma referência a outro documento. Antes de pôr um padrão em `REFERENCIAS`,
  confirmar no texto que o número é de uma secção deste documento; senão o link leva o leitor
  ao sítio errado com toda a confiança.
- **Usar as palavras do documento.** Se ele escreve "seção", o nome em `NOME_SECCAO` é "seção":
  é esse nome que aparece no contador, nas ligações e no guia.

### 5. Guia visual, quando ajuda

Um guia visual é uma parte no topo da página, antes das secções, com figuras que mostram o que no
texto está espalhado. Vale a pena quando o leitor teria de juntar várias secções para perceber
uma coisa só. Perguntas que costumam dar uma boa figura:

- Há uma sequência no tempo ou um caminho com passos? → `m.jornada(...)` ou uma linha do tempo em SVG.
- Há uma ordem de decisão ("se isto, mostra aquilo; senão…")? → `m.escada(...)`.
- Há condições antes de ligar ou publicar alguma coisa? → `m.fluxo_cartoes(...)` e `m.pares(...)`.
- Há valores, códigos ou erros espalhados que o leitor vai querer consultar juntos? → `m.tabela(...)`.
- As secções têm uma arrumação por assunto diferente da numeração? → `TEMAS`.

Regras do guia, e porquê:

- **Tudo o que a figura afirma tem de estar no texto**, e cada figura aponta para as secções de
  onde saiu (`m.ref(n)`, `m.refs_txt(...)`). O leitor tem de conseguir conferir.
- **Não fixar na figura o que muda depressa** (estados, datas, "por aprovar"). O texto das secções
  atualiza-se quando o Markdown muda; uma figura escrita à mão não. Dizer onde está o estado em
  vez de o repetir.
- **Menos figuras, melhores.** Três figuras que mostram um mecanismo valem mais do que oito que
  repetem títulos. Se uma frase diz o mesmo mais depressa, não desenhar.
- O motor acrescenta sozinho a frase "resumo feito a partir do documento; em caso de dúvida vale
  o texto original". Não a retirar: é ela que separa o que é do autor do que é teu.

Documento curto, linear, ou que já é ele próprio um resumo: sem guia.

Nos SVG, conferir as contas antes de gerar: cada rótulo cabe na sua caixa (cerca de 7 px por
carácter em mono de 12 px, 6 px em texto de 11 px) e dois rótulos vizinhos não se sobrepõem.

### 6. Gerar e conferir

```bash
python3 <skill>/scripts/dracula_doc.py doc.md
```

A última linha tem de dizer `conferência do texto: OK, nada se perdeu`. O motor compara as
palavras de cada secção do Markdown com as do painel correspondente, pela mesma ordem.

Se falhar, a causa está na página, não no documento: uma secção omitida sem querer, uma
construção de Markdown que o motor não percebeu. Corrigir a configuração ou contornar no motor.
**Nunca editar o documento de origem para a conferência passar.**

Ler também os avisos e a linha das enumerações: o motor separa "(a) … (b) …" escritos dentro de
um parágrafo; ver se a "cauda" que ele cortou é mesmo uma frase à parte.

### 7. Ver no browser

Abrir o HTML gerado no browser disponível, em largura de desktop e de telemóvel (375 px), e
percorrer: topo, guia visual, duas ou três secções com conteúdo diferente (tabela, código, lista
longa), a última secção. Procurar o que os números não mostram:

- código partido a meio de uma palavra dentro de tabelas;
- rótulos sobrepostos ou cortados nos diagramas;
- pílulas de estado muito compridas a quebrar mal;
- um bloco que ficou com o destaque errado (um "Nota:" que era só um título);
- deslocamento horizontal da página no telemóvel.

Testar o filtro com uma palavra que exista. Corrigir e gerar outra vez; uma segunda volta chega.

Se as ferramentas do browser recusarem um ficheiro local, é porque está fora da pasta do
projeto: gerar com `--saida` para dentro dela.

### 8. Entregar

Dizer, por esta ordem:

1. onde está a página (link para o ficheiro);
2. o que mudou na forma, em poucas linhas;
3. o que acrescentaste que não é do autor (guia visual, temas, etiquetas);
4. o que não verificaste;
5. o que encontraste no conteúdo que parece desatualizado ou contraditório. **Reportar, não
   corrigir**: o documento tem dono, e uma correção silenciosa na versão bonita cria duas
   versões da verdade.

Fechar com uma linha a dizer que dá para publicar como artifact, se o utilizador quiser.

## Publicar (só a pedido)

A variante para artifact não leva `doctype`, `html`, `head` nem `body`, nem o link de volta:

```bash
python3 <skill>/scripts/dracula_doc.py doc.md --artifact <scratchpad>/<nome>.html
```

Publicar esse ficheiro com a ferramenta Artifact (título curto, ícone de uma palavra, descrição
de uma frase). Para atualizar um artifact que já existe, passar o `url` dele em vez de criar
outro. O artifact nasce privado: dizer ao utilizador que os outros só o abrem depois de ele
partilhar.

## Quando o documento muda

Voltar a correr o comando do passo 6. A configuração continua a valer. Rever o que foi escrito à
mão (guia visual, `TEMAS`, `ETIQUETAS`), porque é a única parte que não se atualiza sozinha, e
ver se há secções novas sem tema.

## Limites do motor

Percebe títulos, parágrafos, listas aninhadas e de tarefas, tabelas, blocos de código, citações e
alertas (`> [!NOTE]`), links, imagens, negrito, itálico e front matter. HTML cru dentro do
Markdown aparece como texto. Para uma construção que ele não perceba, a conferência falha e diz
onde: é melhor contornar na configuração (omitir, mudar o nível) do que entregar uma página com
texto em falta.

A página é sempre Dracula, escura por escolha. Se o utilizador pedir outro tema, as cores estão
todas em variáveis no início do CSS do motor; não mudar a estrutura.
