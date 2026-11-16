"""Adapter registry. Adding an adapter = adding one module + one call to `register()` here -- never editing an
existing adapter or facts.py (decision 1/G3). `detect()` refuses rather than guesses when 0 or >1 adapter
claims the input (G4: 'unknown layout' refusal)."""
from core import tsv as T

from v4.adapters.base import Refuse

_ADAPTERS = []


def register(adapter):
    _ADAPTERS.append(adapter)
    return adapter


def detect(text):
    """-> the single adapter module that claims this text. Refuses on 0 or >1 matches."""
    lines = T.split_text(text)
    hits = [a for a in _ADAPTERS if a.sniff(lines)]
    if not hits:
        raise Refuse("Không nhận diện được layout input (không khớp adapter nào đã đăng ký).")
    if len(hits) > 1:
        names = ", ".join(a.NAME for a in hits)
        raise Refuse(f"Input khớp nhiều adapter ({names}) -- không tự chọn, cần làm layout rõ ràng hơn.")
    return hits[0]


def parse(text, add):
    """-> (adapter_name, order, data, extra). `add` is the checks-reporter callback (name, status, detail)."""
    adapter = detect(text)
    lines = T.split_text(text)
    order, data, extra = adapter.parse(lines, add)
    extra["format"] = adapter.NAME
    return adapter.NAME, order, data, extra


def _bootstrap():
    """Registers the built-in adapters. A NEW adapter is one module + one register() call added here --
    never an edit to an existing adapter, base.py or facts.py (decision 1/G3)."""
    from v4.adapters import v2 as _v2
    from v4.adapters import v3 as _v3
    register(_v2)
    register(_v3)


_bootstrap()
