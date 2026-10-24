"""Team memory: 'what did we learn about X?', answered only from the graph, with citations and paths."""
import re

from . import llm, web
from . import graph as G
from .ingest import norm_pkg

STOPWORDS = set(
    "a an and are about at be by did do does for from how i in is it of on or our the this to us we what when "
    "which who why with you learn learned learnt team anything know say said tell".split()
)

ANSWER_PROMPT = """You answer a team's question using ONLY the numbered context items, which are notes teammates took
at a conference plus the sources those notes cite. Cite items inline like [N2] or [S1]. Name the teammate who
captured each point. If the context doesn't answer the question, say exactly: "Nobody on the team captured anything
about this yet." Keep it under 120 words."""


def keywords(question: str) -> list[str]:
    words = re.findall(r"[a-zA-Z0-9@/.+#-]{2,}", question.lower())
    return [w.strip(".") for w in words if w.strip(".") not in STOPWORDS][:8]


def _fulltext(label: str, terms: list[str]) -> list:
    if not terms:
        return []
    query = "|".join(re.sub(r"[^a-z0-9]", "", t) for t in terms if re.sub(r"[^a-z0-9]", "", t))
    try:
        return G.rows(
            f"CALL db.idx.fulltext.queryNodes('{label}', $q) YIELD node RETURN node LIMIT 20", {"q": query}
        )
    except Exception:
        return []


def source_context(sid: str, url: str, title: str, summary: str, fetched_at: str) -> str:
    """One cited source for the model. Title and summary come from a fetched web page, so they're wrapped as
    untrusted; the URL and fetch time are ours."""
    return f"[{sid}] ({url}, fetched {fetched_at}) " + web.wrap_untrusted(f"{title}\n{summary}", limit=2000)


def find_notes(question: str) -> list[str]:
    terms = keywords(question)
    nids: list[str] = []
    for (node,) in _fulltext("Note", terms):
        nids.append(node.properties["nid"])
    # Notes linked to a package/topic named in the question, or notes about matching sessions/sources.
    names = list({norm_pkg(t) for t in terms} | set(terms))
    for cypher in (
        "MATCH (n:Note)-[:MENTIONS]->(k:Package) WHERE k.name IN $names RETURN n.nid",
        "MATCH (n:Note)-[:ABOUT_TOPIC]->(t:Topic) WHERE t.name IN $names RETURN n.nid",
    ):
        nids += [r[0] for r in G.rows(cypher, {"names": names})]
    for (node,) in _fulltext("Session", terms):
        nids += [r[0] for r in G.rows(
            "MATCH (n:Note)-[:ABOUT]->(s:Session {sid: $sid}) RETURN n.nid", {"sid": node.properties["sid"]}
        )]
    for (node,) in _fulltext("Source", terms):
        nids += [r[0] for r in G.rows(
            "MATCH (n:Note)-[:CITES]->(s:Source {url: $url}) RETURN n.nid", {"url": node.properties["url"]}
        )]
    if not nids:  # fall back to substring match
        for term in terms:
            nids += [r[0] for r in G.rows(
                "MATCH (n:Note) WHERE toLower(n.text) CONTAINS $t RETURN n.nid LIMIT 10", {"t": term}
            )]
    return list(dict.fromkeys(nids))[:8]


def ask_team(question: str) -> dict:
    nids = find_notes(question)
    context, citations, paths = [], [], []
    source_ids: dict[str, str] = {}
    for i, nid in enumerate(nids, 1):
        row = G.rows(
            "MATCH (p:Person)-[:WROTE]->(n:Note {nid: $nid}) "
            "OPTIONAL MATCH (n)-[:ABOUT]->(s:Session) "
            "RETURN p.handle, n.text, s.title, n.created_at",
            {"nid": nid},
        )
        if not row:
            continue
        handle, text, session, at = row[0]
        context.append(f"[N{i}] {handle} wrote during '{session or 'the conference'}': <user_note>{text}</user_note>")
        citations.append({"id": f"N{i}", "by": handle, "session": session, "note": text, "at": at})
        for (path,) in G.rows(
            "MATCH path = (p:Person)-[:WROTE]->(n:Note {nid: $nid})-[:ABOUT]->(:Session) RETURN path", {"nid": nid}
        ) + G.rows(
            "MATCH path = (n:Note {nid: $nid})-[:CITES]->(:Source) RETURN path", {"nid": nid}
        ):
            paths.append(G.path_json(path))
        for url, title, summary, fetched_at in G.rows(
            "MATCH (n:Note {nid: $nid})-[:CITES]->(src:Source) RETURN src.url, src.title, src.summary, src.fetched_at",
            {"nid": nid},
        ):
            if url in source_ids or not summary:
                continue
            sid = f"S{len(source_ids) + 1}"
            source_ids[url] = sid
            context.append(source_context(sid, url, title, summary, fetched_at))
            citations.append({"id": sid, "url": url, "title": title, "fetched_at": fetched_at})

    G.highlight(f"Team memory: {question}", paths)
    if not context:
        return {"answer": "Nobody on the team captured anything about this yet.", "citations": [], "paths": []}
    answer = llm.text_call(ANSWER_PROMPT, f"Question: {question}\n\nContext:\n" + "\n".join(context))
    return {"answer": answer, "citations": citations, "paths": [p["text"] for p in paths]}
