from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator

_VAULT_PATH = Path("data/.vault/tokens.json")


class TokenVault:
    def __init__(self, path: Path = _VAULT_PATH) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._store: Dict[str, str] = {}
        if self.path.exists():
            try:
                self._store = json.loads(self.path.read_text(encoding="utf-8"))
            except Exception:
                self._store = {}

    def save(self) -> None:
        self.path.write_text(json.dumps(self._store, ensure_ascii=False, indent=2), encoding="utf-8")

    def token_for(self, kind: str, value: str) -> str:
        key = f"{kind}:{value}"
        if key not in self._store:
            index = sum(1 for k in self._store.keys() if k.startswith(f"{kind}:")) + 1
            self._store[key] = f"[{kind.upper()}_{index}]"
            self.save()
        return self._store[key]


_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_UUID_RE = re.compile(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}\b")
_URL_RE = re.compile(r"\bhttps?://[^\s]+")
_PHONE_RE = re.compile(r"\b(?:\+?\d[\s.-]?){7,}\d\b")


def _mask_text(text: str, mode: str, vault: TokenVault) -> str:
    # Order matters: longer/more specific first
    patterns = [
        ("email", _EMAIL_RE),
        ("uuid", _UUID_RE),
        ("url", _URL_RE),
        ("phone", _PHONE_RE),
    ]
    def repl(kind: str):
        def _r(m: re.Match[str]) -> str:
            val = m.group(0)
            if mode == "pseudonymize":
                return vault.token_for(kind, val)
            return "[REDACTED]"
        return _r
    out = text
    for kind, regex in patterns:
        out = regex.sub(repl(kind), out)
    return out


def _transform(records: Iterable[Dict[str, Any]], mode: str) -> Iterator[Dict[str, Any]]:
    vault = TokenVault()
    for rec in records:
        new_rec = dict(rec)
        text = new_rec.get("content_text")
        if isinstance(text, str):
            new_rec["content_text"] = _mask_text(text, mode=mode, vault=vault)
        yield new_rec


def pseudonymize(records: Iterable[Dict[str, Any]], profile: str = "default") -> Iterable[Dict[str, Any]]:
    return _transform(records, mode="pseudonymize")


def redact(records: Iterable[Dict[str, Any]], profile: str = "strict") -> Iterable[Dict[str, Any]]:
    return _transform(records, mode="redact")
