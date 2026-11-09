#!/usr/bin/env python3
"""Relatório semanal do Instagram @crisarcangeli: cálculos determinísticos.

Somente leitura: este script não fala com o Instagram. Ele recebe os JSONs que
a sessão puxou do Windsor.ai (conector `instagram`) e imprime os números que o
relatório usa. Nada aqui é estimado: campo ausente sai como "n/d".

Uso:
  python3 scripts/relatorio_semanal.py --media media.json --conta conta.json \
      [--semana 2026-11-02]

media.json: lista (ou {"data": [...]}) de posts com os campos
  timestamp, media_id, media_permalink, media_type, media_caption,
  media_reach, media_views, media_like_count, media_comments_count,
  media_saved, media_shares, media_reel_avg_watch_time, media_reel_skip_rate
  Puxe de (início da semana anterior - 21 dias) até (fim da semana + 1 dia),
  para o fuso de Brasília e a detecção de repost funcionarem.
conta.json: lista diária com date, reach, views, likes, comments, saves,
  shares, follower_count_1d (e opcionalmente reach_followers,
  reach_non_followers).

--semana: segunda-feira da semana analisada (padrão: a semana passada inteira,
  segunda a domingo, no horário de Brasília).
"""
import argparse
import json
import statistics
import unicodedata
from datetime import date, datetime, timedelta, timezone

BRT = timezone(timedelta(hours=-3))  # Brasília não tem horário de verão desde 2019

# Ordem importa: o primeiro tema que casar vence.
SERIES = [
    ("Produtos (Beauty'in/PUMP, Clínica Arcangeli)",
     ["beautyin", "beauty'in", "beautydrink", "pump®", "#pump", "novo pump",
      "clinica arcangeli", "clínica arcangeli", "calculadora de proteina",
      "quanta proteina"]),
    ("Papo de Tubarões", ["papo de tubar"]),
    ("#FilmesCris", ["#filmescris", "filmescris"]),
    ("Opinião sobre notícias",
     ["noticia", "notícia", "hoje o brasil", "senna", "medalha", "hino nacional",
      "world governments summit", "fda", "foi anunciad", "acaba de"]),
    ("Empreendedorismo",
     ["empreend", "mercado", "lucr", "shark tank", "tendencia", "tendência",
      "lideranc", "lideranç", "negocio", "negócio", "oportunidade", "inovac",
      "inovaç", "inteligencia artificial", "inteligência artificial", "marca"]),
]
# Heurística de primeira passada. A sessão revisa lendo as legendas e corrige
# com --temas temas.json ({"<shortcode>": "<nome exato da série>"}).
OUTROS = "Outros"

KPIS = [("reach", "Alcance (soma diária)"), ("views", "Visualizações"),
        ("likes", "Curtidas"), ("comments", "Comentários"),
        ("saves", "Salvamentos"), ("shares", "Compartilhamentos"),
        ("follower_count_1d", "Novos seguidores")]


def load(path):
    with open(path, encoding="utf-8") as f:
        d = json.load(f)
    return d["data"] if isinstance(d, dict) and "data" in d else d


def norm(s):
    s = unicodedata.normalize("NFKD", (s or "").lower())
    return "".join(c for c in s if not unicodedata.combining(c))


def hook(caption):
    """Primeiro bloco da legenda (até a primeira linha em branco), numa linha só."""
    block = []
    for line in (caption or "").splitlines():
        if line.strip():
            block.append(line.strip())
        elif block:
            break
    text = " ".join(block)
    return (text[:157] + "...") if len(text) > 160 else (text or "(sem legenda)")


def serie(caption):
    c = norm(caption)
    for name, keys in SERIES:
        if any(norm(k) in c for k in keys):
            return name
    return OUTROS


def brt(ts):
    return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S%z").astimezone(BRT)


def num(v):
    return v if isinstance(v, (int, float)) else None


def fmt(v):
    if v is None:
        return "n/d"
    if isinstance(v, float) and not v.is_integer():
        return f"{v:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{int(v):,}".replace(",", ".")


def var(a, b):
    if a is None or b in (None, 0):
        return "n/d"
    return f"{(a - b) / b * 100:+.0f}%".replace(".", ",")


def week_posts(media, start):
    end = start + timedelta(days=7)
    return [m for m in media if start <= brt(m["timestamp"]).date() < end]


def account_week(rows, start):
    days = {(start + timedelta(days=i)).isoformat() for i in range(7)}
    sel = [r for r in rows if r.get("date") in days]
    out = {"dias": len(sel)}
    for k, _ in KPIS + [("reach_followers", ""), ("reach_non_followers", "")]:
        vals = [num(r.get(k)) for r in sel]
        known = [v for v in vals if v is not None]
        out[k] = sum(known) if known else None
        # dia com 0 em seguidores costuma ser dado ainda não fechado pela Meta
        out[k + "_incompleto"] = len(known) < 7 or (
            k == "follower_count_1d" and any(v == 0 for v in known))
    return out


TEMAS = {}


def shortcode(m):
    return (m.get("media_permalink") or "").rstrip("/").split("/")[-1]


def post_metrics(m):
    reach, views = num(m.get("media_reach")), num(m.get("media_views"))
    shares = num(m.get("media_shares"))
    return {
        "link": m.get("media_permalink"), "formato": m.get("media_type"),
        "quando": brt(m["timestamp"]).strftime("%a %d/%m %H:%M"),
        "gancho": hook(m.get("media_caption")),
        "serie": TEMAS.get(shortcode(m)) or serie(m.get("media_caption")),
        "alcance": reach, "views": views,
        "curtidas": num(m.get("media_like_count")),
        "comentarios": num(m.get("media_comments_count")),
        "salvos": num(m.get("media_saved")), "compart": shares,
        "watch_s": (num(m.get("media_reel_avg_watch_time")) or 0) / 1000 or None,
        "skip": num(m.get("media_reel_skip_rate")),
        "compart_por_mil_alcance": (shares / reach * 1000) if reach and shares is not None else None,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--media", required=True)
    ap.add_argument("--conta", required=True)
    ap.add_argument("--semana")
    ap.add_argument("--temas", help="JSON {shortcode: série} para corrigir a heurística")
    a = ap.parse_args()
    if a.temas:
        TEMAS.update(load(a.temas))
        valid = {n for n, _ in SERIES} | {OUTROS}
        bad = {k: v for k, v in TEMAS.items() if v not in valid}
        if bad:
            raise SystemExit(f"séries inválidas em --temas: {bad}; use uma de {sorted(valid)}")

    if a.semana:
        start = date.fromisoformat(a.semana)
    else:
        today = datetime.now(BRT).date()
        start = today - timedelta(days=today.weekday() + 7)
    prev = start - timedelta(days=7)

    media = sorted(load(a.media), key=lambda m: m["timestamp"])
    conta = load(a.conta)

    # Repost: mesmo gancho já publicado antes no histórico puxado.
    seen = {}
    for m in media:
        h = norm(hook(m.get("media_caption")))[:60]
        m["_repost"] = h in seen
        seen[h] = True

    cur_posts, prev_posts = week_posts(media, start), week_posts(media, prev)
    ca, pa = account_week(conta, start), account_week(conta, prev)

    print(f"SEMANA {start:%d/%m}–{start + timedelta(days=6):%d/%m/%Y} (seg–dom, Brasília)"
          f"  vs  {prev:%d/%m}–{prev + timedelta(days=6):%d/%m}")
    print()
    print("NÚMEROS DA CONTA (insights diários da Meta)")
    print(f"{'métrica':28} {'semana':>12} {'anterior':>12} {'var':>6}")
    print(f"{'Posts publicados':28} {len(cur_posts):>12} {len(prev_posts):>12} "
          f"{var(len(cur_posts), len(prev_posts)):>6}")
    reposts_c = sum(m["_repost"] for m in cur_posts)
    reposts_p = sum(m["_repost"] for m in prev_posts)
    print(f"{'  dos quais repost':28} {reposts_c:>12} {reposts_p:>12}")
    for k, label in KPIS:
        flag = " *" if ca[k + "_incompleto"] else ""
        print(f"{label:28} {fmt(ca[k]):>12} {fmt(pa[k]):>12} {var(ca[k], pa[k]):>6}{flag}")
    if ca.get("reach_non_followers") is not None:
        print(f"{'Alcance de não seguidores':28} {fmt(ca['reach_non_followers']):>12} "
              f"{fmt(pa['reach_non_followers']):>12} {var(ca['reach_non_followers'], pa['reach_non_followers']):>6}")
    print("* dado incompleto: algum dia sem valor ou com 0 (a Meta ainda não fechou o dia).")
    print("Alcance = soma do alcance diário; a mesma pessoa pode contar em mais de um dia.")
    print()

    rows = [post_metrics(m) | {"repost": m["_repost"]} for m in cur_posts]
    by_views = sorted(rows, key=lambda r: r["views"] or 0, reverse=True)
    views_all = [r["views"] for r in rows if r["views"] is not None]
    med = statistics.median(views_all) if views_all else None
    print(f"MEDIANA DE VIEWS POR POST NA SEMANA: {fmt(med)}")
    print()

    def show(title, lst):
        print(title)
        for r in lst:
            mult = f"{r['views'] / med:.1f}x" if med and r["views"] is not None else "n/d"
            print(f"- {r['link']}  [{r['formato']}] {r['quando']}  série: {r['serie']}"
                  f"{'  (REPOST)' if r['repost'] else ''}")
            print(f"  gancho: {r['gancho']}")
            print(f"  views {fmt(r['views'])} ({mult} a mediana) · alcance {fmt(r['alcance'])} · "
                  f"curtidas {fmt(r['curtidas'])} · coment. {fmt(r['comentarios'])} · "
                  f"salvos {fmt(r['salvos'])} · compart. {fmt(r['compart'])} · "
                  f"watch {fmt(r['watch_s'])}s · skip 3s {fmt(r['skip'] * 100 if r['skip'] is not None else None)}%")
        print()

    show("TOP 3 (por visualizações)", by_views[:3])
    show("PIORES 3 (por visualizações)", by_views[-3:][::-1])
    ineditos = [r for r in by_views if not r["repost"]]
    show("PIORES 3 ENTRE CONTEÚDOS INÉDITOS", ineditos[-3:][::-1])

    print("POR SÉRIE/TEMA (posts da semana)")
    print(f"{'série':46} {'posts':>5} {'views':>10} {'méd/post':>10} {'curtidas':>9} "
          f"{'coment':>7} {'salvos':>7} {'compart':>8}")
    names = [n for n, _ in SERIES] + [OUTROS]
    prev_rows = [post_metrics(m) for m in prev_posts]
    for n in names:
        g = [r for r in rows if r["serie"] == n]
        gp = [r for r in prev_rows if r["serie"] == n]
        s = lambda lst, k: sum(r[k] or 0 for r in lst)
        if not g and not gp:
            print(f"{n:46} {0:>5}  (sem posts nas duas semanas)")
            continue
        mv = s(g, "views") / len(g) if g else None
        mvp = s(gp, "views") / len(gp) if gp else None
        print(f"{n:46} {len(g):>5} {fmt(s(g, 'views')):>10} {fmt(mv):>10} "
              f"{fmt(s(g, 'curtidas')):>9} {fmt(s(g, 'comentarios')):>7} "
              f"{fmt(s(g, 'salvos')):>7} {fmt(s(g, 'compart')):>8}   "
              f"(sem. ant.: {len(gp)} posts, méd/post {fmt(mvp)})")
    print()
    print("TODOS OS POSTS DA SEMANA")
    for r in by_views:
        print(f"{fmt(r['views']):>9} views  {fmt(r['alcance']):>8} alc  {fmt(r['curtidas']):>7} curt  "
              f"{fmt(r['compart']):>6} comp  {r['serie'][:14]:14} {'R' if r['repost'] else ' '} "
              f"{r['link']}  {r['gancho'][:70]}")


if __name__ == "__main__":
    main()
