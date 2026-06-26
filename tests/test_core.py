from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from obsidian_agent_bridge.recorder import record
from obsidian_agent_bridge.router import route
from obsidian_agent_bridge.vault import Vault


class CoreTests(unittest.TestCase):
    def make_vault(self) -> Vault:
        tmp_root = Path.cwd() / ".tmp"
        tmp_root.mkdir(exist_ok=True)
        tmp = tempfile.TemporaryDirectory(dir=tmp_root)
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        (root / "CODEX.md").write_text("# CODEX\n", encoding="utf-8")
        category = root / "projects" / "ai" / "agents"
        category.mkdir(parents=True)
        (category / "index.md").write_text("# Local LLM\n", encoding="utf-8")
        return Vault(root)

    def test_route_prefers_agent_notes(self) -> None:
        vault = self.make_vault()
        result = route(vault, cwd=r"C:\work\app", request="Add an MCP agent memory tool")
        self.assertEqual(result.category, "projects/ai/agents")
        self.assertIn("CODEX.md", result.read_set)

    def test_record_writes_history_and_daily_once(self) -> None:
        vault = self.make_vault()
        first = record(
            vault,
            category="ai/agents",
            title="agent memory tool",
            summary="Configured tool.",
            date="2026-06-26",
        )
        second = record(
            vault,
            category="ai/agents",
            title="agent memory tool",
            summary="Configured tool.",
            date="2026-06-26",
        )
        self.assertTrue(vault.path(first.note_path).exists())
        self.assertTrue(first.daily_added)
        self.assertFalse(second.daily_added)


if __name__ == "__main__":
    unittest.main()
