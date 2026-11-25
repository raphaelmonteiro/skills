#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
html2md.py: HTML de documento -> Markdown, para quando não existe uma fonte em Markdown.

    python3 html2md.py DOC.html SAIDA.md

Converte títulos, parágrafos, listas (aninhadas), negrito, itálico, código, blocos <pre>,
links, imagens, tabelas, citações e linhas. Ignora o que é moldura da página e não texto do
documento: <script>, <style>, <nav>, <aside>, <svg>, botões e formulários.

No fim confere que todas as palavras visíveis do HTML estão no Markdown e diz as que faltarem.
Só usa a biblioteca padrão do Python 3.
"""
import re
import sys
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path

VAZIOS = {"br", "hr", "img", "meta", "link", "input", "source", "wbr", "col", "base", "area", "embed", "track"}
IGNORAR = {"script", "style", "nav", "aside", "noscript", "template", "svg", "head", "button", "form", "select", "iframe", "title"}
BLOCO = {"h1", "h2", "h3", "h4", "h5", "h6", "p", "ul", "ol", "pre", "blockquote", "table", "hr", "div", "section",
         "article", "main", "header", "footer", "figure", "figcaption", "details", "summary", "dl", "dt", "dd", "body", "html", "li"}


class No:
    def __init__(self, tag, attrs=None):
        self.tag, self.attrs, self.filhos = tag, dict(attrs or {}), []


class Leitor(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.raiz = No("raiz")
        self.pilha = [self.raiz]

    def handle_starttag(self, tag, attrs):
        no = No(tag, attrs)
        self.pilha[-1].filhos.append(no)
        if tag not in VAZIOS:
            self.pilha.append(no)

    def handle_startendtag(self, tag, attrs):
        self.pilha[-1].filhos.append(No(tag, attrs))

    def handle_endtag(self, tag):
        for i in range(len(self.pilha) - 1, 0, -1):
            if self.pilha[i].tag == tag:
                del self.pilha[i:]
                return

    def handle_data(self, data):
        self.pilha[-1].filhos.append(data)


def texto_cru(no):
    if isinstance(no, str):
        return no
    if no.tag in IGNORAR:
        return ""
    return "".join(texto_cru(f) for f in no.filhos)


def texto_visivel(no):
    """Como texto_cru, mas com um espaço entre elementos (para a conferência não colar células)."""
    if isinstance(no, str):
        return no
    if no.tag in IGNORAR:
        return ""
    return " ".join(texto_visivel(f) for f in no.filhos)


def junta(partes):
    """Junta bocados de texto corrido e arruma os espaços."""
    s = re.sub(r"\s+", " ", "".join(partes))
    return s


def marca(s, m):
    """**texto** com os espaços do lado de fora das marcas."""
    nucleo = s.strip()
    if not nucleo:
        return s
    return (" " if s[:1].isspace() else "") + m + nucleo + m + (" " if s[-1:].isspace() else "")


def corrido(no):
    if isinstance(no, str):
        return re.sub(r"\s+", " ", no)
    t = no.tag
    if t in IGNORAR:
        return ""
    if t == "br":
        return " "
    if t == "img":
        return "![%s](%s)" % (no.attrs.get("alt", ""), no.attrs.get("src", ""))
    if t == "code":
        c = re.sub(r"\s+", " ", texto_cru(no)).strip()
        if not c:
            return ""
        return ("`` %s ``" if "`" in c else "`%s`") % c
    dentro = junta(corrido(f) for f in no.filhos)
    if t in ("strong", "b"):
        return marca(dentro, "**")
    if t in ("em", "i"):
        return marca(dentro, "*")
    if t in ("del", "s", "strike"):
        return marca(dentro, "~~")
    if t == "a":
        href = no.attrs.get("href", "")
        return "[%s](%s)" % (dentro.strip(), href) if href and dentro.strip() else dentro
    return dentro


def e_bloco(no):
    return not isinstance(no, str) and no.tag in BLOCO


def linguagem(no):
    for n in [no] + [f for f in no.filhos if not isinstance(f, str)]:
        m = re.search(r"(?:language|lang)-([\w+#-]+)", n.attrs.get("class", "") or "")
        if m:
            return m.group(1)
    return ""


def celula(no):
    return junta(corrido(f) for f in no.filhos).strip().replace("|", "\\|")


def tabela(no):
    linhas = []

    def anda(n):
        for f in n.filhos:
            if isinstance(f, str):
                continue
            if f.tag == "tr":
                linhas.append([celula(c) for c in f.filhos if not isinstance(c, str) and c.tag in ("th", "td")])
            elif f.tag in ("thead", "tbody", "tfoot"):
                anda(f)
    anda(no)
    linhas = [l for l in linhas if l]
    if not linhas:
        return []
    n = max(len(l) for l in linhas)
    linhas = [l + [""] * (n - len(l)) for l in linhas]
    out = ["| " + " | ".join(linhas[0]) + " |", "|" + "---|" * n]
    out += ["| " + " | ".join(l) + " |" for l in linhas[1:]]
    return out


def blocos(no, out, recuo=""):
    """Escreve em `out` as linhas Markdown dos filhos de `no`."""
    acumulado = []

    def despeja():
        s = junta(acumulado).strip()
        acumulado.clear()
        if s:
            out.extend([recuo + s, ""])

    for f in no.filhos:
        if not e_bloco(f):
            acumulado.append(corrido(f))
            continue
        despeja()
        t = f.tag
        if re.fullmatch(r"h[1-6]", t):
            s = junta(corrido(x) for x in f.filhos).strip()
            if s:
                out.extend([recuo + "#" * int(t[1]) + " " + s, ""])
        elif t == "p" or t in ("figcaption", "summary", "dt", "dd"):
            s = junta(corrido(x) for x in f.filhos).strip()
            if s:
                out.extend([recuo + s, ""])
        elif t in ("ul", "ol"):
            lista(f, out, recuo)
            out.append("")
        elif t == "pre":
            corpo = texto_cru(f).strip("\n")
            out.append(recuo + "```" + linguagem(f))
            out.extend(recuo + l for l in corpo.split("\n"))
            out.extend([recuo + "```", ""])
        elif t == "blockquote":
            dentro = []
            blocos(f, dentro, "")
            while dentro and not dentro[-1]:
                dentro.pop()
            out.extend(recuo + ("> " + l if l else ">") for l in dentro)
            out.append("")
        elif t == "table":
            out.extend(recuo + l for l in tabela(f))
            out.append("")
        elif t == "hr":
            out.extend([recuo + "---", ""])
        else:
            blocos(f, out, recuo)
    despeja()


def lista(no, out, recuo):
    n = int(no.attrs.get("start", 1) or 1) if no.tag == "ol" else 0
    for li in no.filhos:
        if isinstance(li, str) or li.tag != "li":
            continue
        marcador = "%d. " % n if no.tag == "ol" else "- "
        if no.tag == "ol":
            n += 1
        dentro = []
        blocos(li, dentro, "")
        while dentro and not dentro[-1]:
            dentro.pop()
        if not dentro:
            continue
        # linhas vazias entre blocos do mesmo item ficam; a primeira linha leva o marcador
        compactas, anterior_vazia = [], False
        for i, l in enumerate(dentro):
            if not l:
                anterior_vazia = True
                continue
            prox_e_lista = re.match(r"^\s*(?:[-*+] |\d+\. )", l) is not None
            if anterior_vazia and compactas and not prox_e_lista:
                compactas.append("")
            compactas.append(l)
            anterior_vazia = False
        out.append(recuo + marcador + compactas[0])
        pad = recuo + " " * len(marcador)
        out.extend((pad + l) if l else "" for l in compactas[1:])


def palavras(s):
    return re.findall(r"[0-9a-zà-ÿ]+", s.lower())


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    fonte, saida = Path(argv[0]), Path(argv[1])
    leitor = Leitor()
    leitor.feed(fonte.read_text(encoding="utf-8"))
    out = []
    blocos(leitor.raiz, out)
    md = re.sub(r"\n{3,}", "\n\n", "\n".join(out)).strip() + "\n"
    saida.write_text(md, encoding="utf-8")
    falta = Counter(palavras(texto_visivel(leitor.raiz))) - Counter(palavras(re.sub(r"\]\([^)]*\)", "]", md)))
    print("escrito: %s (%d linhas)" % (saida, md.count("\n")))
    if falta:
        print("ATENÇÃO, palavras do HTML que não estão no Markdown: %s" % dict(falta))
        return 1
    print("conferência: OK, todas as palavras visíveis do HTML estão no Markdown")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
