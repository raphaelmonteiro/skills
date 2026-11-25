# skills

Skills para o Claude Code.

| Skill | O que faz |
|---|---|
| [doc-enrich](skills/doc-enrich/SKILL.md) | Transforma um Markdown ou HTML numa página HTML em tema Dracula, sem mudar o texto |
| [snapshot-to-doc](skills/snapshot-to-doc/SKILL.md) | Registra a conversa num documento e confere o resultado contra ela |
| [create-tasks](skills/create-tasks/SKILL.md) | Quebra um documento em tasks com origem, dependências e critérios verificáveis |

A `doc-enrich` precisa de Python 3 (só a biblioteca padrão).

## Instalar

Como plugin, no Claude Code:

```
/plugin marketplace add raphaelmonteiro/skills
/plugin install raphael-skills@raphael-skills
```

Instaladas assim, as skills são chamadas com prefixo: `/raphael-skills:create-tasks`.

Ou copiadas, sem prefixo:

```bash
git clone https://github.com/raphaelmonteiro/skills.git
mkdir -p ~/.claude/skills
cp -R skills/skills/* ~/.claude/skills/
```

Use só uma das duas formas, para as skills não aparecerem em dobro.

## Outras skills que eu uso

Estas não são minhas e não estão neste repositório. Para baixar, use os links dos autores.

| Skill | Autor | Para que serve | Download | Licença |
|---|---|---|---|---|
| OpenSpec | Fission-AI | Desenvolvimento guiado por especificação: propor, aplicar e arquivar mudanças | [Fission-AI/OpenSpec](https://github.com/Fission-AI/OpenSpec) | MIT |
| Elephant-Goldfish Model (EGM) | Google | Escrever specs com contexto e revisá-las com agentes que não viram a conversa | [google/elephant-goldfish-model](https://github.com/google/elephant-goldfish-model) | Apache 2.0 |
| grill-me | Matt Pocock | Entrevista que aperta um plano até as decisões ficarem claras (usa a skill `grilling`) | [mattpocock/skills](https://github.com/mattpocock/skills/tree/main/skills/productivity/grill-me) | MIT |

Como instalar no Claude Code, segundo os autores:

```bash
# OpenSpec (precisa de Node.js; depois, dentro do projeto)
npm install -g @fission-ai/openspec@latest
openspec init

# Elephant-Goldfish Model
claude plugin marketplace add google/elephant-goldfish-model
claude plugin install egm@egm

# grill-me (vem no plugin com as demais skills do Matt Pocock)
claude plugin install mattpocock-skills@claude-plugins-official
```

## Licença

As skills deste repositório: [MIT](LICENSE). As listadas acima seguem a licença de cada autor.
