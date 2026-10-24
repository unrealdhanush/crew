"""FalkorDB access, schema, and turning graph paths into explainable JSON."""
import json
import time

from . import config

_graph = None

# (label, property) pairs that get a range index for fast MERGE/lookup.
INDEXES = [
    ("Person", "handle"),
    ("Repo", "full_name"),
    ("Package", "name"),
    ("Topic", "name"),
    ("Session", "sid"),
    ("Speaker", "name"),
    ("Note", "nid"),
    ("Source", "url"),
]
# Full-text indexes power "what did we learn about X?".
FULLTEXT = [
    ("Note", ["text"]),
    ("Session", ["title", "abstract"]),
    ("Source", ["title", "summary"]),
]


def graph():
    global _graph
    if _graph is None:
        from falkordb import FalkorDB  # imported lazily so pure-logic tests don't need it

        db = FalkorDB(host=config.FALKORDB_HOST, port=config.FALKORDB_PORT)
        _graph = db.select_graph(config.GRAPH_NAME)
    return _graph


def q(cypher: str, params: dict | None = None):
    """Read/write query."""
    return graph().query(cypher, params or {})


def ro(cypher: str, params: dict | None = None):
    """Read-only query."""
    return graph().ro_query(cypher, params or {})


def rows(cypher: str, params: dict | None = None, write: bool = False) -> list:
    res = q(cypher, params) if write else ro(cypher, params)
    return res.result_set or []


def init_schema() -> None:
    for label, prop in INDEXES:
        try:
            q(f"CREATE INDEX FOR (n:{label}) ON (n.{prop})")
        except Exception as exc:  # index already exists
            if "already" not in str(exc).lower():
                raise
    for label, props in FULLTEXT:
        fields = ", ".join(f"n.{p}" for p in props)
        try:
            q(f"CREATE FULLTEXT INDEX FOR (n:{label}) ON ({fields})")
        except Exception as exc:  # index already exists
            if "already" not in str(exc).lower():
                raise


def reset() -> None:
    try:
        graph().delete()
    except Exception:
        pass
    global _graph
    _graph = None
    init_schema()


# ---------- explainability: paths -> JSON the UI and the agent can show ----------

NAME_KEYS = ("handle", "title", "full_name", "name", "url")
HIDDEN_PROPS = {"text", "abstract", "summary", "excerpt"}


def display_name(props: dict) -> str:
    for key in NAME_KEYS:
        if props.get(key):
            return str(props[key])[:80]
    if props.get("text"):  # a Note: show what it says, not its id
        text = " ".join(str(props["text"]).split())
        return f'"{text[:40]}…"' if len(text) > 40 else f'"{text}"'
    return str(props.get("nid") or "?")


def node_json(node) -> dict:
    props = dict(node.properties)
    return {
        "id": node.id,
        "label": node.labels[0] if node.labels else "",
        "name": display_name(props),
        "props": {k: v for k, v in props.items() if k not in HIDDEN_PROPS},
    }


def _node_id(x):
    return getattr(x, "id", x)


def edge_json(edge) -> dict:
    return {
        "id": edge.id,
        "src": _node_id(edge.src_node),
        "dst": _node_id(edge.dest_node),
        "type": edge.relation,
        "props": dict(edge.properties or {}),
    }


def path_text(nodes: list[dict], edges: list[dict]) -> str:
    """Readable path, e.g. 'dhanush -OWNS-> acme/api -DEPENDS_ON-> fastmcp <-MENTIONS- MCP in prod'."""
    if not nodes:
        return ""
    parts = [f"{nodes[0]['name']}"]
    for i, edge in enumerate(edges):
        nxt = nodes[i + 1]
        if edge["src"] == nodes[i]["id"]:
            parts.append(f" -{edge['type']}-> {nxt['name']}")
        else:
            parts.append(f" <-{edge['type']}- {nxt['name']}")
    return "".join(parts)


def path_json(path) -> dict:
    nodes = [node_json(n) for n in path.nodes()]
    edges = [edge_json(e) for e in path.edges()]
    return {"nodes": nodes, "edges": edges, "text": path_text(nodes, edges)}


TEAM_SIDE = {"Person", "Repo", "Note"}


def focus(nodes: list[dict], edges: list[dict], pinned: set | None = None) -> tuple[list[dict], list[dict]]:
    """The part of the graph that tells the story: people, repos and notes; the packages and topics that connect the
    team's side to a session (bridges); the sessions those bridges, people or notes reach; and the sources notes cite.
    Dead-end dependencies, one-sided topics, speakers and agenda pages are dropped. `pinned` ids (the current
    highlight) always stay."""
    pinned = pinned or set()
    label = {n["id"]: n["label"] for n in nodes}
    near: dict = {}
    for e in edges:
        near.setdefault(e["src"], set()).add(e["dst"])
        near.setdefault(e["dst"], set()).add(e["src"])

    def sides(node_id):
        return {label.get(other) for other in near.get(node_id, ())}

    team = {n["id"] for n in nodes if n["label"] in TEAM_SIDE}
    bridges = {n["id"] for n in nodes
               if n["label"] in ("Package", "Topic") and sides(n["id"]) & TEAM_SIDE and "Session" in sides(n["id"])}
    sessions = {n["id"] for n in nodes if n["label"] == "Session" and near.get(n["id"], set()) & (team | bridges)}
    notes = {i for i in team if label[i] == "Note"}
    sources = {n["id"] for n in nodes if n["label"] == "Source" and near.get(n["id"], set()) & notes}
    keep = team | bridges | sessions | sources | (pinned & set(label))
    return ([n for n in nodes if n["id"] in keep],
            [e for e in edges if e["src"] in keep and e["dst"] in keep])


def highlight(title: str, paths: list[dict]) -> None:
    """Tell the graph viewer which paths to light up."""
    payload = {"title": title, "paths": paths, "at": time.time()}
    config.HIGHLIGHT_FILE.write_text(json.dumps(payload, default=str))


def read_highlight() -> dict:
    try:
        return json.loads(config.HIGHLIGHT_FILE.read_text())
    except Exception:
        return {"title": "", "paths": [], "at": 0}
