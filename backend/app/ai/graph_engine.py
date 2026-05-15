"""
Money-hop graph: directed transfers and betweenness-based hub risk.

Betweenness centrality (plain English): how often an account lies on the
shortest paths between other accounts — high values often indicate a
coordinator / orchestrator moving funds between many parties.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import networkx as nx


class TransactionGraph:
    def __init__(self) -> None:
        self.graph: nx.DiGraph = nx.DiGraph()

    def add_transaction(self, sender: str, receiver: str, amount: float, timestamp: str) -> None:
        for node in (sender, receiver):
            if not self.graph.has_node(node):
                self.graph.add_node(node)
        if self.graph.has_edge(sender, receiver):
            data = self.graph[sender][receiver];
            data["transfer_count"] = int(data.get("transfer_count", 1)) + 1
            data["total_amount"] = float(data.get("total_amount", 0.0)) + float(amount)
            data["last_timestamp"] = timestamp
        else:
            self.graph.add_edge(
                sender,
                receiver,
                amount=float(amount),
                total_amount=float(amount),
                transfer_count=1,
                last_timestamp=timestamp,
            )

    def get_risk_score(self, account: str) -> float:
        if not self.graph.has_node(account) or self.graph.number_of_nodes() < 2:
            return 0.0
        centrality = nx.betweenness_centrality(self.graph, normalized=True)
        return float(centrality.get(account, 0.0))

    def get_connected_accounts(self, account: str) -> list[dict[str, Any]]:
        if not self.graph.has_node(account):
            return []
        out: list[dict[str, Any]] = []
        for _, target, data in self.graph.out_edges(account, data=True):
            out.append(
                {
                    "account": target,
                    "direction": "sent",
                    "total_amount": float(data.get("total_amount", data.get("amount", 0.0))),
                }
            )
        for source, _, data in self.graph.in_edges(account, data=True):
            out.append(
                {
                    "account": source,
                    "direction": "received",
                    "total_amount": float(data.get("total_amount", data.get("amount", 0.0))),
                }
            )
        return out

    def find_hub_account(self, flagged_accounts: list[str]) -> tuple[str | None, float]:
        if not flagged_accounts:
            return None, 0.0
        centrality = nx.betweenness_centrality(self.graph, normalized=True)
        best_acc: str | None = None
        best_score = 0.0
        for acc in flagged_accounts:
            if acc not in centrality:
                continue
            s = float(centrality[acc])
            if s > best_score:
                best_score = s
                best_acc = acc
        return best_acc, best_score

    def get_graph_data(self, account: str) -> dict[str, Any]:
        """Nodes/edges JSON for dashboard; ego subgraph around account."""
        if not self.graph.has_node(account):
            return {"nodes": [], "edges": [], "focus": account}

        centrality = nx.betweenness_centrality(self.graph, normalized=True) if self.graph.number_of_nodes() else {}
        nodes_set: set[str] = {account}
        for n in self.graph.successors(account):
            nodes_set.add(n)
        for n in self.graph.predecessors(account):
            nodes_set.add(n)

        nodes: list[dict[str, Any]] = []
        for n in nodes_set:
            nodes.append(
                {
                    "id": n,
                    "centrality": float(centrality.get(n, 0.0)),
                    "label": n[-10:] if len(n) > 10 else n,
                }
            )

        edges: list[dict[str, Any]] = []
        for u, v, data in self.graph.edges(data=True):
            if u in nodes_set and v in nodes_set:
                edges.append(
                    {
                        "source": u,
                        "target": v,
                        "amount": float(data.get("total_amount", data.get("amount", 0.0))),
                        "transfer_count": int(data.get("transfer_count", 1)),
                    }
                )

        return {"nodes": nodes, "edges": edges, "focus": account}

    def clear_old_edges(self, hours: int = 24) -> None:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        to_remove: list[tuple[str, str]] = []
        for u, v, data in self.graph.edges(data=True):
            ts = data.get("last_timestamp")
            if not ts:
                continue
            try:
                if "T" in str(ts):
                    t = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
                else:
                    t = datetime.fromisoformat(str(ts))
                if t.tzinfo is None:
                    t = t.replace(tzinfo=timezone.utc)
                if t < cutoff:
                    to_remove.append((u, v))
            except Exception:
                continue
        self.graph.remove_edges_from(to_remove)
        isolates = list(nx.isolates(self.graph))
        self.graph.remove_nodes_from(isolates)


transaction_graph = TransactionGraph()
