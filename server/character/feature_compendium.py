"""Central feature compendium loader and matcher.

The compendium is intentionally conservative: public records contain structured
metadata plus safe summaries, while imported/private PDF text remains attached to
character data and is never copied back into the shared rules files.
"""
from __future__ import annotations

import copy
import difflib
import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1] / "data" / "rules" / "5e2024" / "features"


def _slug(value: Any) -> str:
    text = str(value or "").strip().lower()
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-")


def _norm(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().lower())


def _clone(value: Any) -> Any:
    return copy.deepcopy(value)


class FeatureCompendium:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or ROOT
        self.features: list[dict[str, Any]] = []
        self.by_id: dict[str, dict[str, Any]] = {}
        self.by_slug: dict[str, dict[str, Any]] = {}
        self.by_name: dict[str, dict[str, Any]] = {}
        self.duplicates: list[dict[str, Any]] = []
        self._load()

    def _iter_files(self) -> Iterable[Path]:
        index = self.root / "index.json"
        if index.exists():
            data = json.loads(index.read_text(encoding="utf-8"))
            for name in data.get("files") or []:
                path = self.root / str(name)
                if path.exists() and path.name != "index.json":
                    yield path
            return
        yield from sorted(p for p in self.root.glob("*.json") if p.name != "index.json")

    def _dedupe_key(self, row: dict[str, Any]) -> str:
        fid = _norm(row.get("id"))
        slug = _slug(row.get("slug") or row.get("name"))
        name = _norm(row.get("name"))
        source = _norm(row.get("source"))
        kind = _norm(row.get("kind"))
        owner = _norm(row.get("class_id") or row.get("subclass_id") or row.get("species_id") or row.get("feat_id") or row.get("background_id") or row.get("item_id"))
        return fid or f"{kind}:{owner}:{slug or name}:{source}"

    def _merge(self, canonical: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
        merged = _clone(canonical)
        aliases = list(merged.get("aliases") or []) + list(incoming.get("aliases") or [])
        aliases.extend([incoming.get("id"), incoming.get("slug"), incoming.get("name")])
        merged["aliases"] = [a for a in dict.fromkeys(str(a) for a in aliases if a)]
        notes = list(merged.get("import_notes") or [])
        if incoming.get("source") and incoming.get("source") != merged.get("source"):
            notes.append(str(incoming.get("source")))
        if notes:
            merged["import_notes"] = [n for n in dict.fromkeys(notes)]
        for key, value in incoming.items():
            if key.startswith("homebrew_") or key.startswith("custom_"):
                merged.setdefault(key, _clone(value))
            elif merged.get(key) in (None, "", [], {}):
                merged[key] = _clone(value)
        return merged

    def _load(self) -> None:
        seen: dict[str, dict[str, Any]] = {}
        for path in self._iter_files():
            data = json.loads(path.read_text(encoding="utf-8"))
            for row in data.get("features") or []:
                if not isinstance(row, dict):
                    continue
                row = _clone(row)
                row.setdefault("slug", _slug(row.get("name") or row.get("id")))
                row.setdefault("aliases", [])
                key = self._dedupe_key(row)
                owner = _norm(row.get("class_id") or row.get("subclass_id") or row.get("species_id") or row.get("feat_id") or row.get("background_id") or row.get("item_id"))
                alt = f"{_norm(row.get('kind'))}:{owner}:{_norm(row.get('source'))}:{_slug(row.get('name'))}"
                match_key = key if key in seen else alt if alt in seen else ""
                if match_key:
                    seen[match_key] = self._merge(seen[match_key], row)
                    self.duplicates.append({"kept": seen[match_key].get("id"), "merged": row.get("id"), "name": row.get("name")})
                else:
                    seen[key] = row
                    seen[alt] = row
        unique = []
        ids = set()
        for row in seen.values():
            obj_id = id(row)
            if obj_id in ids:
                continue
            ids.add(obj_id)
            unique.append(row)
        self.features = unique
        for row in self.features:
            for key in [row.get("id"), *(row.get("aliases") or [])]:
                if key:
                    self.by_id[_norm(key)] = row
            self.by_slug[_slug(row.get("slug") or row.get("name"))] = row
            self.by_name[_norm(row.get("name"))] = row

    def lookup(self, value: Any, *, fuzzy: bool = True) -> dict[str, Any] | None:
        key = _norm(value)
        if not key:
            return None
        found = self.by_id.get(key) or self.by_slug.get(_slug(key)) or self.by_name.get(key)
        if found or not fuzzy:
            return _clone(found) if found else None
        names = list(self.by_name.keys())
        matches = difflib.get_close_matches(key, names, n=1, cutoff=0.82)
        return _clone(self.by_name[matches[0]]) if matches else None

    def filter(self, **criteria: Any) -> list[dict[str, Any]]:
        out = []
        for row in self.features:
            ok = True
            for key, expected in criteria.items():
                if expected in (None, ""):
                    continue
                if _norm(row.get(key)) != _norm(expected):
                    ok = False; break
            if ok:
                out.append(_clone(row))
        return out

    def by_class(self, class_id: str) -> list[dict[str, Any]]: return self.filter(class_id=class_id, kind="class")
    def by_subclass(self, subclass_id: str) -> list[dict[str, Any]]: return self.filter(subclass_id=subclass_id)
    def by_species(self, species_id: str) -> list[dict[str, Any]]: return self.filter(species_id=species_id)
    def by_feat(self, feat_id: str) -> list[dict[str, Any]]: return self.filter(feat_id=feat_id)
    def by_background(self, background_id: str) -> list[dict[str, Any]]: return self.filter(background_id=background_id)
    def by_item(self, item_id: str) -> list[dict[str, Any]]: return self.filter(item_id=item_id)
    def by_action_type(self, action_type: str) -> list[dict[str, Any]]: return self.filter(action_type=action_type)
    def by_resource(self, resource_name: str) -> list[dict[str, Any]]:
        return [ _clone(r) for r in self.features if _norm(r.get("resource_name")) == _norm(resource_name) ]

    def merge_imported_feature(self, imported: dict[str, Any]) -> dict[str, Any]:
        name = imported.get("name") or imported.get("displayName") or imported.get("id")
        canonical = self.lookup(imported.get("id"), fuzzy=False) or self.lookup(name, fuzzy=True)
        private = {k: _clone(v) for k, v in imported.items() if k in {"text", "description", "rawText", "sourceText"}}
        if canonical:
            merged = self._merge(canonical, {"source": imported.get("source") or "imported", "aliases": [imported.get("id"), name]})
            if private:
                merged["private_imported_text"] = private
            return merged
        stub = {
            "id": str(imported.get("id") or f"imported-{_slug(name)}"), "slug": _slug(name), "name": str(name or "Imported Feature"),
            "aliases": [str(name or "")], "source": imported.get("source") or "imported", "source_bucket": "private_import",
            "kind": "imported", "action_type": "passive", "safe_summary": "Imported feature. Needs DM review before public compendium use.",
            "rules_summary": "Needs DM content", "needs_review": True, "implementation_status": "imported_private_stub",
            "private_imported_text": private,
        }
        return stub


@lru_cache(maxsize=1)
def load_feature_compendium() -> FeatureCompendium:
    return FeatureCompendium()
