---
name: snapshot-to-doc
description: Registra a conversa atual num documento Markdown que substitui reler a conversa — o que foi pedido, decidido, descartado e por quê, o que ficou só proposto e o que está em aberto — e confere o resultado contra a conversa antes de entregar. Use quando o usuário chamar /snapshot-to-doc ou pedir para "documentar tudo isso", "documenta o que falamos", "consolida num documento", "registra o que decidimos", "salva esse plano em docs/" ou atualizar um registro desses com o que mudou. Não usar para documentar código que não foi assunto da conversa (README, docs de API), nem para quebrar trabalho em tasks (create-tasks).
argument-hint: "[assunto ou recorte] [arquivo ou pasta de destino]"
---

# Snapshot da conversa em documento

Objetivo: alguém que não esteve na conversa, inclusive você numa sessão futura, lê o documento e
sabe o que vale. O erro caro aqui não é o texto feio: é a **omissão** (um combinado que some) e a
**promoção** (uma ideia sua, que o usuário nunca aprovou, virar "decisão").

Escrever na língua da conversa. Fazer tudo sem pedir confirmação no meio do caminho.

**Documentar não é autorização para começar.** Não implementar, instalar, commitar nem publicar
nada do que o documento descreve.

## 1. Definir recorte e destino

- **Recorte:** o que o usuário indicou; sem indicação, a conversa inteira.
- **Destino**, na primeira regra que servir:
  1. o caminho que o usuário deu;
  2. um documento que já registra este assunto: atualizar (passo 5) em vez de criar outro;
  3. a convenção do projeto: procurar documentos irmãos (`docs/`, `requisitos/`, ADRs) e seguir a
     numeração, o nome e as seções deles;
  4. `docs/<assunto>-<AAAA-MM-DD>.md`.

Se o destino já existir e tratar de outra coisa, usar outro nome; não sobrescrever.

## 2. Levantar antes de escrever

Percorrer a conversa na ordem, mensagem a mensagem, e montar um inventário. Escrever de memória é
o que produz omissões: o fim da conversa fica nítido e o meio desaparece.

Se a conversa foi compactada, o resumo não basta. Ler a transcrição da sessão em
`~/.claude/projects/<projeto>/<sessão>.jsonl`; se não for possível, dizer no documento que o trecho
anterior veio de um resumo.

Para cada item, guardar quem disse e o que o sustenta. O que mais se perde:

- alternativas oferecidas e a escolhida, com o motivo da recusa das outras;
- perguntas do usuário e a resposta que ele recebeu;
- limites e proibições ("não mexe em X", "só depois que eu autorizar", tetos de gasto);
- números, datas, versões, URLs, caminhos, comandos e IDs;
- o que mudou de ideia: vale a última posição, e a anterior fica registrada como substituída;
- efeitos já produzidos: arquivos criados ou alterados, gasto feito, contas, memórias salvas;
- pendências, e de quem é cada uma.

## 3. Classificar

| Estado | Quando usar |
|---|---|
| **DECIDIDO** | o usuário disse, aprovou ou escolheu |
| **PROPOSTO** | você sugeriu e o usuário não respondeu, ou respondeu outra coisa |
| **ABERTO** | falta decisão ou informação; dizer de quem |
| **DESCARTADO** | recusado ou substituído, com o motivo |

Silêncio não é aprovação. Na dúvida entre DECIDIDO e PROPOSTO, é PROPOSTO.

Separar também fato verificado (foi medido, lido no código ou numa fonte; citar qual) de inferência
(marcar "inferência"). Não acrescentar fatos, números ou motivos que não apareceram na conversa; se
o motivo não foi dito, escrever "motivo não registrado".

## 4. Escrever

Se o projeto tem convenção, ela manda na estrutura: manter as seções dela, na ordem dela, e acrescentar
depois só as que faltarem para os estados acima.
Sem convenção, usar estas seções, na ordem, e omitir as vazias:

```markdown
# <Assunto>

> Registro da conversa de <data>. <Uma frase: onde isto está e qual é o próximo passo.>

## Resumo            – o que vale, em até 8 linhas
## O que foi pedido  – objetivo e restrições do usuário
## Contexto e achados – diagnóstico e medições, com fonte
## Decisões          – tabela: ID (D1…) | Decisão | Motivo | Estado; só DECIDIDO, e as que já
                       foram DECIDIDO e caíram
## Propostas sem resposta – o que você sugeriu e o usuário não aprovou
## Alternativas descartadas – opção e por que não
## Regras e limites  – proibições, tetos e autorizações que não estão em Decisões
## Plano             – etapas combinadas; sem etapas combinadas, omitir
## Em aberto         – pergunta | de quem | o que bloqueia; não repetir as propostas
## O que já foi feito – arquivos, gastos, efeitos fora do repositório
## Referências       – arquivos e URLs
```

- O tamanho acompanha a conversa. Uma decisão simples cabe em meia página; não encher seção.
- Cada fato mora num lugar só; nos outros, apontar para ele (`D3`).
- **Segredos nunca entram** (chave, token, senha, dado de cartão), nem parcialmente: escrever o nome
  da variável e onde ela fica. Se o usuário colou um segredo na conversa, avisar na entrega que ele
  deve ser trocado. Dado pessoal de terceiros só entra se a decisão depender dele.
- Datas absolutas, nunca "ontem" ou "semana que vem".

## 5. Atualizar um documento existente

Ler o documento inteiro primeiro. Mudar só o que a conversa mudou e manter o que outra pessoa
escreveu. Uma decisão revertida passa a DESCARTADO com "substituída por D7 em <data>", e a nova ganha
um ID novo: IDs não são reaproveitados porque outros documentos apontam para eles. Registrar a
mudança em `## Histórico`, no fim, com uma linha por atualização; o topo continua curto e sempre diz
o estado atual.

## 6. Conferir, em duas passadas

Na prática, a primeira versão sempre deixa coisa de fora. Não pular, mesmo que pareça completo.

1. **Conversa → documento.** Reler a conversa e checar cada item do inventário no arquivo salvo.
   Corrigir o que faltou.
2. **Documento → conversa.** Reler o arquivo do disco, do começo ao fim: cada DECIDIDO tem uma fala
   do usuário que o sustenta? Os números e datas batem entre seções? Toda referência (`D3`, "§4",
   arquivo) existe? As tabelas estão bem formadas? Sobrou algum segredo?

Se a segunda passada corrigir algo importante, repetir as duas.

## 7. Entregar

Curto, sem repetir o documento: o link do arquivo (criado ou atualizado), as decisões em uma ou duas
linhas, o que ficou **em aberto** e depende do usuário, o que a conferência corrigiu e qualquer
trecho que não deu para confirmar.
