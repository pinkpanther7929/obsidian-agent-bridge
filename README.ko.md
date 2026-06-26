# obsidian-agent-bridge

[English](README.md) | 한국어

코딩 에이전트를 위한 로컬 우선 Obsidian 메모리 도구입니다.

`obsidian-agent-bridge`는 Obsidian Vault를 단순한 Markdown 폴더가 아니라
작고 예측 가능한 에이전트 메모리 시스템처럼 사용할 수 있게 해줍니다.
작업을 알맞은 프로젝트 노트로 라우팅하고, 완료된 작업을 카테고리별
히스토리에 기록하며, Vault의 링크/기록 상태를 점검합니다.

## 기능

- `cwd`, 파일 경로, 요청 문장을 기반으로 작업을 프로젝트/카테고리에 라우팅합니다.
- 에이전트가 Vault 전체를 읽지 않도록 최소 `read_set`을 반환합니다.
- 완료된 작업을 `projects/<project>/<category>/history/`에 기록합니다.
- daily note에는 중복 없는 짧은 backlink 하나만 추가합니다.
- 누락/모호한 note link, 중복 daily backlink, secret처럼 보이는 내용을 점검합니다.
- Vault 경로, 라우팅 힌트, daily 폴더, 히스토리 템플릿을 config로 설정할 수 있습니다.

현재 기본 인터페이스는 CLI입니다. Agent spec, skill, MCP server가 같은 기능을 감싸서 사용합니다.
의존성 없는 stdio MCP server도 포함되어 있습니다.

## 저장소 구조

```text
obsidian-agent-bridge/
  cli/
    obs_agent.py      # CLI 진입점
    config.py         # config 로딩
    router.py         # 라우팅 점수 계산 및 Vault 기반 힌트
    recorder.py       # history + daily 기록
    checker.py        # 링크/secret 점검
    vault.py          # 안전한 Vault 파일 접근
  agents/
    vault-curator.md
  mcp_server/
    server.py
  examples/
    claude_desktop_config.json
    codex_config.toml
  skills/
    obsidian-memory/SKILL.md
  tests/
    test_core.py
```

## 빠른 시작

```powershell
python cli\obs_agent.py route --cwd C:\work\app --path src\auth\session.py --request "Fix stale login sessions" --json
python cli\obs_agent.py read --path CODEX.md --json
python cli\obs_agent.py search --query "session" --path-prefix projects --json
python cli\obs_agent.py record --category engineering/backend --title "auth session fix" --summary "Fixed stale session cleanup." --dry-run --json
python cli\obs_agent.py check --json
```

기본 Vault 경로:

```text
~/Documents/Obsidian Vault
```

`--vault`, `OBSIDIAN_VAULT_PATH`, `--config`, `OBS_AGENT_CONFIG`로 덮어쓸 수 있습니다.

로컬 config 생성:

```powershell
.\scripts\write-config.ps1 -Vault "$env:USERPROFILE\Documents\Obsidian Vault" -Language ko
```

## Config

기본 config 경로:

```text
~/.obsidian-agent-bridge/config.json
```

예시:

```json
{
  "vault": "~/Documents/Obsidian Vault",
  "language": "ko",
  "dailyFolder": "daily",
  "historyTemplate": "# {date} {title}\n\n{summary}\n",
  "categoryHints": {
    "projects/engineering/backend": ["backend", "api", "auth", "database"],
    "projects/ai/agents": ["agent", "mcp", "tool", "memory"]
  }
}
```

`language`는 `en`, `ko`를 지원합니다. 라우팅 이유와 검증 오류 메시지를 현지화합니다.
`--vault`는 config 파일보다 우선합니다. `historyTemplate`은 `{date}`, `{title}`,
`{summary}`, `{category}`를 지원합니다.

라우팅은 `projects/*/*/index.md`도 스캔합니다. 카테고리 경로, index heading,
wikilink target이 라우팅 힌트가 되므로 모든 카테고리를 config에 직접 적지 않아도 됩니다.

## 명령

### `route`

작업에 맞는 카테고리와 최소 읽기 노트를 추천합니다.

```powershell
python cli\obs_agent.py route `
  --cwd C:\work\app `
  --path src\auth\session.py `
  --request "Fix stale login sessions" `
  --json
```

출력 예시:

```json
{
  "category": "projects/engineering/backend",
  "confidence": 0.55,
  "reason": "Matched session",
  "read_set": ["CODEX.md", "projects/engineering/backend/index.md"]
}
```

### `record`

히스토리 노트를 만들고 daily backlink를 추가합니다.

```powershell
python cli\obs_agent.py record `
  --category engineering/backend `
  --title "auth session fix" `
  --summary "Fixed stale session cleanup." `
  --dry-run `
  --json
```

`--dry-run`은 실제 파일을 쓰지 않고 `note_path`, `daily_link`, `note_text`를 미리 보여줍니다.

### `read`

Vault 기준 상대 경로로 note 하나를 읽습니다.

```powershell
python cli\obs_agent.py read --path CODEX.md --json
```

### `search`

archive를 제외한 Markdown note를 검색합니다.

```powershell
python cli\obs_agent.py search `
  --query "session" `
  --path-prefix projects `
  --limit 20 `
  --json
```

### `check`

Vault 상태를 점검합니다.

```powershell
python cli\obs_agent.py check --json
```

점검 항목:

- 누락된 note link
- 모호한 짧은 wikilink
- note를 가리키는 상대 Markdown link
- 중복 daily backlink
- secret처럼 보이는 내용

## Agent Workflow

권장 에이전트 흐름:

1. `route` 실행
2. 반환된 `read_set`만 읽기
3. 사용자 작업 수행
4. `record --dry-run` 실행
5. 대상 카테고리와 note text 확인
6. `record` 실행
7. 필요하면 `check` 실행

포함된 agent/skill 문서:

- [`agents/vault-curator.md`](agents/vault-curator.md)
- [`skills/obsidian-memory/SKILL.md`](skills/obsidian-memory/SKILL.md)

## MCP Server

stdio MCP server 실행:

```powershell
python -m mcp_server.server
```

Windows에서는 cwd-safe wrapper도 제공합니다.

```powershell
powershell.exe -NoProfile -File D:\obsidian-agent-bridge\scripts\run-mcp.ps1
```

패키지로 설치했다면:

```powershell
obs-agent-mcp
```

MCP tools:

- `obs_route`
- `obs_read`
- `obs_search`
- `obs_record`
- `obs_check`

Claude Desktop 예시:

```json
{
  "mcpServers": {
    "obsidian-agent-bridge": {
      "command": "python",
      "args": ["-m", "mcp_server.server"],
      "cwd": "D:\\obsidian-agent-bridge"
    }
  }
}
```

Codex config 예시:

```toml
[mcp_servers.obsidian-agent-bridge]
command = "python"
args = ["-m", "mcp_server.server"]
cwd = "D:\\obsidian-agent-bridge"
```

Claude Code 등록 명령:

```powershell
claude mcp add -s user obsidian-agent-bridge -- powershell.exe -NoProfile -File D:\obsidian-agent-bridge\scripts\run-mcp.ps1
```

복사 가능한 설정 예시는 [`examples/`](examples/)에 있습니다.

Claude/Codex 프로젝트 지시는 [`examples/AGENTS.md`](examples/AGENTS.md)의 내용을 참고하면 됩니다.

## 개발

테스트 실행:

```powershell
python -m unittest discover -s tests
```

GitHub Actions도 push/pull request에서 같은 테스트를 실행합니다.
