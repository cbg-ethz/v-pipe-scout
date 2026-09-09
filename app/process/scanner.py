"""Panel scanner: classify unexplained co-occurrence patterns (Option C).

Given the unexplained patterns from run_cooc_panel_completeness and the full
pango tree, assigns each co-occurrence pattern to the tightest pango node its
fingerprint supports, then categorizes by relationship to the user's panel.

Categories:
  resolved_lineage  — fingerprint matches exactly one pango lineage.
  resolved_clade    — fingerprint matches several lineages forming a tight
                      clade; labelled by their common ancestor.
  unresolved        — fingerprint matches many lineages across unrelated
                      clades (common ancestor too ancient to be meaningful).
  novel             — no pango lineage explains the fingerprint.

Within resolved_* each finding is tagged by panel relationship:
  in_panel     — the assigned node is a panel variant (explained; dropped).
  sublineage   — assigned node descends from a panel variant.
  new_lineage  — assigned node unrelated to the panel.

Co-occurrence requires >= 2 fingerprint mutations by definition (a single
mutation is allele frequency, not a haplotype), so patterns with fewer than
2 mutations beyond the panel are excluded.

Called by the worker Celery task (run_cooc_scanner_lapis) — pure computation.
"""

import logging
import re
from typing import Dict, List, Optional, Set, Tuple

import pandas as pd

logger = logging.getLogger(__name__)

# A clade label is only meaningful if the common ancestor of the candidate
# set is reasonably recent. If the common ancestor is at or above this depth
# threshold from the root it's too broad (e.g. BA.2) -> unresolved.
# Depth is measured as number of parent hops from the node to the tree root.
MIN_CLADE_DEPTH = 6

# Minimum fingerprint size for co-occurrence (2 = haplotype, 1 = allele freq).
MIN_FINGERPRINT = 2


def _sig_explains(present: Set[str], sig: Set[str]) -> bool:
    return bool(present) and present.issubset(sig)


class _Tree:
    """Lightweight pango tree helper built from a parent map."""

    def __init__(self, parent_map: Dict[str, str]):
        self.parent = parent_map
        self.children: Dict[str, List[str]] = {}
        for node, par in parent_map.items():
            if par:
                self.children.setdefault(par, []).append(node)
        self._depth: Dict[str, int] = {}

    def depth(self, node: str) -> int:
        if node in self._depth:
            return self._depth[node]
        d, cur = 0, node
        seen = set()
        while True:
            par = self.parent.get(cur, "")
            if not par or par in seen:
                break
            seen.add(par)
            d += 1
            cur = par
        self._depth[node] = d
        return d

    def ancestors(self, node: str) -> Set[str]:
        a, cur, seen = set(), node, set()
        while cur and cur not in seen:
            a.add(cur)
            seen.add(cur)
            cur = self.parent.get(cur, "")
        return a

    def is_descendant(self, node: str, ancestor: str) -> bool:
        cur, seen = node, set()
        while cur and cur not in seen:
            seen.add(cur)
            cur = self.parent.get(cur, "")
            if cur == ancestor:
                return True
        return False

    def lca(self, nodes: List[str]) -> Optional[str]:
        """Deepest common ancestor of all nodes (may be one of the nodes)."""
        if not nodes:
            return None
        common: Optional[Set[str]] = None
        for n in nodes:
            a = self.ancestors(n)
            common = a if common is None else (common & a)
        if not common:
            return None
        return max(common, key=self.depth)

    def dominant_clade(
        self, nodes: List[str], min_fraction: float = 0.6
    ) -> Optional[str]:
        """Deepest node that is an ancestor of >= min_fraction of `nodes`.

        Unlike strict LCA, this tolerates outliers — recombinants (which have
        no parent chain) and convergent lineages that share the fingerprint
        but sit outside the main clade don't drag the label up to the root.
        Returns the tightest (deepest) clade covering the bulk of candidates.
        """
        if not nodes:
            return None
        # count how many candidates each ancestor covers
        cover: Dict[str, int] = {}
        for n in nodes:
            for anc in self.ancestors(n):
                cover[anc] = cover.get(anc, 0) + 1
        threshold = max(2, int(len(nodes) * min_fraction))
        qualifying = [a for a, c in cover.items() if c >= threshold]
        if not qualifying:
            return None
        return max(qualifying, key=self.depth)


def _assign(
    fingerprint: Set[str],
    all_sigs: Dict[str, Set[str]],
    tree: _Tree,
) -> Tuple[Optional[str], str, List[str]]:
    """Assign a fingerprint to the tightest clade it supports.

    Returns (label_node, kind, candidates).
      kind: 'clade' | 'unresolved' | 'novel'
      label_node: the clade root (clade), else None.
      candidates: all lineages whose signature contains the fingerprint.

    We deliberately do NOT claim a single "exact" lineage. A fingerprint
    matching exactly one lineage is usually a coincidence of which lineages
    happen to carry those muts (e.g. {1722T,1895A} intersecting at PY.1.1),
    not evidence that lineage specifically is present. Co-occurrence resolves
    to clades; which member drives the signal is shown in the drill-down
    discriminating-mutation heatmap, not claimed as a label.
    """
    candidates = [l for l, s in all_sigs.items() if fingerprint.issubset(s)]
    if not candidates:
        return None, "novel", []
    if len(candidates) == 1:
        # single candidate: label it as a clade-of-one at that node, but only
        # if it's deep enough to be meaningful; else unresolved.
        node = candidates[0]
        if tree.depth(node) >= MIN_CLADE_DEPTH:
            return node, "clade", candidates
        return None, "unresolved", candidates

    clade = tree.dominant_clade(candidates)
    if clade is None or tree.depth(clade) < MIN_CLADE_DEPTH:
        return None, "unresolved", candidates
    return clade, "clade", candidates


def _panel_relationship(
    node: str,
    panel_set: Set[str],
    tree: _Tree,
) -> Tuple[str, Optional[str]]:
    """Return (relationship, panel_ancestor).

    relationship: 'in_panel' | 'sublineage' | 'new_lineage'.
    """
    if node in panel_set:
        return "in_panel", node
    for pv in panel_set:
        if tree.is_descendant(node, pv):
            return "sublineage", pv
    return "new_lineage", None


def scan_unexplained_patterns(
    unexplained_patterns: pd.DataFrame,
    panel_variants: List[str],
    all_lineage_signatures: Dict[str, Set[str]],
    panel_parent_map: Dict[str, str],
    min_read_count: int = 2,
    # kept for backwards-compat with the task signature; unused in Option C.
    cowwid_signatures: Optional[Dict[str, Set[str]]] = None,
    truly_private_muts: Optional[Dict[str, Set[str]]] = None,
) -> dict:
    """Classify unexplained co-occurrence patterns (Option C).

    Args:
        unexplained_patterns: DataFrame with columns date, count,
            confirmed_present (list of "{pos}{alt}" per row).
        panel_variants: currently selected panel variant names.
        all_lineage_signatures: {lineage: set of "{pos}{alt}"} for all pango.
        panel_parent_map: {lineage: parent} for the full pango tree.
        min_read_count: minimum reads for a pattern to count.

    Returns dict with keys:
        resolved_lineage:  [{node, relationship, panel_ancestor, total_reads,
                             pattern_count, observed_mutations, designation}]
        resolved_clade:    [{node, relationship, panel_ancestor, member_count,
                             members, total_reads, pattern_count,
                             observed_mutations, designation}]
        unresolved:        [{fingerprint, candidate_count, common_ancestor,
                             total_reads, pattern_count}]
        novel:             {total_reads, pattern_count, top_patterns}
        total_unexplained_reads: int
        summary: str
    """
    panel_set = set(panel_variants)
    tree = _Tree(panel_parent_map)

    panel_union: Set[str] = set()
    for pv in panel_set:
        panel_union |= all_lineage_signatures.get(pv, set())

    patterns = unexplained_patterns
    if patterns is None or patterns.empty:
        return _empty_result()

    # aggregate per assigned clade
    clade_hits: Dict[str, dict] = {}
    unresolved_hits: Dict[frozenset, dict] = {}
    novel_reads = 0
    novel_patterns: List[dict] = []
    total_unexplained = 0

    for _, row in patterns.iterrows():
        present = set(row["confirmed_present"])
        count = int(row["count"])
        if count < min_read_count:
            continue
        total_unexplained += count

        fingerprint = present - panel_union
        if len(fingerprint) < MIN_FINGERPRINT:
            continue  # not co-occurrence beyond panel

        node, kind, candidates = _assign(
            fingerprint, all_lineage_signatures, tree
        )

        if kind == "novel":
            novel_reads += count
            if len(novel_patterns) < 10:
                novel_patterns.append(
                    {"count": count, "date": row.get("date", ""),
                     "mutations": sorted(fingerprint)[:8]}
                )
            continue

        if kind == "unresolved":
            lca = tree.dominant_clade(candidates, min_fraction=0.9) or ""
            key = frozenset(fingerprint)
            slot = unresolved_hits.get(key)
            if slot is None:
                slot = unresolved_hits[key] = {
                    "fingerprint": sorted(fingerprint),
                    "candidate_count": len(candidates),
                    "common_ancestor": lca or "",
                    "total_reads": 0, "pattern_count": 0,
                }
            slot["total_reads"] += count
            slot["pattern_count"] += 1
            continue

        # clade (may still be in_panel -> explained, drop those)
        rel, panel_anc = _panel_relationship(node, panel_set, tree)
        if rel == "in_panel":
            continue

        slot = clade_hits.get(node)
        if slot is None:
            slot = clade_hits[node] = {
                "node": node,
                "relationship": rel,
                "panel_ancestor": panel_anc,
                "total_reads": 0, "pattern_count": 0,
                "observed_mutations": set(),
                "designation": "",
                "candidates": set(),
            }
        slot["total_reads"] += count
        slot["pattern_count"] += 1
        slot["observed_mutations"].update(fingerprint)
        slot["candidates"].update(candidates)

    # ── build output lists ────────────────────────────────────────────────
    resolved_clade = sorted(
        [_finalize_clade(s, tree, all_lineage_signatures) for s in clade_hits.values()],
        key=lambda x: -x["total_reads"],
    )
    unresolved = sorted(
        unresolved_hits.values(), key=lambda x: -x["total_reads"]
    )

    novel = {
        "total_reads": novel_reads,
        "top_patterns": sorted(
            novel_patterns, key=lambda x: -x["count"]
        )[:10],
    }
    novel["pattern_count"] = _count_novel(
        patterns, panel_union, all_lineage_signatures, tree, min_read_count
    )

    summary = _summary(resolved_clade, unresolved, novel)

    result = {
        "resolved_clade": resolved_clade,
        "unresolved": unresolved,
        "novel": novel,
        "total_unexplained_reads": total_unexplained,
        "summary": summary,
    }
    # ── backward-compat shim ──────────────────────────────────────────────
    # Map the new clade-only shape onto the legacy keys the current UI reads,
    # so nothing crashes during the UI transition. Legacy consumers see:
    #   missing_from_panel  <- new-lineage clades (not descended from panel)
    #   emerging_sublineage <- sublineage clades (descend from panel)
    #   possibly_new        <- novel
    result["missing_from_panel"] = [
        {"variant": c["node"], "total_reads": c["total_reads"],
         "pattern_count": c["pattern_count"],
         "observed_mutations": c["observed_mutations"],
         "cluster_key": c["node"]}
        for c in resolved_clade if c["relationship"] == "new_lineage"
    ]
    result["emerging_sublineage"] = [
        {"lineage": c["node"], "parent": c["panel_ancestor"] or "",
         "total_reads": c["total_reads"], "pattern_count": c["pattern_count"],
         "observed_mutations": c["observed_mutations"]}
        for c in resolved_clade if c["relationship"] == "sublineage"
    ]
    result["possibly_new"] = novel
    return result


def _finalize_clade(s: dict, tree: "_Tree", all_sigs: Dict[str, Set[str]]) -> dict:
    """Build the clade finding, including per-member discriminating-mutation
    blocks for the drill-down heatmap.

    members = candidates that are descendants of the clade node, PLUS
    recombinant candidates (no parent chain) that share the clade fingerprint —
    e.g. XFG shares LF.7's spike mutations through recombination, so it's
    consistent with an LF.7-clade signal even though it's not phylogenetically
    under LF.7. These "associated" members matter: XFG is often the dominant
    variant driving the signal.

    For each member we compute its discriminating muts so the UI can show
    which member's block lights up.
    """
    node = s["node"]
    candidates = sorted(s["candidates"])
    # phylogenetic members (descend from the clade node)
    phylo = [c for c in candidates
             if c == node or tree.is_descendant(c, node)]
    # associated members: recombinants (no parent) sharing the fingerprint,
    # e.g. XFG under an LF.7 clade. These are consistent with the signal.
    associated = [c for c in candidates
                  if c not in phylo and not tree.parent.get(c, "")]
    members = phylo + associated
    if not members:
        members = candidates

    # shared muts = intersection of all member sigs (the clade fingerprint)
    member_sigs = {m: all_sigs.get(m, set()) for m in members}
    shared = set.intersection(*member_sigs.values()) if member_sigs else set()

    # discriminating block per member (unique vs other members).
    # prioritise associated recombinants (XFG etc.) — they're the ones the
    # user most needs to see — then the largest phylo members.
    ordered = associated + phylo
    blocks = []
    for m in ordered[:8]:
        others = set().union(*(member_sigs[o] for o in members if o != m)) \
            if len(members) > 1 else set()
        disc = sorted(member_sigs[m] - others)
        if disc:
            blocks.append({"member": m, "discriminating": disc[:6]})

    return {
        "node": node,
        "relationship": s["relationship"],
        "panel_ancestor": s["panel_ancestor"],
        "member_count": len(members),
        "members": (associated + phylo)[:30],  # show recombinants first
        "associated_members": associated[:10],
        "total_reads": s["total_reads"],
        "pattern_count": s["pattern_count"],
        "observed_mutations": sorted(s["observed_mutations"]),
        "shared_mutations": sorted(shared)[:10],
        "member_blocks": blocks,
        "designation": s["designation"],
    }


def _count_novel(patterns, panel_union, all_sigs, tree, min_read_count) -> int:
    n = 0
    all_sig_list = list(all_sigs.values())
    for _, row in patterns.iterrows():
        count = int(row["count"])
        if count < min_read_count:
            continue
        fp = set(row["confirmed_present"]) - panel_union
        if len(fp) < MIN_FINGERPRINT:
            continue
        if not any(fp.issubset(s) for s in all_sig_list):
            n += 1
    return n


def _summary(clade, unresolved, novel) -> str:
    parts = []
    if clade:
        top = clade[0]
        label = f"{top['node']} clade" if top["member_count"] > 1 else top["node"]
        extra = len(clade) - 1
        parts.append(label + (f" + {extra} more" if extra else ""))
    if novel["total_reads"] > 0:
        parts.append(f"{novel['pattern_count']} novel pattern(s)")
    if unresolved:
        parts.append(f"{len(unresolved)} unresolved")
    if not parts:
        return "No co-occurrence signal beyond the panel."
    return "; ".join(parts) + " not explained by panel."


def _empty_result() -> dict:
    return {
        "resolved_clade": [], "unresolved": [],
        "novel": {"total_reads": 0, "pattern_count": 0, "top_patterns": []},
        "total_unexplained_reads": 0,
        "summary": "No unexplained patterns.",
    }