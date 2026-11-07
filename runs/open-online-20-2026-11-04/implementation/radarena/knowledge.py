"""Small versioned reference packs, separate from learned memory and case labels."""

import hashlib
import json
from pathlib import Path


class KnowledgePack:
    def __init__(self, path: Path):
        content = path.read_bytes()
        self.sha256 = hashlib.sha256(content).hexdigest()
        self.data = json.loads(content)
        for key in ["pack_id", "version", "review_status", "scope", "sources", "cards", "role_guidance"]:
            if key not in self.data:
                raise ValueError(f"Reference pack lacks {key}")
        source_ids = [s["id"] for s in self.data["sources"]]
        card_ids = [c["id"] for c in self.data["cards"]]
        if len(set(source_ids)) != len(source_ids) or len(set(card_ids)) != len(card_ids):
            raise ValueError("Duplicate reference source or card IDs")
        if not card_ids:
            raise ValueError("Reference pack is empty")
        for card in self.data["cards"]:
            if not card["text"].strip() or not card["source_ids"] or not set(card["source_ids"]) <= set(source_ids):
                raise ValueError("Each knowledge card needs text and known source IDs")

    def render(self, role="verifier") -> str:
        if role not in {"red", "verifier"}:
            raise ValueError("Reference role must be red or verifier")
        lines = [f"Reference pack: {self.data['pack_id']} ({self.data['version']})",
                 f"Review status: {self.data['review_status']}",
                 f"Scope: {self.data['scope']}"]
        for card in self.data["cards"]:
            lines.append(f"[{card['id']}; sources: {', '.join(card['source_ids'])}] {card['title']}: {card['text']}")
        lines.append(f"Role instructions: {self.data['role_guidance'][role]}")
        text = "\n".join(lines)
        if len(text) > 8000:
            raise ValueError("Reference context exceeds 8,000 characters; curate or add retrieval before expanding")
        return text

    def metadata(self):
        return {"pack_id": self.data["pack_id"], "version": self.data["version"],
                "sha256": self.sha256, "card_ids": [c["id"] for c in self.data["cards"]],
                "review_status": self.data["review_status"]}


def load_pack(path=None, condition="full"):
    if path is None:
        if condition != "full":
            raise ValueError("Handbook ablation requires a handbook directory")
        return None
    path = Path(path)
    if path.is_dir():
        from .handbook import RadiologyHandbook
        return RadiologyHandbook(path, condition=condition)
    if condition != "full":
        raise ValueError("Handbook ablation applies to a handbook directory, not a JSON pack")
    return KnowledgePack(path)


def reference_context(knowledge, role, sentences, lm):
    if knowledge is None:
        return ""
    if hasattr(knowledge, "context_for"):
        # Only the caller's public/source sentences enter the selector, never a
        # benchmark record containing private labels or the other agent's data.
        return knowledge.context_for(role, "\n".join(s.text for s in sentences), lm)
    return knowledge.render(role)
