from __future__ import annotations

from typing import Any, Dict

from app.services.notes_store import NotesStore


class NotesTool:
    def __init__(self, db_path: str) -> None:
        self.store = NotesStore(db_path)

    def __call__(self, args: Dict[str, Any]) -> Dict[str, Any]:
        action = str(args.get("action", "search")).strip().lower()

        if action == "add":
            content = str(args.get("content", "")).strip()
            tags = str(args.get("tags", "")).strip()
            if not content:
                return {"error": "content is required for add action"}
            note = self.store.add_note(content=content, tags=tags)
            return {"action": "add", "note": note}

        if action == "recent":
            limit = int(args.get("limit", 5))
            return {"action": "recent", "notes": self.store.recent_notes(limit=limit)}

        query = str(args.get("query", "")).strip()
        if not query:
            return {"error": "query is required for search action"}
        limit = int(args.get("limit", 5))
        return {"action": "search", "notes": self.store.search_notes(query=query, limit=limit)}
