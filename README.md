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

## Licença

[MIT](LICENSE)
