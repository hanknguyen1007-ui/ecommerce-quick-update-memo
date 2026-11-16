"""Shared adapter contract (decision 1/2 of CHARTER v4).

INPUT adapters turn pasted text into normalized rows: {brand: {channel: {plan, ptd, actual, last, line, x}}}
plus an `extra` dict of adapter-specific metadata (cmp_label, suggest, platform, ...) and a `caps` dict of
capability flags (has_comparison, has_da, has_channels, has_platforms). They never compute metrics -- that is
facts.py's job (one layer, one direction: INPUT -> FACTS -> SURFACES).

Column resolution is synonym-based: each logical field maps to a LIST of regex patterns (so a renamed/
reordered column header still resolves -- G3). If a field's patterns match more than one header cell, that is
an unresolvable ambiguity: adapters must refuse (raise Refuse), never guess which column is right (decision 2).
"""
import re

from core import tsv as T


class Refuse(Exception):
    """Raised by an adapter when it cannot safely parse the input: ambiguous header mapping, mismatched
    run-rate across platform blocks, or an unrecognized layout. Carries a human-readable Vietnamese reason
    plus optional structured detail for the UI."""

    def __init__(self, reason: str, detail=None):
        super().__init__(reason)
        self.reason = reason
        self.detail = detail or {}


class ColumnMatch:
    __slots__ = ("field", "index", "header_text", "candidates")

    def __init__(self, field, index, header_text, candidates):
        self.field = field
        self.index = index            # resolved column index, or None if missing
        self.header_text = header_text  # the header cell text at `index` (None if missing)
        self.candidates = candidates  # all header texts that matched this field's synonyms (len > 1 -> ambiguous)

    def as_preview_row(self):
        return {"field": self.field, "column": self.header_text, "index": self.index,
                "ambiguous": len(self.candidates) > 1, "candidates": self.candidates}


def resolve_columns(header, synonyms: dict, required: set):
    """synonyms: {field: [regex, ...]}. Returns (matches: {field: ColumnMatch}, preview: [row, ...]).
    Raises Refuse if any field matches 2+ header cells (ambiguous) or a required field matches 0."""
    folded = [T.fold(h) for h in header]
    matches, preview, ambiguous = {}, [], []
    for field, patterns in synonyms.items():
        rxs = [re.compile(p) for p in patterns]
        hits = [i for i, h in enumerate(folded) if any(rx.search(h) for rx in rxs)]
        cand_texts = [header[i] for i in hits]
        if len(hits) > 1:
            ambiguous.append((field, cand_texts))
            cm = ColumnMatch(field, None, None, cand_texts)
        elif hits:
            cm = ColumnMatch(field, hits[0], header[hits[0]], cand_texts)
        else:
            cm = ColumnMatch(field, None, None, [])
        matches[field] = cm
        preview.append(cm.as_preview_row())
    if ambiguous:
        detail = ", ".join(f"{f} khớp {len(c)} cột ({', '.join(c)})" for f, c in ambiguous)
        raise Refuse(f"Mapping cột không rõ ràng, từ chối đoán: {detail}", {"ambiguous": ambiguous, "preview": preview})
    missing_required = [f for f in required if matches[f].index is None]
    if missing_required:
        raise Refuse("Thiếu cột bắt buộc: " + ", ".join(missing_required), {"missing": missing_required, "preview": preview})
    return matches, preview
