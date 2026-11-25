---
name: create-tasks
description: Quebra um documento (spec, plano, ADR, ata, registro de decisões) e o que foi combinado na conversa em arquivos de task em Markdown, prontos para executar — pequenos, ordenados por dependência, com critérios verificáveis e a origem de cada um. Use quando o usuário chamar /create-tasks ou pedir para "criar as tasks", "quebrar isso em tarefas", "gerar o backlog desse doc", "transformar o plano em tasks" ou atualizar as tasks depois que o documento mudou. Não usar para executar as tasks, para registrar a conversa (snapshot-to-doc) nem para criar uma change do OpenSpec.
argument-hint: "[documento.md ...] [pasta de destino]"
---

# Criar tasks

Objetivo: cada arquivo pode ser entregue a uma pessoa ou a um agente **que não leu a conversa** e
dá para dizer, sem discussão, se ficou pronto. Uma task que exige perguntar "o que era isso mesmo?"
não está pronta; uma task que o documento não pediu é trabalho inventado.

Escrever na língua do documento. **Criar a task não é autorização para executá-la.**

## 1. Reunir as fontes

Ler inteiros os documentos indicados. Sem indicação, usar o que esteve em discussão na conversa; se
houver mais de um candidato plausível, perguntar qual. Seguir links internos só quando a task
depende deles.

Quando documento e conversa discordam, vale a fala mais recente **do usuário**. Registrar a
divergência na task e avisar na entrega que o documento está desatualizado; não editar o documento.

## 2. Ver o que já existe

- **Destino:** o que o usuário indicou; senão a pasta de tasks que o projeto já usa; senão `tasks/`.
- **Formato:** se já há tasks, seguir o formato, os nomes e a numeração delas. Senão, usar
  [task-template.md](task-template.md), na pasta desta skill (`${CLAUDE_SKILL_DIR}/task-template.md`).
- **Repetição:** ler as tasks existentes. Não recriar o que já tem task nem refazer o que está
  concluído; se uma task aberta mudou, atualizar a seção afetada e preservar status, notas e itens
  marcados. Task concluída não se edita: o que mudou vira task nova que aponta para ela.
- **Numeração:** continuar do maior ID existente. IDs não são reaproveitados.
- **Código:** quando há repositório, conferir rapidamente se o que a task descreve já está feito e
  quais arquivos ela toca. Citar só caminhos que existem.
- **OpenSpec:** se o projeto planeja com OpenSpec, criar as tasks se o usuário chamou a skill, e dizer
  numa linha que uma change seria o caminho do projeto.

## 3. Decompor

Cortar por **resultado observável**, não por camada: "cliente cancela o pedido" é melhor que
"criar endpoint" + "criar botão", a menos que times diferentes façam cada parte.

- **Tamanho:** cabe numa sessão de trabalho e num PR revisável. Dividir quando há dois resultados
  independentes; juntar quando uma parte não faz sentido sozinha. Um pedido pequeno é **uma** task.
- **Cobertura:** todo requisito vai para uma task, ou para a lista do que ficou de fora com o motivo.
- **Limites viram texto da task:** quem executa não leu o documento, então "não mexer em X" precisa
  estar na task que poderia esbarrar em X. Só nela: o mesmo aviso colado em todas deixa de ser lido.
- **Nada inventado:** não acrescentar requisito, prazo, estimativa ou tecnologia sem fonte. Testes,
  migração e documentação só viram critério quando a fonte ou as regras do projeto pedem; "ter testes"
  repetido em cada task não acrescenta nada aos comportamentos já listados.
- **Decisão em aberto não se resolve aqui**, nem a que a fonte declara ("a definir"), nem a que só
  aparece ao escrever o critério. "Um uso por CPF" pode ser por cupom ou no total; "primeira compra"
  pode contar ou não pedido cancelado. Se duas leituras razoáveis levam a comportamentos diferentes,
  não escolher em silêncio: a task nasce `Bloqueada`, com a pergunta, as leituras e quem responde. Se
  a dúvida afeta só um pedaço, separar esse pedaço para o resto poder andar.
- **Dependência** só quando uma task não pode começar sem a outra. Sem ciclos.
- **Prioridade:** a da fonte; sem ela, `Média`. Não deduzir urgência.

## 4. Escrever

Um arquivo por task: `TASK-<NNN>-<nome-curto>.md`, salvo convenção do projeto. Título com verbo e
resultado ("Impedir cancelamento de pedido já enviado").

Critério de aceitação é algo que se verifica com sim ou não. Incluir o caso de erro ou limite quando
a fonte o define.

- Ruim: "Cancelamento funciona corretamente"
- Bom: "Cancelar um pedido com status `enviado` responde 409 e não altera o pedido"

Em **Origem**, apontar documento e seção, ou a decisão da conversa com a data. Omitir seções que
ficariam vazias. Não copiar segredos da fonte: citar o nome da variável.

## 5. Conferir

Reler do disco **todos** os arquivos gravados, não uma amostra (um comando que mostre a pasta inteira
basta), e checar:

1. cada requisito da fonte está em exatamente uma task, ou na lista do que ficou de fora;
2. cada critério tem fonte, e nenhum é vago;
3. toda dependência aponta para um ID que existe;
4. reler cada requisito procurando uma segunda interpretação: nenhuma task executável depende de uma
   decisão em aberto;
5. lendo só a task, dá para começar.

## 6. Entregar

Uma tabela em ordem de execução (ID com link, título, depende de, status) e, abaixo, só o que existir:
o que ficou de fora e por quê, as decisões que bloqueiam e de quem são, as divergências entre documento
e conversa, as tasks existentes que foram atualizadas. Não gravar um índice, a menos que o projeto já
tenha um (nesse caso, atualizá-lo) ou o usuário peça.
