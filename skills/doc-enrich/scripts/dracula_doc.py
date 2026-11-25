#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
dracula_doc.py: Markdown -> página HTML em tema Dracula, sem reescrever o texto.

    python3 dracula_doc.py DOC.md --analisar          # retrato da estrutura, para escrever a configuração
    python3 dracula_doc.py DOC.md                     # gera DOC-dracula.html ao lado do documento
    python3 dracula_doc.py DOC.md --artifact X.html   # gera também a variante para publicar como artifact

Opções: --config FICHEIRO.py (por omissão DOC.dracula.py, se existir), --saida FICHEIRO.html.

O motor lê o Markdown, transforma cada secção num painel, pinta estados, rótulos e referências
conforme a configuração, e no fim confere que todas as palavras do documento estão na página,
pela mesma ordem. Sai com código 1 se a conferência falhar.

A configuração é um módulo Python opcional; todas as chaves estão em references/configuracao.md.
Só usa a biblioteca padrão do Python 3.
"""
import datetime
import html
import importlib.util
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

# --------------------------------------------------------------------------
# Textos da interface
# --------------------------------------------------------------------------

TXT = {
    "pt": {
        "indice": "Índice", "documento": "Documento", "intro": "Introdução", "guia": "Guia visual",
        "filtrar": "Filtrar: palavra, código, endpoint…", "filtrar_rotulo": "Filtrar", "de": "de",
        "limpar": "limpar", "vazio": "Nada corresponde ao filtro.", "limpar_filtro": "Limpar filtro",
        "copiar": "Copiar", "copiado": "Copiado", "selecionado": "Selecionado", "liga": "Liga com",
        "no_guia": "No guia", "fonte": "fonte", "fonte_de": "fonte de", "temas": "Por tema",
        "temas_sub": "As mesmas secções, juntas por assunto.", "em": "em", "das": "das",
        "guia_nota": "Resumo feito a partir do documento, para orientar a leitura. Em caso de dúvida vale o texto original.",
        "rodape": "Gerado de <code>{f}</code> com a skill doc-enrich. O ficheiro de origem continua a ser a fonte: para mudar o texto, editá-lo e voltar a gerar.",
        "seccao": ("secção", "secções"), "texto": "texto",
        "alertas": {"NOTE": "Nota", "TIP": "Dica", "IMPORTANT": "Importante", "WARNING": "Aviso", "CAUTION": "Cuidado"},
    },
    "en": {
        "indice": "Contents", "documento": "Document", "intro": "Introduction", "guia": "Visual guide",
        "filtrar": "Filter: word, code, endpoint…", "filtrar_rotulo": "Filter", "de": "of",
        "limpar": "clear", "vazio": "Nothing matches the filter.", "limpar_filtro": "Clear filter",
        "copiar": "Copy", "copiado": "Copied", "selecionado": "Selected", "liga": "Related",
        "no_guia": "In the guide", "fonte": "source", "fonte_de": "source dated", "temas": "By topic",
        "temas_sub": "The same sections, grouped by subject.", "em": "in", "das": "of",
        "guia_nota": "A summary made from the document, to help you find your way. If in doubt, the original text wins.",
        "rodape": "Generated from <code>{f}</code> with the doc-enrich skill. The source file remains the source of truth: edit it and generate again.",
        "seccao": ("section", "sections"), "texto": "text",
        "alertas": {"NOTE": "Note", "TIP": "Tip", "IMPORTANT": "Important", "WARNING": "Warning", "CAUTION": "Caution"},
    },
}

CORES = ("green", "cyan", "orange", "pink", "purple", "red", "yellow", "muted")
FORMAS = ("cheio", "meio", "oco")

# tipo de destaque -> (cor, ícone)
DESTAQUES = {
    "mudou": ("yellow", "↻"), "fazer": ("purple", "✓"), "pergunta": ("pink", "?"), "aberto": ("orange", "◇"),
    "risco": ("red", "!"), "info": ("cyan", "i"), "ok": ("green", "◆"),
}
ALERTAS = {"NOTE": "info", "TIP": "ok", "IMPORTANT": "fazer", "WARNING": "aberto", "CAUTION": "risco"}

# rótulo em negrito no início de um item ("**Decisão:** …") -> tipo. A configuração (ROTULOS) vem primeiro.
ROTULOS_PADRAO = [
    ("revist", "mudou"), ("atualiza", "mudou"), ("mudou", "mudou"), ("changed", "mudou"), ("updated", "mudou"), ("revised", "mudou"),
    ("o que fazer", "fazer"), ("a fazer", "fazer"), ("todo", "fazer"), ("to do", "fazer"), ("próximos passos", "fazer"),
    ("next steps", "fazer"), ("ação", "fazer"), ("ações", "fazer"), ("action", "fazer"),
    ("pergunta", "pergunta"), ("dúvida", "pergunta"), ("question", "pergunta"),
    ("em decisão", "aberto"), ("em aberto", "aberto"), ("pendente", "aberto"), ("por decidir", "aberto"),
    ("open", "aberto"), ("pending", "aberto"), ("tbd", "aberto"),
    ("risco", "risco"), ("atenção", "risco"), ("cuidado", "risco"), ("aviso", "risco"), ("bloqueia", "risco"),
    ("warning", "risco"), ("caution", "risco"), ("risk", "risco"),
    ("nota", "info"), ("note", "info"), ("dica", "info"), ("tip", "info"), ("contexto", "info"),
    ("decisão", "ok"), ("decision", "ok"), ("resposta", "ok"), ("answer", "ok"), ("resolvido", "ok"), ("feito", "ok"), ("done", "ok"),
]
TITULOS_INDICE = {"sumário", "sumario", "índice", "indice", "conteúdo", "table of contents", "contents", "toc"}
RESERVADOS = {"settings", "sidebar", "customize", "upgrade", "downloads"}

# --------------------------------------------------------------------------
# Markdown -> árvore de blocos
# --------------------------------------------------------------------------

RE_BULLET = re.compile(r"^( *)([-*+]) (.*)$")
RE_ORDERED = re.compile(r"^( *)(\d+)([.)]) (.*)$")
RE_FENCE = re.compile(r"^ *(```+|~~~+) *([\w+#.-]*).*$")
RE_HEAD = re.compile(r"^(#{1,6}) +(.*?)(?: +#+)? *$")
RE_HR = re.compile(r"^ {0,3}([-*_])(?: *\1){2,} *$")
RE_TSEP = re.compile(r"^ *\|?(?: *:?-+:? *\|)+(?: *:?-+:? *)?\|? *$")
RE_TASK = re.compile(r"^\[([ xX])\] +(.*)$")
RE_ALERTA = re.compile(r"^\[!(NOTE|TIP|IMPORTANT|WARNING|CAUTION)\]\s*$")


def recuo(s):
    return len(s) - len(s.lstrip(" "))


def item_de(linha):
    m = RE_BULLET.match(linha)
    if m:
        return len(m.group(1)), len(m.group(1)) + 2, m.group(3), False, None
    m = RE_ORDERED.match(linha)
    if m:
        return len(m.group(1)), len(m.group(1)) + len(m.group(2)) + 2, m.group(4), True, int(m.group(2))
    return None


def celulas(linha):
    linha = linha.strip()
    if linha.startswith("|"):
        linha = linha[1:]
    if linha.endswith("|") and not linha.endswith("\\|"):
        linha = linha[:-1]
    out, cur, code, ant = [], "", False, ""
    for ch in linha:
        if ch == "`":
            code = not code
        if ch == "|" and not code and ant != "\\":
            out.append(cur.strip())
            cur = ""
        else:
            cur += ch
        ant = ch
    out.append(cur.strip())
    return out


def inicio_tabela(linhas, i):
    return linhas[i].lstrip().startswith("|") and i + 1 < len(linhas) and bool(RE_TSEP.match(linhas[i + 1]))


def blocos(linhas, base=None):
    """base: número da primeira linha no ficheiro (só no nível de cima), para saber onde começa cada cabeçalho."""
    out, i, n = [], 0, len(linhas)
    while i < n:
        linha = linhas[i]
        if not linha.strip():
            i += 1
            continue
        m = RE_FENCE.match(linha)
        if m:
            marca, j, corpo = m.group(1), i + 1, []
            while j < n and not (linhas[j].strip().startswith(marca[:3]) and set(linhas[j].strip()) <= set(marca[0])):
                corpo.append(linhas[j])
                j += 1
            r = min((recuo(c) for c in corpo if c.strip()), default=0)
            out.append({"t": "code", "lang": m.group(2), "text": "\n".join(c[r:] for c in corpo)})
            i = j + 1
            continue
        m = RE_HEAD.match(linha)
        if m:
            b = {"t": "h", "level": len(m.group(1)), "text": m.group(2).strip()}
            if base is not None:
                b["linha"] = base + i
            out.append(b)
            i += 1
            continue
        if RE_HR.match(linha) and not item_de(linha):
            out.append({"t": "hr"})
            i += 1
            continue
        if linha.lstrip().startswith(">"):
            j, q = i, []
            while j < n and linhas[j].lstrip().startswith(">"):
                q.append(re.sub(r"^ *> ?", "", linhas[j]))
                j += 1
            b = {"t": "quote", "alerta": None}
            ma = RE_ALERTA.match(q[0].strip()) if q else None
            if ma:
                b["alerta"] = ma.group(1)
                q = q[1:]
            b["blocks"] = blocos(q)
            out.append(b)
            i = j
            continue
        if inicio_tabela(linhas, i):
            j, rows = i, []
            while j < n and linhas[j].lstrip().startswith("|"):
                rows.append(celulas(linhas[j]))
                j += 1
            out.append({"t": "table", "head": rows[0], "rows": rows[2:]})
            i = j
            continue
        it = item_de(linha)
        if it:
            base_i, ordered = it[0], it[3]
            itens = []
            while i < n:
                linha = linhas[i]
                if not linha.strip():
                    j = i
                    while j < n and not linhas[j].strip():
                        j += 1
                    if j >= n:
                        i = j
                        break
                    if recuo(linhas[j]) > base_i:
                        itens[-1]["lines"].append("")
                        i = j
                        continue
                    prox = item_de(linhas[j])
                    i = j
                    if prox and prox[0] == base_i and prox[3] == ordered:
                        continue
                    break
                it2 = item_de(linha)
                if it2 and it2[0] == base_i and it2[3] == ordered:
                    texto, task = it2[2], None
                    mt = RE_TASK.match(texto)
                    if mt:
                        task, texto = mt.group(1) != " ", mt.group(2)
                    itens.append({"col": it2[1], "num": it2[4], "task": task, "lines": [texto]})
                    i += 1
                    continue
                if recuo(linha) > base_i and itens:
                    col = itens[-1]["col"]
                    itens[-1]["lines"].append(linha[col:] if recuo(linha) >= col else linha.lstrip())
                    i += 1
                    continue
                break
            out.append({"t": "list", "ordered": ordered,
                        "items": [{"num": x["num"], "task": x["task"], "blocks": blocos(x["lines"])} for x in itens]})
            continue
        buf = []
        while i < n and linhas[i].strip():
            l = linhas[i]
            if buf and (RE_FENCE.match(l) or inicio_tabela(linhas, i) or item_de(l) or RE_HEAD.match(l)
                        or l.lstrip().startswith(">") or RE_HR.match(l)):
                break
            buf.append(l.strip())
            i += 1
        out.append({"t": "p", "text": " ".join(buf)})
    return out


# --------------------------------------------------------------------------
# Utilitários de texto
# --------------------------------------------------------------------------

def esc(s):
    return html.escape(s, quote=False)


def atr(s):
    return html.escape(s, quote=True)


def simples(md):
    return re.sub(r"[`*]", "", md)


def slug(s):
    s = unicodedata.normalize("NFD", simples(s)).encode("ascii", "ignore").decode("ascii").lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")[:60].strip("-")
    if not s or s[0].isdigit() or s in RESERVADOS or s.startswith("comment-"):
        s = "s-" + s
    return s


def equilibrado(s):
    return s.count("`") % 2 == 0 and s.count("**") % 2 == 0


def maiuscula(md):
    return md[0].upper() + md[1:] if md and md[0].islower() else md


def cortar_cauda(seg, terminador):
    paragens = "?" if terminador == "?" else "."
    code, fundo = False, 0
    for i, ch in enumerate(seg):
        if ch == "`":
            code = not code
        elif not code:
            if ch == "(":
                fundo += 1
            elif ch == ")":
                fundo = max(0, fundo - 1)
            elif ch in paragens and fundo == 0:
                resto = seg[i + 1:]
                if re.match(r"\s+(\*\*)?[A-ZÁÉÍÓÚÂÊÔÃÕÇ]", resto):
                    return seg[: i + 1], resto.strip()
    return seg, ""


def enumeracao(md):
    """Separa "(a) … (b) …" ou "(1) … (2) …" escritos dentro de um parágrafo."""
    for seq in ("abcdefgh", "12345678"):
        pos, ini = [], 0
        for mk in seq:
            k = md.find("(%s) " % mk, ini)
            if k < 0:
                break
            pos.append(k)
            ini = k + 4
        if len(pos) < 2:
            continue
        cabeca = md[: pos[0]]
        segs = [md[pos[k]: pos[k + 1] if k + 1 < len(pos) else len(md)] for k in range(len(pos))]
        if not all(equilibrado(x) for x in [cabeca] + segs):
            continue
        ultimo, cauda = cortar_cauda(segs[-1], segs[0].rstrip()[-1])
        segs[-1] = ultimo
        return cabeca.strip(), [(seq[k], segs[k][4:].strip()) for k in range(len(segs))], cauda
    return None


RE_ROTULO = re.compile(r"^\*\*((?:[^*`]|`[^`]*`|\*(?!\*))+?):\*\*\s*")
RE_NEGRITO_INI = re.compile(r"^\*\*((?:[^*`]|`[^`]*`|\*(?!\*))+)\*\*\s*")
RE_IMG = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
RE_LINK = re.compile(r"(?<!!)\[((?:[^\]\[`]|`[^`]*`)+)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
RE_URL = re.compile(r"(?<![\w/\"=])(https?://[^\s<>()]+[^\s<>().,;:!?'\"])")
RE_EM1 = re.compile(r"(?<![\w*])\*([A-Za-zÀ-ÿ0-9\"“][^*\n]*?[A-Za-zÀ-ÿ0-9.!?\"”)])\*(?![\w*])")
RE_EM2 = re.compile(r"(?<![\w_])_([A-Za-zÀ-ÿ0-9\"“][^_\n]*?[A-Za-zÀ-ÿ0-9.!?\"”)])_(?![\w_])")
RE_DEL = re.compile(r"~~([^~\n]+)~~")
RE_JSON = re.compile(r'("(?:[^"\\]|\\.)*")(\s*:)?|\b(true|false|null)\b|(-?\d+(?:\.\d+)?)')
METODOS = "GET|POST|PUT|PATCH|DELETE"
HTTP = {"200", "201", "202", "204", "301", "302", "400", "401", "402", "403", "404", "409", "422", "429", "500", "502", "503"}


def realce(texto, lang):
    lang = (lang or "").lower()
    if lang == "json":
        out, pos = [], 0
        for m in RE_JSON.finditer(texto):
            out.append(esc(texto[pos:m.start()]))
            if m.group(1):
                out.append('<span class="%s">%s</span>%s' % ("j-k" if m.group(2) else "j-s", esc(m.group(1)), esc(m.group(2) or "")))
            elif m.group(3):
                out.append('<span class="j-c">%s</span>' % m.group(3))
            else:
                out.append('<span class="j-n">%s</span>' % m.group(4))
            pos = m.end()
        out.append(esc(texto[pos:]))
        return "".join(out)
    marca = {"bash": "#", "sh": "#", "shell": "#", "zsh": "#", "yaml": "#", "yml": "#", "python": "#", "py": "#",
             "sql": "--", "js": "//", "ts": "//", "java": "//", "javascript": "//", "typescript": "//"}.get(lang)
    if not marca:
        return esc(texto)
    return "\n".join('<span class="j-x">%s</span>' % esc(l) if l.lstrip().startswith(marca) else esc(l) for l in texto.split("\n"))


def palavras(s):
    return re.findall(r"[0-9a-zà-ÿ]+", s.lower())


def texto_de(h):
    return html.unescape(re.sub(r"<[^>]+>", " ", h))


def fonte_limpa(txt):
    """O que do Markdown não é texto visível: endereços de links, caixas de tarefa, marcas de alerta."""
    txt = re.sub(r"!\[([^\]]*)\]\([^)]*\)", r"\1", txt)
    txt = re.sub(r"\]\([^)\s]+(?:\s+\"[^\"]*\")?\)", "]", txt)
    txt = re.sub(r"^(\s*(?:[-*+]|\d+[.)]) )\[[ xX]\] ", r"\1", txt, flags=re.M)
    txt = re.sub(r"^\s*>\s*\[!\w+\]\s*$", "", txt, flags=re.M)
    return txt


def subsequencia(fonte, saida):
    j = 0
    for i, w in enumerate(fonte):
        while j < len(saida) and saida[j] != w:
            j += 1
        if j >= len(saida):
            return i
        j += 1
    return -1


class Sec:
    def __init__(self):
        self.key = self.chip = self.titulo = ""
        self.n = None
        self.blocos = []
        self.linha = 0
        self.fim = 0
        self.parte = None
        self.estados = set()
        self.refs = set()
        self.html = ""
        self.titulo_html = ""


# --------------------------------------------------------------------------
# Motor
# --------------------------------------------------------------------------

class Motor:
    def __init__(self, fonte, cfg=None):
        self.fonte = Path(fonte)
        self.cfg = cfg
        self.t = TXT.get(self.op("IDIOMA", "pt"), TXT["pt"])
        self.avisos = []
        self.relatorio = {"enum": []}
        self.ancoras = {}      # id -> título (para dicas)
        self.def_ids = {}      # identificador (ex. "REQ-7") -> âncora onde é definido
        self._sem_link = set()
        self._usados = set()

        md = self.fonte.read_text(encoding="utf-8")
        md = re.sub(r"<!--.*?-->", "", md, flags=re.S)
        self.linhas = md.split("\n")
        self.pre = 0
        if self.linhas and self.linhas[0].strip() == "---":      # front matter
            fim = next((i for i in range(1, len(self.linhas)) if self.linhas[i].strip() == "---"), None)
            if fim:
                self.pre = fim + 1
        self.arvore = blocos(self.linhas[self.pre:], base=self.pre)

        self._estados()
        self._estrutura()
        self._decor()

    # ---------------- configuração ----------------

    def op(self, nome, padrao=None):
        return getattr(self.cfg, nome, padrao) if self.cfg is not None else padrao

    def _estados(self):
        self.estados, marcas = [], []
        for i, e in enumerate(self.op("ESTADOS", []) or []):
            d = dict(e)
            d.setdefault("id", "e%d" % i)
            d.setdefault("cor", CORES[i % len(CORES)])
            d.setdefault("forma", FORMAS[i % 3])
            d.setdefault("rotulo", d.get("marca", d["id"]))
            d.setdefault("curto", d["rotulo"])
            d.setdefault("onde", "texto")
            if d.get("padrao"):
                d["re"] = re.compile(d["padrao"], re.M)
            if d.get("marca"):
                marcas.append(d["marca"])
            self.estados.append(d)
        self.por_marca = {d["marca"]: d for d in self.estados if d.get("marca")}
        self.re_estado = None
        if marcas:
            alt = "|".join(re.escape(x) for x in sorted(marcas, key=len, reverse=True))
            self.re_estado = re.compile(r"(?<!`)\[(%s)((?:[^\]`]|`[^`]*`)*)\]" % alt)

    def _estrutura(self):
        tops = [b for b in self.arvore if b["t"] == "h"]
        nivel = self.op("NIVEL")
        if not nivel:
            conta = Counter(b["level"] for b in tops)
            nivel = 2 if conta[2] >= 2 else (3 if conta[3] >= 2 else (1 if conta[1] >= 2 else 2))
        self.nivel = nivel
        h1 = next((b for b in tops if b["level"] == 1), None) if nivel > 1 else None
        self.titulo_md = self.op("TITULO") or (h1["text"] if h1 else self.fonte.stem)
        nome = self.op("NOME_SECCAO") or self.t["seccao"]
        self.nome = (nome, nome + "s") if isinstance(nome, str) else tuple(nome)
        self.prefixo = self.op("PREFIXO") or (slug(self.nome[0]) if self.op("NOME_SECCAO") else "sec")
        ids_cfg = [rx for rx, _ in (self.op("IDS", []) or [])]
        re_id_ini = re.compile(r"^(%s)\s*(?:[·:—–-]\s*)?(.+)$" % "|".join("(?:%s)" % x for x in ids_cfg)) if ids_cfg else None
        omitir = [x.lower() for x in (self.op("OMITIR") or [])]

        self.intro, self.fluxo, self.seccoes, self.omitidas = [], [], [], []
        atual = parte = None
        for b in self.arvore:
            if b["t"] == "h" and b is h1:
                continue
            if b["t"] == "h" and b["level"] <= nivel:
                if b["level"] < nivel:
                    parte = {"t": "parte", "titulo": b["text"], "blocos": [], "linha": b["linha"], "key": None}
                    self.fluxo.append(parte)
                    atual = None
                    continue
                s = Sec()
                s.linha, s.parte = b["linha"], parte
                tit = b["text"]
                m = re.match(r"^(§?\d+(?:\.\d+)*)[.)]?\s+(.+)$", tit)
                mi = re_id_ini.match(tit) if re_id_ini else None
                if m:
                    s.chip, s.titulo = m.group(1), m.group(2)
                    num = m.group(1).lstrip("§")
                    if num.isdigit():
                        s.n = int(num)
                        s.key = "%s-%d" % (self.prefixo, s.n)
                    else:
                        s.key = "%s-%s" % (self.prefixo, num.replace(".", "-"))
                elif mi:
                    s.chip, s.titulo, s.key = mi.group(1), mi.group(2), mi.group(1)
                    self.def_ids[mi.group(1)] = s.key
                else:
                    s.titulo, s.key = tit, slug(tit)
                s.key = self._unico(s.key)
                s.omitida = simples(s.titulo).strip().lower() in TITULOS_INDICE if self.op("OMITIR") is None \
                    else (simples(s.titulo).strip().lower() in omitir or s.key in (self.op("OMITIR") or []))
                (self.omitidas if s.omitida else self.seccoes).append(s)
                self.todas = getattr(self, "todas", []) + [s]
                if not s.omitida:
                    self.fluxo.append(s)
                atual = s
                continue
            if atual is not None:
                atual.blocos.append(b)
            elif parte is not None:
                parte["blocos"].append(b)
            else:
                self.intro.append(b)
        self.todas = getattr(self, "todas", [])
        marcos = sorted([s.linha for s in self.todas] + [p["linha"] for p in self.fluxo if isinstance(p, dict)])
        for alvo in self.todas + [p for p in self.fluxo if isinstance(p, dict)]:
            ini = alvo.linha if isinstance(alvo, Sec) else alvo["linha"]
            fim = next((x for x in marcos if x > ini), len(self.linhas))
            if isinstance(alvo, Sec):
                alvo.fim = fim
            else:
                alvo["fim"] = fim
        self.primeira = min(marcos) if marcos else len(self.linhas)
        self.por_n = {s.n: s for s in self.seccoes if s.n is not None}
        self.por_key = {s.key: s for s in self.seccoes}
        self.numeradas = any(s.chip for s in self.seccoes)
        for s in self.seccoes:
            self.ancoras[s.key] = simples(s.titulo)

        # cartões e subtítulos: âncoras conhecidas antes de renderizar
        self.cartoes = {}
        for alvo, pref in (self.op("CARTOES", {}) or {}).items():
            s = self.sec(alvo)
            if not s:
                continue
            self.cartoes[s.key] = pref
            for b in s.blocos:
                if b["t"] == "list" and b["ordered"]:
                    for it in b["items"]:
                        anc = "%s-%d" % (pref, it["num"])
                        prim = it["blocks"][0]["text"] if it["blocks"] and it["blocks"][0]["t"] == "p" else ""
                        mt = RE_NEGRITO_INI.match(prim)
                        self.ancoras[anc] = simples(mt.group(1)) if mt else ""
                        mi = re_id_ini.match(mt.group(1)) if (mt and re_id_ini) else None
                        if mi:
                            self.def_ids[mi.group(1)] = anc
        for s in self.seccoes:
            for b in s.blocos:
                if b["t"] == "h":
                    b["id"] = self._unico(slug(b["text"]))
                    self.ancoras[b["id"]] = simples(b["text"])
                    mi = re_id_ini.match(b["text"]) if re_id_ini else None
                    if mi:
                        self.def_ids[mi.group(1)] = b["id"]

    def _unico(self, k):
        base, i = k, 2
        while k in self._usados:
            k = "%s-%d" % (base, i)
            i += 1
        self._usados.add(k)
        return k

    def _decor(self):
        self.refs = []
        cfg = self.op("REFERENCIAS")
        if cfg is None and self.numeradas:
            formas = "|".join("[%s%s]%s" % (x[0].upper(), x[0].lower(), re.escape(x[1:])) for x in sorted(set(self.nome), key=len, reverse=True))
            cfg = [("(?:%s)" % formas, self.prefixo + "-{n}")]
        for r in cfg or []:
            if isinstance(r, (tuple, list)):
                r = {"palavra": r[0], "ancora": r[1]}
            r = dict(r)
            r.setdefault("sep", " ")
            self.refs.append(r)
        self.ids = list(self.op("IDS", []) or [])
        partes = []
        for i, r in enumerate(self.refs):
            if r["sep"]:
                partes.append(r"(?P<r%d>(?<![\w-])(?:%s)%s\d+(?:(?:, | e | a | ou | and | to | or )\d+)*(?![\w-]))" % (i, r["palavra"], re.escape(r["sep"])))
            else:
                partes.append(r"(?P<r%d>(?:%s)\d+)" % (i, r["palavra"]))
        for i, (rx, _) in enumerate(self.ids):
            partes.append(r"(?P<i%d>(?<![\w-])(?:%s)(?![\w-]))" % (i, rx))
        self.re_decor = re.compile("|".join(partes)) if partes else None
        vocab = []
        for k, v in (self.op("ROTULOS", []) or []):
            vocab.append((k.lower(), v))
        self.vocab = vocab + ([] if self.op("ROTULOS_PADRAO", True) is False else ROTULOS_PADRAO)

    def sec(self, alvo):
        if isinstance(alvo, Sec):
            return alvo
        if isinstance(alvo, int):
            return self.por_n.get(alvo)
        return self.por_key.get(alvo)

    # ---------------- texto corrido ----------------

    def code_span(self, c):
        e = esc(c)
        m = re.match(r"^(%s) (\S.*)$" % METODOS, c)
        if m:
            return '<code class="ep"><span class="vb vb-%s">%s</span> %s</code>' % (m.group(1).lower(), m.group(1), esc(m.group(2)))
        if c in HTTP:
            return '<code class="hs hs-%s">%s</code>' % (c[0], c)
        m = re.fullmatch(r"(\d{3}) ([A-Z][A-Z0-9_]+)", c)
        if m and m.group(1) in HTTP:
            return '<code class="hs hs-%s">%s</code> <code class="k">%s</code>' % (c[0], m.group(1), m.group(2))
        if re.fullmatch(r"[A-Z][A-Z0-9_]{2,}", c):
            return '<code class="k">%s</code>' % e
        return "<code>%s</code>" % e

    def c(self, s):
        return self.code_span(s)

    def pilula(self, estado, extra="", mini=False):
        e = estado if isinstance(estado, dict) else next(x for x in self.estados if x["id"] == estado or x.get("marca") == estado)
        ex = '<span class="st-c">%s</span>' % esc(extra) if extra else ""
        return '<span class="st c-%s f-%s%s"><span class="st-l">%s</span>%s</span>' % (
            e["cor"], e["forma"], " st-mini" if mini else "", esc(e["rotulo"]), ex)

    def link_ancora(self, anc, texto, sec=None):
        if anc not in self.ancoras:
            return None
        if sec is not None and anc in self.por_key and anc != sec.key:
            sec.refs.add(anc)
        return '<a class="nref" href="#%s" title="%s">%s</a>' % (anc, atr(self.ancoras[anc]), texto)

    def _sub_decor(self, m, sec):
        g = m.lastgroup
        i = int(g[1:])
        txt = m.group(0)
        if g[0] == "r":
            r = self.refs[i]
            if not r["sep"]:
                k = int(re.search(r"\d+$", txt).group(0))
                return self.link_ancora(r["ancora"].format(n=k), txt, sec) or txt
            mm = re.match(r"(.*?)(\d.*)$", txt, re.S)
            palavra, resto = mm.group(1), mm.group(2)
            nums = re.findall(r"\d+", resto)
            if len(nums) == 1:
                return self.link_ancora(r["ancora"].format(n=int(nums[0])), txt, sec) or txt
            return palavra + re.sub(r"\d+", lambda x: self.link_ancora(r["ancora"].format(n=int(x.group(0))), x.group(0), sec) or x.group(0), resto)
        cor = self.ids[i][1]
        if txt in self.def_ids and txt not in self._sem_link:
            alvo = self.def_ids[txt]
            if sec is not None and alvo in self.por_key and alvo != sec.key:
                sec.refs.add(alvo)
            return '<a class="pid c-%s" href="#%s" title="%s">%s</a>' % (cor, alvo, atr(self.ancoras.get(alvo, "")), txt)
        return '<span class="pid c-%s">%s</span>' % (cor, txt)

    def inline(self, s, sec=None):
        stash = []

        def put(h):
            stash.append(h)
            return "\x00%d\x00" % (len(stash) - 1)

        def fora(m):
            return m.string[: m.start()].count("`") % 2 == 0

        s = re.sub(r"\\([\\`*_{}\[\]()#+\-.!|>~])", lambda m: put(esc(m.group(1))) if fora(m) else m.group(0), s)
        if self.re_estado:
            def pill(m):
                e = self.por_marca[m.group(1)]
                if sec is not None:
                    sec.estados.add(e["id"])
                return put(self.pilula(e, m.group(2).lstrip(", ").strip().replace("`", "")))
            s = self.re_estado.sub(pill, s)
        s = RE_IMG.sub(lambda m: put('<img src="%s" alt="%s">' % (atr(m.group(2)), atr(m.group(1)))) if fora(m) else m.group(0), s)

        def lnk(m):
            if not fora(m):
                return m.group(0)
            url = m.group(2)
            ext = ' target="_blank" rel="noopener"' if re.match(r"https?://", url) else ""
            return put('<a href="%s"%s>%s</a>' % (atr(url), ext, self.inline(m.group(1), sec)))
        s = RE_LINK.sub(lnk, s)
        s = re.sub(r"<(https?://[^>\s]+)>", lambda m: put('<a href="%s" target="_blank" rel="noopener">%s</a>' % (atr(m.group(1)), esc(m.group(1)))) if fora(m) else m.group(0), s)

        out, bold = [], False
        for parte in re.split(r"(``.+?``|`[^`]+`)", s):
            if len(parte) >= 2 and parte[0] == "`" and parte[-1] == "`":
                out.append(self.code_span(parte[2:-2].strip() if parte.startswith("``") else parte[1:-1]))
                continue
            for k, seg in enumerate(parte.split("**")):
                if k:
                    out.append("</strong>" if bold else "<strong>")
                    bold = not bold
                t = esc(seg)
                t = RE_URL.sub(lambda m: put('<a href="%s" target="_blank" rel="noopener">%s</a>' % (atr(html.unescape(m.group(1))), m.group(1))), t)
                t = RE_DEL.sub(r"<del>\1</del>", RE_EM2.sub(r"<em>\1</em>", RE_EM1.sub(r"<em>\1</em>", t)))
                if self.re_decor:
                    t = self.re_decor.sub(lambda m: self._sub_decor(m, sec), t)
                out.append(t)
        if bold:
            out.append("</strong>")
            self.avisos.append("negrito por fechar em: %s" % s[:70])
        res = "".join(out)
        for _ in range(3):
            res = re.sub("\x00(\\d+)\x00", lambda m: stash[int(m.group(1))], res)
        return res

    # ---------------- blocos ----------------

    def paragrafo(self, md, sec, cls=""):
        c = ' class="%s"' % cls if cls else ""
        mi = re.fullmatch(RE_IMG.pattern, md.strip())
        if mi:
            cap = "<figcaption>%s</figcaption>" % esc(mi.group(1)) if mi.group(1) else ""
            return '<figure class="fig"><img src="%s" alt="">%s</figure>' % (atr(mi.group(2)), cap)
        partes = enumeracao(md)
        if not partes:
            return "<p%s>%s</p>" % (c, self.inline(md, sec))
        cabeca, itens, cauda = partes
        self.relatorio["enum"].append((sec.chip or sec.key if sec else "-", len(itens), cauda[:40]))
        h = "<p%s>%s</p>" % (c, self.inline(cabeca, sec)) if cabeca else ""
        h += '<ol class="enum">' + "".join(
            '<li><span class="mk">(%s)</span><span>%s</span></li>' % (mk, self.inline(t, sec)) for mk, t in itens) + "</ol>"
        if cauda:
            h += "<p%s>%s</p>" % (c, self.inline(cauda, sec))
        return h

    def paragrafo_com_estado(self, md, sec, inicio=False, cls=""):
        """Um estado no início do texto vai para uma linha própria. inicio=True: o texto vinha a seguir a um
        rótulo que passou a título do bloco, por isso a primeira letra sobe a maiúscula."""
        m = self.re_estado.match(md) if self.re_estado else None
        if inicio:
            md = md[: m.end()] + " " + maiuscula(md[m.end():].strip()) if m else maiuscula(md)
        if m:
            resto = md[m.end():].strip()
            return '<div class="st-line">%s</div>%s' % (self.inline(m.group(0), sec), self.paragrafo(resto, sec, cls) if resto else "")
        return self.paragrafo(md, sec, cls)

    def tipo_de(self, rotulo):
        l = simples(rotulo).lower().strip()
        for chave, tipo in self.vocab:
            if l.startswith(chave):
                return tipo, True
        return "titulo", False

    def bloco_html(self, tipo, rotulo, corpo, sec=None, aninhado=False, rotulo_html=None):
        destaque = tipo in DESTAQUES
        curto = len(simples(rotulo)) <= 44 and "`" not in rotulo and tipo != "titulo"
        cls = "blk blk-%s" % tipo
        ico = ""
        if destaque:
            cls += " blk-call c-%s" % DESTAQUES[tipo][0]
            ico = '<span class="blk-i" aria-hidden="true">%s</span>' % DESTAQUES[tipo][1]
        if aninhado:
            cls += " nested"
        return '<div class="%s"><div class="blk-h%s">%s<span>%s</span></div><div class="blk-b">%s</div></div>' % (
            cls, " up" if curto else "", ico, rotulo_html if rotulo_html is not None else self.inline(rotulo, sec), corpo)

    def callout(self, tipo, titulo, corpo_html):
        return self.bloco_html(tipo, titulo, corpo_html, rotulo_html=esc(titulo))

    def render_tabela(self, b, sec):
        numerica = len(b["head"]) > 4 and all(re.fullmatch(r"-?[\d.,]+%?", c) for r in b["rows"] for c in r[1:])
        head = "".join("<th>%s</th>" % self.inline(c, sec) for c in b["head"])
        rows = "".join("<tr>" + "".join("<td>%s</td>" % self.inline(c, sec) for c in r) + "</tr>" for r in b["rows"])
        return '<div class="tbl%s"><table><thead><tr>%s</tr></thead><tbody>%s</tbody></table></div>' % (
            " tbl-num" if numerica else "", head, rows)

    def render_codigo(self, b):
        return ('<figure class="code"><figcaption><span>%s</span><button class="copy" type="button">%s</button>'
                '</figcaption><pre><code>%s</code></pre></figure>') % (
                    esc(b["lang"] or self.t["texto"]), self.t["copiar"], realce(b["text"], b["lang"]))

    def render_citacao(self, b, sec, nivel):
        if b.get("alerta"):
            return self.bloco_html(ALERTAS[b["alerta"]], "", self.render_blocos(b["blocks"], sec, nivel + 1), sec,
                                   rotulo_html=esc(self.t["alertas"][b["alerta"]]))
        bs = b["blocks"]
        if bs and bs[0]["t"] == "p":
            m = RE_ROTULO.match(bs[0]["text"])
            if m:
                tipo, _ = self.tipo_de(m.group(1))
                if tipo in DESTAQUES:
                    resto = bs[0]["text"][m.end():]
                    corpo = (self.paragrafo_com_estado(resto, sec, True) if resto.strip() else "") + self.render_blocos(bs[1:], sec, nivel + 1)
                    return self.bloco_html(tipo, m.group(1), corpo, sec)
        return '<blockquote class="quote">%s</blockquote>' % self.render_blocos(bs, sec, nivel + 1)

    def render_blocos(self, bs, sec, nivel):
        h = []
        for b in bs:
            t = b["t"]
            if t == "p":
                h.append(self.paragrafo_com_estado(b["text"], sec))
            elif t == "list":
                h.append(self.render_lista(b, sec, nivel))
            elif t == "code":
                h.append(self.render_codigo(b))
            elif t == "table":
                h.append(self.render_tabela(b, sec))
            elif t == "quote":
                h.append(self.render_citacao(b, sec, nivel))
            elif t == "hr":
                h.append('<hr class="rule">')
            elif t == "h":
                nv = min(max(b["level"], 3), 5)
                h.append('<h%d class="sub sub-%d"%s>%s</h%d>' % (nv, nv, ' id="%s"' % b["id"] if b.get("id") else "", self.inline(b["text"], sec), nv))
        return "".join(h)

    def render_lista(self, lst, sec, nivel):
        if lst["ordered"]:
            if nivel == 0 and sec is not None and sec.key in self.cartoes:
                return self.render_cartoes(lst, sec)
            return '<ol class="nums">' + "".join(
                '<li><span class="num">%d.</span><div class="num-b">%s</div></li>' % (it["num"], self.render_blocos(it["blocks"], sec, nivel + 1))
                for it in lst["items"]) + "</ol>"
        itens = []
        for it in lst["items"]:
            bs = it["blocks"]
            rot = tipo = None
            expl, resto = False, ""
            if bs and bs[0]["t"] == "p":
                m = RE_ROTULO.match(bs[0]["text"])
                if m:
                    rot, resto = m.group(1), bs[0]["text"][m.end():]
                    tipo, expl = self.tipo_de(rot)
            grande = len(bs) > 1 or (bs and bs[0]["t"] == "p" and len(bs[0]["text"]) > 220)
            itens.append((it, bs, rot, tipo, expl, resto, grande))
        modo_blocos = nivel == 0 and any(rot and (expl or grande) for _, _, rot, _, expl, _, grande in itens)
        partes = []
        for it, bs, rot, tipo, expl, resto, grande in itens:
            if rot and (modo_blocos or tipo in DESTAQUES):
                corpo = (self.paragrafo_com_estado(resto, sec, True) if resto.strip() else "") + self.render_blocos(bs[1:], sec, nivel + 1)
                partes.append(("bloco", self.bloco_html(tipo, rot, corpo, sec, not modo_blocos), it))
            else:
                partes.append(("item", self.render_blocos(bs, sec, nivel + 1), it))
        if modo_blocos:
            return '<div class="blocks">' + "".join(
                h if k == "bloco" else '<div class="blk blk-plain"><div class="blk-b">%s</div></div>' % h for k, h, _ in partes) + "</div>"
        out = []
        for k, h, it in partes:
            if k == "bloco":
                out.append('<li class="li-call">%s</li>' % h)
            elif it["task"] is not None:
                out.append('<li class="task%s"><span class="tk-box" aria-hidden="true">%s</span>%s</li>' % (
                    " done" if it["task"] else "", "☑" if it["task"] else "☐", h))
            else:
                out.append("<li>%s</li>" % h)
        return '<ul class="items">%s</ul>' % "".join(out)

    def render_cartoes(self, lst, sec):
        pref = self.cartoes[sec.key]
        out = ['<ol class="cards">']
        for it in lst["items"]:
            bs = it["blocks"]
            titulo, resto = "", ""
            if bs and bs[0]["t"] == "p":
                m = RE_NEGRITO_INI.match(bs[0]["text"])
                if m:
                    titulo, resto = m.group(1), bs[0]["text"][m.end():]
                else:
                    resto = bs[0]["text"]
            self._sem_link = {k for k, v in self.def_ids.items() if v == "%s-%d" % (pref, it["num"])}
            th = '<h3 class="card-t">%s</h3>' % self.inline(titulo, sec) if titulo else ""
            self._sem_link = set()
            corpo = (self.paragrafo(resto, sec) if resto.strip() else "") + self.render_blocos(bs[1:] if bs and bs[0]["t"] == "p" else bs, sec, 1)
            out.append('<li class="card" id="%s-%d"><div class="card-h"><span class="card-n">%d</span>%s</div>'
                       '<div class="card-b">%s</div></li>' % (pref, it["num"], it["num"], th, corpo))
        out.append("</ol>")
        return "".join(out)

    def md(self, texto, sec=None):
        """Markdown solto -> HTML, com as mesmas regras do documento."""
        return self.render_blocos(blocos(texto.strip("\n").split("\n")), sec, 0)

    # ---------------- peças para o guia visual ----------------

    def ref(self, alvo, texto=None):
        s = self.sec(alvo)
        if not s:
            return esc(str(texto or alvo))
        rot = texto or (("%s %s" % (self.nome[0], s.chip)) if s.chip else esc(simples(s.titulo)))
        return '<a class="nref" href="#%s" title="%s">%s</a>' % (s.key, atr(simples(s.titulo)), rot)

    def refs_txt(self, *alvos):
        """"notas 1, 2 e 3", cada número com o seu link."""
        if len(alvos) == 1:
            return self.ref(alvos[0])
        ls = [self.ref(a, (self.sec(a).chip or simples(self.sec(a).titulo)) if self.sec(a) else str(a)) for a in alvos]
        e = " e " if self.op("IDIOMA", "pt") == "pt" else " and "
        return "%s %s%s%s" % (self.nome[1], ", ".join(ls[:-1]), e, ls[-1])

    def jornada(self, passos):
        """passos: [(título, descrição_html, [códigos], [secções])] -> lista numerada com linha de ligação."""
        return '<ol class="journey">' + "".join(
            '<li><span class="jr-n">%d</span><div class="jr-c"><h3>%s</h3><p>%s</p>%s</div><div class="jr-notes">%s</div></li>' % (
                i + 1, t, d, '<div class="jr-api">%s</div>' % " ".join(self.c(a) for a in cods) if cods else "",
                self.refs_txt(*alvos) if alvos else "")
            for i, (t, d, cods, alvos) in enumerate(passos)) + "</ol>"

    def escada(self, linhas, alternativa=False):
        """linhas: [(marca, condição_html, resultado, detalhe_html)] -> "se isto, então aquilo", por ordem."""
        return '<div class="ladder%s">' % (" ladder-alt" if alternativa else "") + "".join(
            '<div class="ld-row"><span class="ld-n">%s</span><div class="ld-if">%s</div><span class="ld-a" aria-hidden="true">→</span>'
            '<div class="ld-then"><span class="screen%s">%s</span><span class="ld-x">%s</span></div></div>' % (
                n, cond, " screen-off" if alternativa else "", res, det) for n, cond, res, det in linhas) + "</div>"

    def fluxo_cartoes(self, cartoes):
        """cartoes: [(título, corpo_html, destaque)] -> cartões lado a lado, ligados por setas."""
        return '<div class="gates" style="--n:%d">' % len(cartoes) + "".join(
            '<div class="gate%s"><div class="gate-k"><span>%d</span> %s</div>%s</div>' % (" gate-flag" if dest else "", i + 1, t, corpo)
            for i, (t, corpo, dest) in enumerate(cartoes)) + "</div>"

    def pares(self, linhas):
        """linhas: [(chave, valor_html)] -> linhas tracejadas chave / valor."""
        return '<div class="gates-extra">' + "".join(
            '<div class="gx"><span class="gx-k">%s</span><span class="gx-v">%s</span></div>' % (k, v) for k, v in linhas) + "</div>"

    def tabela(self, cabecalho, linhas):
        """Células já em HTML."""
        return '<div class="tbl"><table><thead><tr>%s</tr></thead><tbody>%s</tbody></table></div>' % (
            "".join("<th>%s</th>" % x for x in cabecalho),
            "".join("<tr>" + "".join("<td>%s</td>" % x for x in r) + "</tr>" for r in linhas))

    def figura(self, conteudo, legenda="", rolavel=True):
        cap = "<figcaption>%s</figcaption>" % legenda if legenda else ""
        return '<figure class="fig">%s%s</figure>' % ('<div class="fig-scroll">%s</div>' % conteudo if rolavel else conteudo, cap)

    def linha_tempo(self, entradas):
        """entradas: [(data_ou_marca, html)]"""
        return '<ol class="timeline">' + "".join(
            '<li><span class="tl-d">%s</span><div class="tl-t">%s</div></li>' % (d, h) for d, h in entradas) + "</ol>"

    def legenda_estados(self):
        if not self.estados:
            return ""
        total = len(self.seccoes)
        return '<div class="legend">' + "".join(
            '<div class="lg"><div class="lg-h">%s</div>%s<p class="lg-c">%s %d %s %d %s</p></div>' % (
                self.pilula(e), "<p>%s</p>" % self.inline(e["desc"]) if e.get("desc") else "",
                self.t["em"], sum(1 for s in self.seccoes if e["id"] in s.estados), self.t["das"], total, self.nome[1])
            for e in self.estados) + "</div>"

    def pontos(self, estados):
        return "".join('<i class="dot c-%s f-%s" title="%s"></i>' % (e["cor"], e["forma"], atr(e["rotulo"]))
                       for e in self.estados if e["id"] in estados)

    # ---------------- montagem ----------------

    def render_intro(self):
        out = []
        for b in self.intro:
            if b["t"] == "quote" and not b.get("alerta"):
                out.append(self.render_blocos(b["blocks"], None, 0))
            else:
                out.append(self.render_blocos([b], None, 0))
        return "".join(out)

    def gerar(self):
        t = self.t
        figuras = {self.sec(k).key: v for k, v in (self.op("FIGURAS", {}) or {}).items() if self.sec(k)}
        lead = bool(self.op("LEAD", False))

        for s in self.seccoes:
            partes, usou = [], False
            for i, b in enumerate(s.blocos):
                if b["t"] == "p":
                    partes.append(self.paragrafo_com_estado(b["text"], s, cls="lead" if (lead and i == 0) else ""))
                else:
                    partes.append(self.render_blocos([b], s, 0))
                if not usou and s.key in figuras and b["t"] == "p":
                    partes.append(figuras[s.key])
                    usou = True
            if s.key in figuras and not usou:
                partes.insert(0, figuras[s.key])
            s.titulo_html = self.inline(s.titulo, s)
            s.html = "".join(partes)
            for e in self.estados:                  # estados reconhecidos por expressão regular
                if e.get("re"):
                    alvo = s.titulo if e["onde"] == "titulo" else "\n".join(self.linhas[s.linha:s.fim])
                    if e["re"].search(alvo):
                        s.estados.add(e["id"])

        for p in self.fluxo:
            if isinstance(p, dict):
                p["html"] = self.render_blocos(p["blocos"], None, 0)
                p["key"] = self._unico(slug(p["titulo"]))
        intro_fn = self.op("introducao")
        intro_html = intro_fn(self, self.intro) if intro_fn else self.render_intro() + self.legenda_estados()

        # temas, etiquetas, ligações
        temas = self.op("TEMAS", []) or []
        tema_de = {}
        for nome, alvos in temas:
            for a in alvos:
                if self.sec(a):
                    tema_de[self.sec(a).key] = nome
        etiquetas = {}
        for a, lst in (self.op("ETIQUETAS", {}) or {}).items():
            if self.sec(a):
                etiquetas[self.sec(a).key] = [lst] if isinstance(lst, tuple) else list(lst)
        ponteiros = {self.sec(a).key: v for a, v in (self.op("PONTEIROS", {}) or {}).items() if self.sec(a)}
        chip_alerta = self.op("FILTRO_ETIQUETA")
        for s in self.seccoes:
            s.rel = sorted((s.refs | {o.key for o in self.seccoes if s.key in o.refs}) - {s.key},
                           key=lambda k: self.seccoes.index(self.por_key[k]))

        paineis = []
        for p in self.fluxo:
            if isinstance(p, dict):
                paineis.append('<div class="part-sep sec" id="%s"><h2>%s</h2>%s</div>' % (
                    p["key"], self.inline(p["titulo"]), '<div class="prose">%s</div>' % p["html"] if p["html"] else ""))
                continue
            s = p
            meta = []
            if s.key in tema_de:
                meta.append('<span class="tag tag-theme">%s</span>' % esc(tema_de[s.key]))
            meta += [self.pilula(e, mini=True) for e in self.estados if e["id"] in s.estados]
            tags = etiquetas.get(s.key, [])
            meta += ['<span class="tag tag-%s">%s</span>' % ("gate" if k == "alerta" else "calm", esc(txt)) for k, txt in tags]
            extra = ""
            if s.rel:
                extra += '<span class="rel"><span class="rel-l">%s</span>%s</span>' % (t["liga"], "".join(
                    '<a class="nref" href="#%s" title="%s">%s</a>' % (k, atr(self.ancoras[k]), esc(self.por_key[k].chip or simples(self.por_key[k].titulo)[:28]))
                    for k in s.rel))
            if s.key in ponteiros:
                extra += '<a class="guide-link" href="#%s">%s: %s</a>' % (ponteiros[s.key][0], t["no_guia"], esc(ponteiros[s.key][1]))
            chip = '<a class="note-n" href="#%s">%s</a>' % (s.key, esc(s.chip)) if s.chip else ""
            paineis.append(
                '<section class="note%s" id="%s" data-k="%s" data-st="%s" data-gate="%s">'
                '<header class="note-h">%s<div class="note-hd"><h2>%s</h2>%s%s</div></header>'
                '<div class="note-b">%s</div></section>' % (
                    "" if s.chip else " note-plain", s.key, s.key, " ".join(sorted(s.estados)),
                    "1" if any(k == "alerta" for k, _ in tags) else "0", chip, s.titulo_html,
                    '<div class="note-meta">%s</div>' % "".join(meta) if meta else "",
                    '<div class="note-meta note-meta2">%s</div>' % extra if extra else "", s.html))

        # guia visual
        guia_fn = self.op("guia")
        guia_secs = [tuple(x) + ("",) * (4 - len(x)) for x in (guia_fn(self) if guia_fn else [])]
        temas_html = ""
        if temas:
            temas_html = '<section class="sec" id="temas"><h2>%s</h2><p class="sec-sub">%s</p><div class="themes">%s</div></section>' % (
                esc(self.op("TEMAS_TITULO", t["temas"])), esc(self.op("TEMAS_NOTA", t["temas_sub"])), "".join(
                    '<div class="theme"><h3>%s</h3><ul>%s</ul></div>' % (esc(nome), "".join(
                        '<li><a href="#%s">%s<span class="th-t">%s</span><span class="dots">%s</span></a></li>' % (
                            self.sec(a).key, '<span class="th-n">%s</span>' % esc(self.sec(a).chip) if self.numeradas else "",
                            esc(simples(self.sec(a).titulo)), self.pontos(self.sec(a).estados))
                        for a in alvos if self.sec(a))) for nome, alvos in temas))
        guia_html = ""
        if guia_secs or temas_html:
            guia_html = '<div class="part"><p class="part-k">%s</p><h2 class="part-t">%s</h2><p class="sec-sub">%s</p>%s%s</div>' % (
                t["guia"], esc(self.op("GUIA_TITULO", t["guia"])), esc(self.op("GUIA_NOTA", t["guia_nota"])),
                "".join('<section class="sec" id="%s"><h2>%s</h2>%s%s</section>' % (
                    gid, gt, '<p class="sec-sub">%s</p>' % gsub if gsub else "", gh) for gid, gt, gh, gsub in guia_secs),
                temas_html)

        # barra lateral
        nav = []
        if intro_html.strip():
            nav.append('<div class="side-g">%s</div><a class="plain" href="#intro">%s</a>' % (t["documento"], esc(self.op("INTRO_TITULO", t["intro"]))))
        if guia_secs or temas_html:
            nav.append('<div class="side-g">%s</div>' % t["guia"])
            nav += ['<a class="plain" href="#%s">%s</a>' % (gid, texto_de(gt).strip()) for gid, gt, _, _ in guia_secs]
            if temas_html:
                nav.append('<a class="plain" href="#temas">%s</a>' % esc(self.op("TEMAS_TITULO", t["temas"])))
        if not any(isinstance(p, dict) for p in self.fluxo[:1]):
            nav.append('<div class="side-g">%s</div>' % esc(self.nome[1].capitalize()))
        for p in self.fluxo:
            if isinstance(p, dict):
                nav.append('<a class="side-g side-part" href="#%s">%s</a>' % (p["key"], esc(simples(p["titulo"]))))
            else:
                nav.append('<a href="#%s" data-k="%s"%s>%s<span class="stt">%s</span><span class="dots">%s</span></a>' % (
                    p.key, p.key, "" if self.numeradas else ' class="nonum"',
                    '<span class="sn">%s</span>' % esc(p.chip) if self.numeradas else "", esc(simples(p.titulo)), self.pontos(p.estados)))

        # filtro
        filtro = ""
        if len(self.seccoes) >= 8 or self.estados:
            chips = ['<button class="chip" type="button" data-st="%s" aria-pressed="false"><i class="dot c-%s f-%s"></i>%s</button>' % (
                e["id"], e["cor"], e["forma"], esc(e["curto"])) for e in self.estados]
            if chip_alerta and any(k == "alerta" for v in etiquetas.values() for k, _ in v):
                chips.append('<button class="chip" type="button" data-gate="1" aria-pressed="false">%s</button>' % esc(chip_alerta))
            filtro = (
                '<div class="filter"><label class="sr" for="q">%s</label>'
                '<input id="q" type="search" placeholder="%s" autocomplete="off">%s'
                '<div class="f-count"><span id="count" aria-live="polite" data-de="%s" data-nome="%s"></span>'
                '<button id="clear" type="button" hidden>%s</button></div></div>'
                '<div class="empty" id="empty" hidden>%s <button class="copy" id="empty-clear" type="button">%s</button></div>') % (
                    t["filtrar_rotulo"], atr(t["filtrar"]),
                    '<div class="chips" role="group">%s</div>' % "".join(chips) if chips else "",
                    t["de"], atr(self.nome[1]), t["limpar"], t["vazio"], t["limpar_filtro"])

        mtime = datetime.date.fromtimestamp(self.fonte.stat().st_mtime)
        factos = self.op("FACTOS")
        if factos is None:
            factos = ["<b>%d</b> %s" % (len(self.seccoes), self.nome[1] if len(self.seccoes) != 1 else self.nome[0]),
                      "%s <b>%s</b>" % (t["fonte_de"], mtime.strftime("%d/%m/%Y")), "%s: %s" % (t["fonte"], esc(self.fonte.name))]
        voltar = self.op("VOLTAR")
        titulo_aba = self.op("TITULO_ABA") or simples(self.titulo_md)[:60]
        pagina = PAGINA
        for chave, valor in {
            "%%LANG%%": self.op("IDIOMA", "pt"),
            "%%ABA%%": esc(titulo_aba),
            "%%CSS%%": CSS,
            "%%JS%%": JS.replace("%%COPIAR%%", t["copiar"]).replace("%%COPIADO%%", t["copiado"]).replace("%%SELECIONADO%%", t["selecionado"]),
            "%%INDICE%%": t["indice"],
            "%%SOBRE%%": esc(self.op("SOBRETITULO", "")),
            "%%MARCA%%": esc(titulo_aba),
            "%%TITULO_TXT%%": esc(simples(self.titulo_md)),
            "%%TITULO%%": self.inline(self.titulo_md),
            "%%VOLTAR%%": '<p class="back"><a href="%s">%s</a></p>' % (atr(voltar[0]), esc(voltar[1])) if voltar else "",
            "%%EYEBROW%%": '<p class="eyebrow">%s</p>' % esc(self.op("SOBRETITULO")) if self.op("SOBRETITULO") else "",
            "%%FACTOS%%": "".join("<span>%s</span>" % f for f in factos),
            "%%INTRO%%": '<section class="sec intro" id="intro">%s</section>' % intro_html if intro_html.strip() else "",
            "%%GUIA%%": guia_html,
            "%%NAV%%": "".join(nav),
            "%%FILTRO%%": filtro,
            "%%PAINEIS%%": "".join(paineis),
            "%%RODAPE%%": t["rodape"].format(f=esc(self.fonte.name)),
        }.items():
            pagina = pagina.replace(chave, valor)
        self.pagina = pagina
        return pagina

    def conferir(self):
        """Todas as palavras da fonte estão na página, pela mesma ordem (por secção)?"""
        ok, msgs = True, []
        blocos_html = dict(re.findall(r'<section class="note[^"]*" id="([^"]+)"(.*?)</section>', self.pagina, re.S))
        for s in self.seccoes:
            fonte = palavras(fonte_limpa("\n".join(self.linhas[s.linha:s.fim])))
            falha = subsequencia(fonte, palavras(texto_de(blocos_html.get(s.key, ""))))
            if falha >= 0:
                ok = False
                msgs.append("FALHA em «%s»: falta «%s» (… %s …)" % (s.chip or s.titulo[:30], fonte[falha], " ".join(fonte[max(0, falha - 6): falha + 4])))
        resto = [l for i, l in enumerate(self.linhas) if i >= self.pre and not any(s.linha <= i < s.fim for s in self.todas)]
        falta = Counter(palavras(fonte_limpa("\n".join(resto)))) - Counter(palavras(texto_de(self.pagina)))
        if falta:
            ok = False
            msgs.append("FALHA fora das secções: faltam %s" % dict(falta))
        return ok, msgs


def variante_artifact(pagina):
    """A mesma página sem doctype/html/head/body (o Artifact acrescenta os seus) e sem o link de volta,
    que só existe na pasta do documento."""
    head = re.search(r"<head>(.*?)</head>", pagina, re.S).group(1)
    head = re.sub(r'<meta charset[^>]*>\n?|<meta name="viewport"[^>]*>\n?|<link rel="preconnect"[^>]*>\n?', "", head)
    body = re.search(r"<body>(.*)</body>", pagina, re.S).group(1)
    body = re.sub(r'\s*<p class="back">.*?</p>', "", body, count=1, flags=re.S)
    return '<meta name="claude:viewport-fit-sides" content="cover">\n' + head.strip() + "\n" + body.strip() + "\n"


# --------------------------------------------------------------------------
# --analisar: retrato do documento, para escrever a configuração
# --------------------------------------------------------------------------

def analisar(fonte):
    md = Path(fonte).read_text(encoding="utf-8")
    fora, dentro, linguas = [], False, Counter()
    for l in md.split("\n"):
        m = RE_FENCE.match(l)
        if m:
            if not dentro and m.group(2):
                linguas[m.group(2)] += 1
            dentro = not dentro
            continue
        if not dentro:
            fora.append(l)
    txt = "\n".join(fora)
    sem_codigo = re.sub(r"`[^`\n]*`", " ", txt)
    niveis = Counter(len(m.group(1)) for l in fora for m in [RE_HEAD.match(l)] if m)
    print("Documento: %s (%d linhas)" % (Path(fonte).name, md.count("\n") + 1))
    print("Cabeçalhos: " + "  ".join("h%d×%d" % (k, niveis[k]) for k in sorted(niveis)))
    for nv in (2, 3):
        tits = [RE_HEAD.match(l).group(2) for l in fora if RE_HEAD.match(l) and len(RE_HEAD.match(l).group(1)) == nv]
        if tits:
            num = sum(1 for x in tits if re.match(r"§?\d+(\.\d+)*[.)]?\s", x))
            print("  NIVEL = %d daria %d painéis (%d numerados). Ex.: %s" % (nv, len(tits), num, " | ".join(x[:40] for x in tits[:3])))

    def top(titulo, itens, minimo=2, n=12):
        c = Counter(itens)
        linhas = ["%s ×%d" % (k, v) for k, v in c.most_common(n) if v >= minimo]
        print("%s: %s" % (titulo, ", ".join(linhas) if linhas else "nenhum"))

    top("Rótulos em negrito no início de item/parágrafo (candidatos a ROTULOS)",
        [re.sub(r"\s*\(.*", "", m.group(1)).strip() for l in fora for m in [re.match(r"^\s*(?:[-*+] |\d+[.)] |> ?)?\*\*([^*]{2,60}?):\*\*", l)] if m])
    top("Marcas [entre parênteses rectos] (candidatas a ESTADOS)",
        [re.sub(r",.*", "", m).strip() for m in re.findall(r"(?<![!\]`])\[([a-zà-ÿA-Z][^\]\n`]{2,40})\](?!\()", sem_codigo)])
    top("Identificadores (candidatos a IDS)", [re.sub(r"\d+", "n", m) for m in re.findall(r"(?<![\w-])([A-Z]{1,4}-\d+)(?![\w-])", sem_codigo)], 3)
    top("Referências «palavra N» (candidatas a REFERENCIAS)",
        [m.lower() for m in re.findall(r"(?<![\w-])([A-Za-zÀ-ÿ§]{3,12}) \d+(?![\w.%-])", sem_codigo)
         if m.lower() not in {"até", "aos", "dos", "das", "com", "por", "para", "mais", "menos", "cerca", "entre", "the", "and", "for", "from", "than"}], 4)
    top("Símbolo colado a número", re.findall(r"([§#])\d+", sem_codigo), 3)
    print("Código por linguagem: %s" % (", ".join("%s ×%d" % kv for kv in linguas.most_common()) or "nenhum"))
    print("Tabelas: %d · citações: %d · tarefas: %d · listas numeradas: %d itens · links: %d · imagens: %d" % (
        sum(1 for l in fora if RE_TSEP.match(l) and "|" in l), sum(1 for l in fora if l.lstrip().startswith(">")),
        len(re.findall(r"^\s*[-*+] \[[ xX]\] ", txt, re.M)), len(re.findall(r"^\s*\d+[.)] ", txt, re.M)),
        len(RE_LINK.findall(txt)), len(RE_IMG.findall(txt))))
    print("Enumerações em linha «(a) … (b) …»: %d parágrafos" % sum(1 for l in re.split(r"\n\s*\n", txt) if enumeracao(" ".join(l.split()))))


def carregar_config(caminho):
    sys.dont_write_bytecode = True      # sem __pycache__ ao lado do documento
    spec = importlib.util.spec_from_file_location("dracula_cfg", str(caminho))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    def opcao(nome):
        return argv[argv.index(nome) + 1] if nome in argv and argv.index(nome) + 1 < len(argv) else None
    valores = {opcao(x) for x in ("--config", "--saida", "--artifact")}
    args = [a for a in args if a not in valores]
    if not args:
        print(__doc__)
        return 2
    fonte = Path(args[0]).resolve()
    if "--analisar" in argv:
        analisar(fonte)
        return 0
    cfg_path = Path(opcao("--config")) if opcao("--config") else fonte.with_name(fonte.stem + ".dracula.py")
    cfg = carregar_config(cfg_path) if cfg_path.exists() else None
    m = Motor(fonte, cfg)
    pagina = m.gerar()
    saida = Path(opcao("--saida")) if opcao("--saida") else fonte.with_name(fonte.stem + "-dracula.html")
    saida.write_text(pagina, encoding="utf-8")
    if opcao("--artifact"):
        Path(opcao("--artifact")).write_text(variante_artifact(pagina), encoding="utf-8")
        print("variante para artifact:", opcao("--artifact"))
    ok, msgs = m.conferir()
    print("configuração: %s" % (cfg_path if cfg else "nenhuma (só as regras por omissão)"))
    print("%d %s (nível h%d)%s" % (len(m.seccoes), m.nome[1], m.nivel,
                                  "; omitidas: " + ", ".join(simples(s.titulo) for s in m.omitidas) if m.omitidas else ""))
    if m.estados:
        print("estados: " + ", ".join("%s em %d" % (e["rotulo"], sum(1 for s in m.seccoes if e["id"] in s.estados)) for e in m.estados))
    en = m.relatorio["enum"]
    if en:
        print("enumerações «(a) … (b) …» separadas: %d%s" % (len(en), " " + str(en) if len(en) <= 10 else " (em %d secções)" % len({x[0] for x in en})))
    for a in m.avisos:
        print("AVISO:", a)
    for x in msgs:
        print(x)
    print("conferência do texto:", "OK, nada se perdeu" if ok else "COM FALHAS")
    print("escrito: %s (%d KB)" % (saida, len(pagina.encode("utf-8")) // 1024))
    return 0 if ok else 1


# --------------------------------------------------------------------------
# Página
# --------------------------------------------------------------------------

CSS = r"""
/* Layout: barra lateral fixa, como o explorador de um editor, e uma coluna de leitura; cada secção é um painel na cor de fundo do Dracula. */
:root{
  color-scheme:dark;
  --bg:#21222c; --bg-deep:#191a21; --surface:#282a36; --surface-2:#2f3142;
  --line:#383a4c; --line-strong:#44475a; --comment:#6272a4;
  --fg:#f8f8f2; --text:#dcdde9; --muted:#a2aaca;
  --cyan:#8be9fd; --green:#50fa7b; --orange:#ffb86c; --pink:#ff79c6; --purple:#bd93f9; --red:#ff5555; --yellow:#f1fa8c;
  --code-bg:rgba(98,114,164,.2);
  --font-text:"IBM Plex Sans",system-ui,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
  --font-mono:"IBM Plex Mono",ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
  --side-w:312px;
}
.c-green{--c:var(--green)} .c-cyan{--c:var(--cyan)} .c-orange{--c:var(--orange)} .c-pink{--c:var(--pink)}
.c-purple{--c:var(--purple)} .c-red{--c:var(--red)} .c-yellow{--c:var(--yellow)} .c-muted{--c:var(--muted)}
*{box-sizing:border-box}
[hidden]{display:none!important}
html{scroll-behavior:smooth;-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--text);font:400 16px/1.68 var(--font-text)}
::selection{background:var(--line-strong);color:var(--fg)}
a{color:var(--cyan);text-decoration:none}
a:hover{text-decoration:underline}
:focus-visible{outline:2px solid var(--purple);outline-offset:2px;border-radius:4px}
strong{color:var(--fg);font-weight:600}
p{margin:0}
h1,h2,h3,h4,h5{color:var(--fg);font-weight:600;text-wrap:balance}
img{max-width:100%;height:auto;border-radius:8px}

/* código em linha */
code{font:500 .86em var(--font-mono);background:var(--code-bg);color:var(--fg);padding:.12em .4em;border-radius:5px;overflow-wrap:anywhere}
code.k{color:var(--purple)}
code.hs{font-weight:600}
.hs-2{color:var(--green)} .hs-3{color:var(--cyan)} .hs-4{color:var(--orange)} .hs-5{color:var(--red)}
.vb{font-weight:600}
.vb-get{color:var(--cyan)} .vb-post{color:var(--green)} .vb-put{color:var(--orange)} .vb-patch{color:var(--yellow)} .vb-delete{color:var(--red)}

/* referências e identificadores */
.nref{text-decoration:underline dotted;text-underline-offset:3px;font-weight:500}
.nref:hover{text-decoration-style:solid}
.pid{font:500 .82em var(--font-mono);color:var(--c);border:1px solid color-mix(in srgb,var(--c) 40%,transparent);border-radius:5px;padding:.05em .4em;white-space:nowrap}
.pid.c-muted{border-color:transparent;padding:0}
a.pid:hover{background:color-mix(in srgb,var(--c) 12%,transparent);text-decoration:none}

/* estados */
.st{display:inline-block;max-width:100%;font:500 .74rem/1.5 var(--font-mono);padding:.14em .7em .14em .6em;border-radius:11px;vertical-align:.08em;overflow-wrap:anywhere;
  color:var(--c);border:1px solid color-mix(in srgb,var(--c) 44%,transparent);background:color-mix(in srgb,var(--c) 7%,transparent)}
.st-l::before{content:"";display:inline-block;width:.62em;height:.62em;border-radius:50%;margin-right:.5em;vertical-align:.02em}
.f-cheio .st-l::before,.dot.f-cheio{background:var(--c)}
.f-meio .st-l::before,.dot.f-meio{background:linear-gradient(90deg,var(--c) 50%,transparent 50%);box-shadow:inset 0 0 0 1.5px var(--c)}
.f-oco .st-l::before,.dot.f-oco{box-shadow:inset 0 0 0 1.5px var(--c)}
.st-c{margin-left:.6em;padding-left:.6em;border-left:1px solid color-mix(in srgb,var(--c) 44%,transparent);color:var(--text)}
.st-mini{font-size:.7rem;background:transparent}
.st-line{margin-bottom:5px}
.dots{display:inline-flex;gap:4px;align-items:center}
.dot{display:inline-block;width:8px;height:8px;border-radius:50%}

.tag{display:inline-block;font:500 .72rem/1.5 var(--font-text);padding:.14em .7em;border-radius:6px;border:1px solid var(--line-strong);color:var(--muted)}
.tag-theme{color:var(--purple);border-color:rgba(189,147,249,.4)}
.tag-gate{color:var(--red);border-color:rgba(255,85,85,.5);background:rgba(255,85,85,.08)}
.tag-calm{color:var(--muted)}

/* estrutura */
.shell{display:grid;grid-template-columns:var(--side-w) minmax(0,1fr);min-height:100vh}
.side{position:sticky;top:0;height:100vh;overflow-y:auto;background:var(--bg-deep);border-right:1px solid var(--line);padding:22px 12px 40px;font-size:.84rem;scrollbar-width:thin;scrollbar-color:var(--line-strong) transparent}
.side-brand{padding:0 10px 14px;margin-bottom:6px;border-bottom:1px solid var(--line)}
.side-brand b{display:block;color:var(--fg);font-weight:600;font-size:.95rem}
.side-brand span{font:500 .72rem var(--font-mono);color:var(--muted)}
.side-g{display:block;font:600 .68rem var(--font-mono);letter-spacing:.12em;text-transform:uppercase;color:var(--comment);padding:16px 10px 6px}
.side a{display:grid;grid-template-columns:30px minmax(0,1fr) auto;gap:8px;align-items:baseline;padding:5px 10px;border-radius:6px;color:var(--muted);line-height:1.35}
.side a.plain,.side a.nonum{grid-template-columns:minmax(0,1fr) auto}
.side a.side-part{display:block;color:var(--comment);padding:16px 10px 6px}
.side a:hover{background:var(--surface);color:var(--fg);text-decoration:none}
.side a.on{background:var(--surface);color:var(--fg);box-shadow:inset 2px 0 0 var(--purple)}
.sn{font:500 .76rem var(--font-mono);color:var(--purple);text-align:right;white-space:nowrap}
.side .dots{align-self:center}
.side .dot{width:6px;height:6px}
.main{min-width:0;padding-block:44px 96px;padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px))}
.col{max-width:880px;margin:0 auto}
.topbar,.scrim{display:none}

/* cabeçalho */
.back{font-size:.86rem;margin-bottom:26px}
.eyebrow{font:500 .74rem var(--font-mono);letter-spacing:.14em;text-transform:uppercase;color:var(--purple)}
h1{font-size:clamp(1.85rem,4.2vw,2.6rem);line-height:1.12;letter-spacing:-.012em;margin:10px 0 16px}
.facts{display:flex;flex-wrap:wrap;gap:6px 22px;font:500 .8rem var(--font-mono);color:var(--muted)}
.facts b{color:var(--fg);font-weight:600}

.sec{margin-top:60px;scroll-margin-top:24px}
.sec>h2{font-size:1.45rem;line-height:1.25;margin:0 0 8px}
.sec-sub{color:var(--muted);max-width:68ch;margin-bottom:22px}
.part{margin-top:84px;padding-top:30px;border-top:1px solid var(--line-strong)}
.part-k{font:600 .72rem var(--font-mono);letter-spacing:.14em;text-transform:uppercase;color:var(--purple)}
.part h2.part-t{font-size:1.9rem;line-height:1.15;margin:8px 0 10px}
.part .sec:first-of-type{margin-top:40px}
.intro{margin-top:36px;display:flex;flex-direction:column;gap:14px;font-size:1.03rem}
.intro>p{max-width:72ch}
.intro-lead{font-size:1.05rem;max-width:70ch}
.prose{display:flex;flex-direction:column;gap:14px;margin-top:10px}
.part-sep{margin:26px 0 0}
.part-sep>h2{font-size:1.5rem;padding-top:26px;border-top:1px solid var(--line-strong)}

/* legenda */
.legend{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px;margin-top:8px}
.lg{background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:16px 18px;display:flex;flex-direction:column;gap:10px;font-size:.92rem}
.lg-c{margin-top:auto;font:500 .74rem var(--font-mono);color:var(--muted)}
.kinds{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:8px 22px;font-size:.9rem}
.kind{display:grid;grid-template-columns:22px minmax(0,1fr);gap:10px;align-items:baseline}
.kind i{font:600 .82rem var(--font-mono);font-style:normal;text-align:center;color:var(--c)}
.kind b{color:var(--c);font-weight:600}
.conv{color:var(--muted);font-size:.9rem;max-width:74ch}

/* histórico / linha do tempo em lista */
.latest{background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:18px 20px}
.latest-k{font:600 .72rem var(--font-mono);letter-spacing:.1em;text-transform:uppercase;color:var(--yellow);margin-bottom:8px}
.older>summary{cursor:pointer;color:var(--cyan);font-size:.92rem;padding:6px 0;width:max-content;max-width:100%}
.timeline{list-style:none;margin:14px 0 0;padding:0;display:flex;flex-direction:column;gap:16px;font-size:.92rem}
.timeline li{display:grid;grid-template-columns:104px minmax(0,1fr);gap:16px}
.tl-d{font:500 .78rem/1.9 var(--font-mono);color:var(--purple)}

/* jornada */
.journey{list-style:none;margin:0;padding:0}
.journey>li{display:grid;grid-template-columns:40px minmax(0,1fr) minmax(120px,auto);gap:16px;padding-bottom:22px;position:relative}
.journey>li::before{content:"";position:absolute;left:19px;top:40px;bottom:0;width:2px;background:var(--line-strong)}
.journey>li:last-child{padding-bottom:0}
.journey>li:last-child::before{display:none}
.jr-n{width:40px;height:40px;border-radius:50%;display:grid;place-items:center;font:600 .95rem var(--font-mono);color:var(--bg-deep);background:var(--purple);position:relative}
.jr-c h3{margin:6px 0 4px;font-size:1.08rem}
.jr-c p{font-size:.95rem;max-width:62ch}
.jr-api{display:flex;flex-wrap:wrap;gap:6px;margin-top:10px;font-size:.92rem}
.jr-notes{font-size:.86rem;color:var(--muted);padding-top:9px;text-align:right}

/* figuras e diagramas SVG */
.fig{margin:0}
.fig-scroll{overflow-x:auto;background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:20px 18px 16px}
.note .fig-scroll{background:var(--surface-2)}
.fig figcaption,.fig-note{margin-top:12px;color:var(--muted);font-size:.88rem;max-width:74ch}
.dia{display:block;width:100%;min-width:640px;height:auto}
.dia text{font-family:var(--font-text);fill:var(--text)}
.dia .tm{font:600 12px var(--font-mono);fill:var(--fg)}
.dia .ts{font-size:11px;fill:var(--muted)}
.dia .tl{font-size:12.5px;fill:var(--muted)}
.dia .tl2{font-size:13px;font-weight:600;fill:var(--fg)}
.dia .tk{font:500 11px var(--font-mono);fill:var(--muted)}
.dia .tb{font:500 11.5px var(--font-mono);fill:var(--fg)}
.dia .tb.off{fill:var(--muted)}
.dia .guide line{stroke:var(--line-strong);stroke-width:1;stroke-dasharray:3 4}
.dia .b{stroke-width:1.2}
.b-purple{fill:rgba(189,147,249,.18);stroke:var(--purple)}
.b-green{fill:rgba(80,250,123,.14);stroke:var(--green)}
.b-orange{fill:rgba(255,184,108,.18);stroke:var(--orange)}
.b-cyan{fill:rgba(139,233,253,.15);stroke:var(--cyan)}
.b-yellow{fill:rgba(241,250,140,.12);stroke:var(--yellow)}
.b-pink{fill:rgba(255,121,198,.15);stroke:var(--pink)}
.b-red{fill:rgba(255,85,85,.15);stroke:var(--red)}
.b-plain{fill:var(--surface-2);stroke:var(--line-strong)}
.b-off{fill:transparent;stroke:var(--line-strong);stroke-dasharray:4 3}
.dia .axis{stroke:var(--line-strong);stroke-width:2;fill:none}
.dia .axis-dash{stroke-dasharray:3 5}
.dia .arrow{stroke:var(--muted);stroke-width:1.5;fill:none}
.dia .arrow-head{fill:var(--muted)}
.mk-push{fill:var(--pink);stroke:var(--surface-2);stroke-width:2}
.mk-chat{fill:var(--cyan);stroke:var(--surface-2);stroke-width:2}
.fig-inline .half{background:var(--surface-2);border:1px solid var(--line);border-radius:10px;padding:14px 16px;display:flex;flex-direction:column;gap:10px}
.half-row{display:grid;grid-template-columns:auto minmax(0,1fr) auto;gap:14px;align-items:center;font-size:.92rem}
.half-dots{display:inline-flex;gap:5px}
.half-dots i{width:13px;height:13px;border-radius:50%;box-shadow:inset 0 0 0 1.5px var(--comment)}
.half-dots i.on{background:var(--green);box-shadow:none}
.half-v{font:600 .76rem var(--font-mono);padding:.14em .7em;border-radius:6px;border:1px solid}
.half-ok{color:var(--green)} .half-no{color:var(--red)}

/* escada "se isto, então aquilo" */
.ladder{background:var(--surface);border:1px solid var(--line);border-radius:12px;overflow:hidden}
.ld-row{display:grid;grid-template-columns:30px minmax(0,.85fr) 20px minmax(0,1.25fr);gap:14px;align-items:center;padding:14px 18px;border-top:1px solid var(--line)}
.ld-row:first-child{border-top:0}
.ld-n{font:600 .82rem var(--font-mono);color:var(--bg-deep);background:var(--purple);width:26px;height:26px;border-radius:50%;display:grid;place-items:center}
.ld-a{color:var(--comment);font-family:var(--font-mono)}
.ld-then{display:flex;flex-direction:column;gap:5px;align-items:flex-start}
.screen{font-weight:600;color:var(--fg);background:var(--surface-2);border:1px solid var(--line-strong);border-radius:8px;padding:.3em .75em;font-size:.95rem}
.screen-off{color:var(--muted);font-weight:500}
.ld-x{font-size:.84rem;color:var(--muted)}
.ladder-alt{margin-top:10px;border-style:dashed}
.ladder-alt .ld-n{background:transparent;color:var(--comment)}

/* cartões em fluxo */
.gates{display:grid;grid-template-columns:repeat(var(--n,3),minmax(0,1fr));gap:26px}
.gate{background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:18px 18px 16px;position:relative;font-size:.92rem;display:flex;flex-direction:column;gap:8px}
.gate:not(:last-child)::after{content:"→";position:absolute;right:-21px;top:20px;color:var(--comment);font:600 1rem var(--font-mono)}
.gate-flag{border-color:rgba(80,250,123,.5)}
.gate-flag p code{font-size:.78em;white-space:nowrap}
.gate-k{font-weight:600;color:var(--fg);font-size:1rem;display:flex;gap:10px;align-items:center;margin-bottom:4px}
.gate-k span{font:600 .8rem var(--font-mono);width:26px;height:26px;border-radius:50%;display:grid;place-items:center;background:var(--purple);color:var(--bg-deep);flex:none}
.gate-flag .gate-k span{background:var(--green)}
.gate ul{margin:0;padding-left:18px;display:flex;flex-direction:column;gap:6px}
.gate li::marker{color:var(--comment)}
.gate-l{font:600 .7rem var(--font-mono);letter-spacing:.09em;text-transform:uppercase;margin-top:4px}
.gate-block{color:var(--red)} .gate-rec{color:var(--yellow)}
.gate-n{margin-top:auto;padding-top:6px;font-size:.84rem;color:var(--muted)}
.gates-extra{display:flex;flex-direction:column;gap:8px;margin-top:16px}
.gx{display:grid;grid-template-columns:minmax(0,230px) minmax(0,1fr);gap:16px;border:1px dashed var(--line-strong);border-radius:10px;padding:12px 16px;font-size:.92rem}
.gx-k{font-weight:600;color:var(--fg)}

/* temas */
.themes{display:grid;grid-template-columns:repeat(auto-fill,minmax(270px,1fr));gap:14px}
.theme{background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:14px 8px 8px}
.theme h3{font:600 .72rem var(--font-mono);letter-spacing:.1em;text-transform:uppercase;color:var(--purple);margin:0 10px 8px}
.theme ul{list-style:none;margin:0;padding:0}
.theme a{display:flex;gap:10px;align-items:baseline;padding:6px 10px;border-radius:7px;color:var(--text);font-size:.9rem;line-height:1.35}
.theme a:hover{background:var(--surface-2);text-decoration:none;color:var(--fg)}
.th-n{font:500 .78rem var(--font-mono);color:var(--purple);text-align:right;min-width:22px;flex:none}
.th-t{flex:1;min-width:0}
.theme .dots{align-self:center}

/* filtro */
.docs{margin-top:84px;padding-top:6px;border-top:1px solid var(--line-strong)}
.filter{position:sticky;top:env(safe-area-inset-top,0px);z-index:5;display:flex;flex-wrap:wrap;gap:10px 12px;align-items:center;padding:12px 0;margin:10px 0 20px;background:rgba(33,34,44,.94);backdrop-filter:blur(8px);border-bottom:1px solid var(--line)}
.filter input{flex:1 1 220px;min-width:0;font:400 .92rem var(--font-text);color:var(--fg);background:var(--bg-deep);border:1px solid var(--line-strong);border-radius:8px;padding:8px 12px}
.filter input::placeholder{color:var(--comment)}
.filter input:focus{outline:none;border-color:var(--purple)}
.chips{display:flex;flex-wrap:wrap;gap:6px}
.chip{font:500 .76rem var(--font-mono);color:var(--muted);background:transparent;border:1px solid var(--line-strong);border-radius:999px;padding:5px 11px;cursor:pointer;display:inline-flex;gap:7px;align-items:center}
.chip:hover{color:var(--fg);border-color:var(--comment)}
.chip[aria-pressed="true"]{color:var(--fg);background:var(--line-strong);border-color:var(--purple)}
.f-count{font:500 .76rem var(--font-mono);color:var(--muted);margin-left:auto;display:flex;gap:10px;align-items:center}
.f-count button{font:inherit;color:var(--cyan);background:none;border:0;cursor:pointer;padding:0}
.sr{position:absolute;width:1px;height:1px;overflow:hidden;clip-path:inset(50%)}
.empty{border:1px dashed var(--line-strong);border-radius:12px;padding:26px;text-align:center;color:var(--muted);margin-bottom:20px}

/* painéis */
.notes{display:flex;flex-direction:column;gap:24px;margin-top:24px}
.note{background:var(--surface);border:1px solid var(--line);border-radius:14px;padding:26px 30px 30px;scroll-margin-top:82px}
.note:target{border-color:var(--purple)}
.note-h{display:grid;grid-template-columns:auto minmax(0,1fr);gap:16px;align-items:start;padding-bottom:18px;margin-bottom:20px;border-bottom:1px solid var(--line)}
.note-plain .note-h{grid-template-columns:minmax(0,1fr)}
.note-n{font:600 1.02rem var(--font-mono);color:var(--bg-deep);background:var(--purple);min-width:44px;height:44px;padding:0 9px;border-radius:10px;display:grid;place-items:center;white-space:nowrap}
.note-n:hover{text-decoration:none;background:var(--pink)}
.note h2{font-size:1.3rem;line-height:1.3;margin:6px 0 0}
.note-plain h2{margin-top:0}
.note-meta{display:flex;flex-wrap:wrap;gap:6px 8px;align-items:center;margin-top:12px}
.note-meta2{font-size:.8rem;color:var(--muted);gap:6px 18px;margin-top:10px}
.rel{display:inline-flex;flex-wrap:wrap;gap:4px 6px;align-items:center}
.rel-l{margin-right:2px}
.rel .nref{font:500 .76rem var(--font-mono);text-decoration:none;border:1px solid var(--line-strong);border-radius:5px;padding:0 .45em;color:var(--cyan)}
.rel .nref:hover{border-color:var(--cyan);background:rgba(139,233,253,.08)}
.guide-link{color:var(--purple)}
.guide-link::before{content:"◫ ";font-family:var(--font-mono)}
.note-b{display:flex;flex-direction:column;gap:16px}
.lead{color:var(--muted);font-size:.96rem}
.sub{margin:14px 0 0;line-height:1.3;scroll-margin-top:82px}
.sub-3{font-size:1.12rem;padding-top:16px;border-top:1px solid var(--line)}
.note-b>.sub-3:first-child{padding-top:0;border-top:0;margin-top:0}
.sub-4{font-size:1rem} .sub-5{font-size:.92rem;color:var(--muted)}
.rule{border:0;border-top:1px solid var(--line);margin:6px 0;width:100%}
.quote{margin:0;padding:4px 0 4px 18px;border-left:3px solid var(--line-strong);color:var(--muted);display:flex;flex-direction:column;gap:10px}
.blocks{display:flex;flex-direction:column;gap:22px}
.blk-b{display:flex;flex-direction:column;gap:10px;min-width:0}
.blk-h{display:flex;gap:8px;align-items:baseline;font-weight:600;color:var(--fg);margin-bottom:8px;font-size:1rem;line-height:1.4}
.blk-h.up{font:600 .71rem/1.4 var(--font-mono);letter-spacing:.11em;text-transform:uppercase;color:var(--muted)}
.blk-h code{text-transform:none;letter-spacing:0}
.blk-i{font:600 .86rem var(--font-mono);flex:none}
.blk-destaque .blk-b{color:var(--fg)}
.blk-discreto>.blk-h.up{color:var(--purple)}
.blk-call{border:1px solid color-mix(in srgb,var(--c) 36%,transparent);background:color-mix(in srgb,var(--c) 7%,transparent);border-radius:10px;padding:14px 16px 16px}
.blk-call>.blk-h{color:var(--c)}
.blk-call>.blk-h:has(span:empty){display:none}
.blk-aberto{border-style:dashed;background:transparent;border-color:color-mix(in srgb,var(--c) 55%,transparent)}
.items{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:14px}
.items>li{position:relative;padding-left:20px;display:flex;flex-direction:column;gap:8px;min-width:0}
.items>li::before{content:"";position:absolute;left:3px;top:.68em;width:6px;height:6px;border-radius:2px;background:var(--comment)}
.items .items{gap:10px}
.items .items>li::before{background:transparent;border-radius:50%;box-shadow:inset 0 0 0 1.5px var(--comment)}
.items>li.li-call{padding-left:0}
.items>li.li-call::before,.items>li.task::before{display:none}
.items>li.task{padding-left:26px}
.tk-box{position:absolute;left:0;top:-.08em;font-size:1.05rem;color:var(--comment)}
.task.done>.tk-box{color:var(--green)}
.blk-fazer .items>li:not(.task)::before{content:"✓";background:none;box-shadow:none;width:auto;height:auto;left:1px;top:.05em;color:var(--purple);font:600 .82rem/1.9 var(--font-mono)}
.nums{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:12px}
.nums>li{display:grid;grid-template-columns:2.1em minmax(0,1fr);gap:6px}
.num{font:600 .86em/1.95 var(--font-mono);color:var(--purple);text-align:right;padding-right:4px}
.num-b{display:flex;flex-direction:column;gap:8px;min-width:0}
.enum{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:8px}
.enum>li{display:grid;grid-template-columns:2em minmax(0,1fr);gap:6px}
.mk{font:600 .84em/1.95 var(--font-mono);color:var(--purple)}
.blk-pergunta .mk,.card .mk{color:var(--pink)}

/* tabelas e blocos de código */
.tbl{overflow-x:auto;border:1px solid var(--line);border-radius:10px;background:var(--surface)}
table{border-collapse:collapse;width:100%;min-width:520px;font-size:.9rem}
th{font:600 .7rem var(--font-mono);letter-spacing:.07em;text-transform:uppercase;color:var(--muted);background:var(--bg);text-align:left;padding:10px 14px;white-space:nowrap}
th code{text-transform:none;letter-spacing:0;font-size:1.05em}
td{padding:10px 14px;border-top:1px solid var(--line);vertical-align:top}
td.nowrap{white-space:nowrap}
td code,th code{white-space:nowrap}
.tbl-num td,.tbl-num th{text-align:center;font-variant-numeric:tabular-nums}
.tbl-num td:first-child,.tbl-num th:first-child{text-align:left}
.code{margin:0;border:1px solid var(--line);border-radius:10px;overflow:hidden;background:var(--bg-deep)}
.code figcaption{display:flex;justify-content:space-between;align-items:center;padding:6px 8px 6px 14px;border-bottom:1px solid var(--line);font:600 .68rem var(--font-mono);letter-spacing:.1em;text-transform:uppercase;color:var(--comment)}
.copy{font:500 .7rem var(--font-mono);color:var(--muted);background:transparent;border:1px solid var(--line-strong);border-radius:6px;padding:3px 10px;cursor:pointer}
.copy:hover{color:var(--fg);border-color:var(--comment)}
.code pre{margin:0;padding:14px 16px;overflow-x:auto;font:400 .84rem/1.65 var(--font-mono);color:var(--fg)}
.code pre code{font:inherit;background:none;padding:0;border-radius:0;white-space:pre;overflow-wrap:normal}
.j-k{color:var(--cyan)} .j-s{color:var(--yellow)} .j-n,.j-c{color:var(--purple)} .j-x{color:var(--comment)}

/* cartões numerados */
.cards{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:14px}
.card{background:var(--surface-2);border:1px solid var(--line);border-radius:12px;padding:16px 18px 18px;scroll-margin-top:82px}
.card:target{border-color:var(--pink)}
.card-h{display:grid;grid-template-columns:auto minmax(0,1fr);gap:14px;align-items:start}
.card-n{font:600 .9rem var(--font-mono);color:var(--pink);border:1px solid rgba(255,121,198,.5);border-radius:8px;min-width:34px;height:34px;display:grid;place-items:center}
.card-t{font-size:1.02rem;line-height:1.45;margin:3px 0 0}
.card-t .pid{margin-right:4px;font-size:.78em;vertical-align:.1em}
.card-b{margin-top:12px;padding-left:48px;display:flex;flex-direction:column;gap:10px}

.foot{margin-top:72px;padding-top:22px;border-top:1px solid var(--line);color:var(--muted);font-size:.86rem}

@media (max-width:1100px){
  .gates{grid-template-columns:1fr;gap:14px}
  .gate:not(:last-child)::after{content:"↓";right:auto;left:22px;top:auto;bottom:-17px}
}
@media (max-width:960px){
  .shell{display:block}
  .topbar{display:flex;position:sticky;top:env(safe-area-inset-top,0px);z-index:20;gap:12px;align-items:center;height:50px;background:var(--bg-deep);border-bottom:1px solid var(--line);padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px))}
  .topbar button{font:600 .8rem var(--font-mono);color:var(--fg);background:var(--surface);border:1px solid var(--line-strong);border-radius:8px;padding:6px 12px;cursor:pointer}
  .topbar span{color:var(--muted);font-size:.86rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  .side{position:fixed;inset:0 auto 0 0;width:min(86vw,330px);z-index:40;transform:translateX(-102%);padding-top:calc(22px + env(safe-area-inset-top,0px));padding-left:max(12px,env(safe-area-inset-left,0px))}
  .nav-ready .side{transition:transform .2s ease}
  .nav-open .side{transform:none}
  .nav-open .scrim{display:block;position:fixed;inset:0;z-index:30;background:rgba(0,0,0,.55)}
  .main{padding-block:28px 72px}
  .filter{position:static}
  .f-count{margin-left:0}
  .note,.card,.sub,.sec{scroll-margin-top:62px}
}
@media (max-width:640px){
  body{font-size:15.5px}
  .note{padding:20px 16px 22px;border-radius:12px}
  .note-h{gap:12px}
  .note-n{min-width:38px;height:38px;font-size:.92rem}
  .note h2{font-size:1.14rem;margin-top:4px}
  .journey>li{grid-template-columns:40px minmax(0,1fr)}
  .jr-notes{grid-column:2;text-align:left;padding-top:0}
  .ld-row{grid-template-columns:26px minmax(0,1fr);gap:8px 12px}
  .ld-a{display:none}
  .ld-then{grid-column:2}
  .gx{grid-template-columns:1fr;gap:4px}
  .timeline li{grid-template-columns:1fr;gap:2px}
  .card-b{padding-left:0}
  .half-row{grid-template-columns:auto minmax(0,1fr)}
  .half-v{grid-column:2;justify-self:start}
  .fig-scroll{padding:16px}
}
@media (prefers-reduced-motion:reduce){html{scroll-behavior:auto}.nav-ready .side{transition:none}}
"""

JS = r"""
(function(){
  function $(s,r){return (r||document).querySelector(s)}
  function $$(s,r){return Array.prototype.slice.call((r||document).querySelectorAll(s))}
  var notes=$$('.note'), links={}, side=$('#side'), menu=$('#menu');
  $$('.side a[data-k]').forEach(function(a){links[a.dataset.k]=a});
  var q=$('#q'), count=$('#count'), clear=$('#clear'), empty=$('#empty');
  var state={q:'',st:{},gate:false};
  function norm(s){return s.normalize('NFD').replace(/[̀-ͯ]/g,'').toLowerCase()}
  var texts=notes.map(function(n){return norm(n.textContent)});
  function sts(){return Object.keys(state.st).filter(function(k){return state.st[k]})}
  function apply(){
    if(!count) return;
    var shown=0, on=sts();
    notes.forEach(function(n,i){
      var has=n.dataset.st.split(' ');
      var ok=(!state.q||texts[i].indexOf(state.q)>-1)
        &&(!on.length||on.some(function(s){return has.indexOf(s)>-1}))
        &&(!state.gate||n.dataset.gate==='1');
      n.hidden=!ok; if(links[n.dataset.k]) links[n.dataset.k].hidden=!ok; if(ok) shown++;
    });
    count.textContent=shown+' '+count.dataset.de+' '+notes.length+' '+count.dataset.nome;
    clear.hidden=!(state.q||state.gate||on.length);
    empty.hidden=shown>0;
  }
  function reset(){
    if(!q) return;
    state.q='';state.st={};state.gate=false;q.value='';
    $$('.chip').forEach(function(c){c.setAttribute('aria-pressed','false')});
    apply();
  }
  if(q){
    q.addEventListener('input',function(){state.q=norm(q.value.trim());apply()});
    $$('.chip').forEach(function(c){c.addEventListener('click',function(){
      var on=c.getAttribute('aria-pressed')!=='true';
      c.setAttribute('aria-pressed',on?'true':'false');
      if(c.dataset.st) state.st[c.dataset.st]=on; else state.gate=on;
      apply();
    })});
    clear.addEventListener('click',reset);
    $('#empty-clear').addEventListener('click',reset);
  }

  function setMenu(o){document.body.classList.add('nav-ready');document.body.classList.toggle('nav-open',o); if(menu) menu.setAttribute('aria-expanded',o?'true':'false')}
  if(menu) menu.addEventListener('click',function(){setMenu(!document.body.classList.contains('nav-open'))});
  $('#scrim').addEventListener('click',function(){setMenu(false)});
  document.addEventListener('keydown',function(e){if(e.key==='Escape') setMenu(false)});

  // um link para uma secção escondida pelo filtro limpa o filtro primeiro
  function reveal(hash){
    if(!hash||hash.length<2) return;
    var t=null; try{t=document.getElementById(decodeURIComponent(hash.slice(1)))}catch(e){}
    var n=t&&t.closest('.note'); if(n&&n.hidden) reset();
  }
  document.addEventListener('click',function(e){
    var a=e.target.closest&&e.target.closest('a[href^="#"]'); if(!a) return;
    reveal(a.getAttribute('href')); if(document.body.classList.contains('nav-open')) setMenu(false);
  });
  window.addEventListener('hashchange',function(){reveal(location.hash)});

  $$('.code .copy').forEach(function(b){b.addEventListener('click',function(){
    var pre=b.closest('.code').querySelector('pre');
    function back(){setTimeout(function(){b.textContent='%%COPIAR%%'},1400)}
    function done(){b.textContent='%%COPIADO%%';back()}
    function select(){var r=document.createRange();r.selectNodeContents(pre);var s=getSelection();s.removeAllRanges();s.addRange(r);b.textContent='%%SELECIONADO%%';back()}
    if(navigator.clipboard&&navigator.clipboard.writeText) navigator.clipboard.writeText(pre.textContent).then(done,select); else select();
  })});

  // secção atual na barra lateral
  var navs={}, cur=null;
  $$('.side a[href^="#"]').forEach(function(a){navs[a.getAttribute('href').slice(1)]=a});
  function keep(a){
    var top=a.offsetTop, bot=top+a.offsetHeight;
    if(top<side.scrollTop+70) side.scrollTop=top-70;
    else if(bot>side.scrollTop+side.clientHeight-24) side.scrollTop=bot-side.clientHeight+24;
  }
  if('IntersectionObserver' in window){
    var io=new IntersectionObserver(function(es){es.forEach(function(e){
      if(!e.isIntersecting) return; var a=navs[e.target.id]; if(!a) return;
      if(cur) cur.classList.remove('on'); cur=a; a.classList.add('on'); keep(a);
    })},{rootMargin:'-12% 0px -78% 0px'});
    $$('.sec[id], .note[id]').forEach(function(s){io.observe(s)});
  }
  apply();
})();
"""

PAGINA = """<!doctype html>
<html lang="%%LANG%%">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>%%ABA%%</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap">
<style>%%CSS%%</style>
</head>
<body>
<div class="topbar"><button id="menu" type="button" aria-expanded="false" aria-controls="side">%%INDICE%%</button><span>%%TITULO_TXT%%</span></div>
<div class="scrim" id="scrim"></div>
<div class="shell">
<nav class="side" id="side" aria-label="%%INDICE%%">
  <div class="side-brand"><b>%%MARCA%%</b><span>%%SOBRE%%</span></div>
  %%NAV%%
</nav>
<main class="main"><div class="col">

<header class="hero">
  %%VOLTAR%%
  %%EYEBROW%%
  <h1>%%TITULO%%</h1>
  <p class="facts">%%FACTOS%%</p>
</header>

%%INTRO%%

%%GUIA%%

<div class="docs">
  %%FILTRO%%
  <div class="notes">%%PAINEIS%%</div>
</div>

<footer class="foot">%%RODAPE%%</footer>
</div></main>
</div>
<script>%%JS%%</script>
</body>
</html>
"""

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
