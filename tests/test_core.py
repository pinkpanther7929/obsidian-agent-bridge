from __future__ import annotations

import tempfile
import unittest
import json
from pathlib import Path

from cli.config import AppConfig
from cli.checker import check
from cli.reader import read_note, search_notes
from cli.recorder import record
from cli.router import build_category_hints, route
from cli.vault import Vault
from mcp_server.server import handle


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
                    "historyTemplate": "# {title}\n\n{summary}\n\nCategory: {category}\n",
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
            history_template=config.history_template,
            dry_run=True,
        )
        self.assertEqual(routed.category, "projects/ai/agents")
        self.assertEqual(result.daily_path, "journal/2026-06-26.md")
        self.assertIn("Category: projects/ai/agents", result.note_text)
        self.assertIn("[[projects/ai/agents/history/2026-06-26-curator-workflow", result.daily_link)

    def test_korean_language_localizes_route_reason(self) -> None:
        vault = self.make_vault()
        result = route(vault, request="MCP agent memory", language="ko")
        self.assertTrue(result.reason.startswith("\uc77c\uce58\ud55c \ud78c\ud2b8"))

    def test_korean_language_localizes_category_errors(self) -> None:
        with self.assertRaisesRegex(Exception, "\uce74\ud14c\uace0\ub9ac"):
            record(
                self.make_vault(),
                category="bad",
                title="\uc81c\ubaa9",
                summary="\uc694\uc57d",
                language="ko",
                dry_run=True,
            )

    def test_route_learns_categories_from_vault_indexes(self) -> None:
        vault = self.make_vault()
        category = vault.root / "projects" / "research" / "papers"
        category.mkdir(parents=True)
        (category / "index.md").write_text("# Papers\n\n- [[retrieval-notes]]\n", encoding="utf-8")
        hints = build_category_hints(vault, seed={})
        result = route(vault, request="Summarize retrieval notes", category_hints={})
        self.assertIn("projects/research/papers", hints)
        self.assertEqual(result.category, "projects/research/papers")

    def test_check_resolves_relative_and_markdown_links(self) -> None:
        vault = self.make_vault()
        docs = vault.root / "projects" / "ai" / "agents"
        (docs / "details.md").write_text("# Details\n", encoding="utf-8")
        (docs / "index.md").write_text("[[details]]\n[details](details.md)\n", encoding="utf-8")
        result = check(vault)
        self.assertEqual(result["error_count"], 0)

    def test_check_reports_ambiguous_stem_links(self) -> None:
        vault = self.make_vault()
        left = vault.root / "projects" / "left" / "area"
        right = vault.root / "projects" / "right" / "area"
        left.mkdir(parents=True)
        right.mkdir(parents=True)
        (left / "shared.md").write_text("# Shared\n", encoding="utf-8")
        (right / "shared.md").write_text("# Shared\n", encoding="utf-8")
        (vault.root / "CODEX.md").write_text("[[shared]]\n", encoding="utf-8")
        result = check(vault)
        self.assertEqual(result["errors"][0]["kind"], "ambiguous_link")

    def test_read_and_search_notes(self) -> None:
        vault = self.make_vault()
        path = vault.root / "projects" / "ai" / "agents" / "index.md"
        path.write_text("# Agents\n\nMemory routing\n", encoding="utf-8")
        read = read_note(vault, path="projects/ai/agents/index.md", start=2, lines=2)
        hits = search_notes(vault, query="memory", path_prefix="projects/ai", limit=5)
        self.assertEqual(read.content, "\nMemory routing")
        self.assertEqual(hits[0].path, "projects/ai/agents/index.md")

    def test_mcp_lists_and_calls_route_tool(self) -> None:
        listed = handle({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
        self.assertIsNotNone(listed)
        self.assertIn("obs_route", {tool["name"] for tool in listed["result"]["tools"]})

        vault = self.make_vault()
        called = handle(
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": "obs_route",
                    "arguments": {
                        "vault": str(vault.root),
                        "config": str(vault.root / "missing-config.json"),
                        "request": "MCP agent memory",
                    },
                },
            }
        )
        self.assertIsNotNone(called)
        content = called["result"]["content"][0]["text"]
        self.assertIn("projects/ai/agents", content)


if __name__ == "__main__":
    unittest.main()
