"""Load tagged inputs and the source register."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import yaml

DATA = Path(__file__).resolve().parents[1] / "data"
TAGS = ("Sourced", "Estimated", "Illustrative", "Definition")


@dataclass(frozen=True)
class Input:
    key: str
    label: str
    value: float
    unit: str
    tag: str
    source: str
    section: str
    note: str = ""


def load_sources() -> dict:
    return yaml.safe_load((DATA / "sources.yaml").read_text())


def load_inputs(name: str) -> list[Input]:
    """``name`` is 'property' or 'solar_storage'; reads data/<name>_inputs.yaml."""
    raw = yaml.safe_load((DATA / f"{name}_inputs.yaml").read_text())
    sources = load_sources()
    out, seen = [], set()
    for section, items in raw.items():
        for it in items:
            inp = Input(section=section, note=it.get("note", ""), **{k: it[k] for k in
                        ("key", "label", "value", "unit", "tag", "source")})
            if inp.key in seen:
                raise ValueError(f"duplicate input key {inp.key}")
            if inp.tag not in TAGS:
                raise ValueError(f"{inp.key}: tag must be one of {TAGS}")
            if inp.source not in sources:
                raise ValueError(f"{inp.key}: unknown source id {inp.source!r}")
            seen.add(inp.key)
            out.append(inp)
    return out


def values(inputs: list[Input], **overrides) -> dict[str, float]:
    v = {i.key: float(i.value) for i in inputs}
    unknown = set(overrides) - set(v)
    if unknown:
        raise KeyError(f"unknown input(s): {sorted(unknown)}")
    v.update({k: float(x) for k, x in overrides.items()})
    return v


def fingerprint(inputs: list[Input]) -> str:
    blob = json.dumps([[i.key, i.value, i.tag, i.source] for i in inputs], sort_keys=True)
    return hashlib.sha256(blob.encode()).hexdigest()[:12]
