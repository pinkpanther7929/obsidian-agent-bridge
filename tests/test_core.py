from __future__ import annotations

import tempfile
import unittest
import json
from pathlib import Path

from cli.config import AppConfig
from cli.recorder import record
from cli.router import route
from cli.vault import Vault


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

    def test_config_loads_custom_hints_and_daily_folder(self) -> None:
        vault = self.make_vault()
        config_path = vault.root / "config.json"
        config_path.write_text(
            json.dumps(
                {
                    "dailyFolder": "journal",
                    "categoryHints": {"projects/ai/agents": ["curator"]},
                }
            ),
            encoding="utf-8",
        )
        config = AppConfig.load(str(config_path))
        routed = route(vault, request="Build curator workflow", category_hints=config.category_hints)
        result = record(
            vault,
            category="ai/agents",
            title="curator workflow",
            summary="Added workflow.",
            date="2026-06-26",
            daily_folder=config.daily_folder,
        )
        self.assertEqual(routed.category, "projects/ai/agents")
        self.assertEqual(result.daily_path, "journal/2026-06-26.md")


if __name__ == "__main__":
    unittest.main()
