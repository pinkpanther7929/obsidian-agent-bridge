# obsidian-agent-bridge

[English](README.md) | Korean

Claude Code, Codex, MCP 호환 코딩 에이전트가 Obsidian Vault를 로컬 메모리처럼 쓰게 해주는 브리지입니다.

작업을 알맞은 Vault 카테고리로 라우팅하고, 읽어야 할 최소 노트 목록을 돌려주며, 완료된 작업을 히스토리 노트로 기록하고, Vault 위생 상태를 점검합니다. 모든 처리는 로컬에서 끝납니다.

## 설치

### Claude Code

빠른 로컬 설정:

```powershell
git clone https://github.com/pinkpanther7929/obsidian-agent-bridge.git D:\obsidian-agent-bridge
cd D:\obsidian-agent-bridge
.\scripts\write-config.ps1 -Vault "$env:USERPROFILE\Documents\Obsidian Vault" -Language ko
.\scripts\install-claude.ps1
```

위 스크립트는 Claude Code에 MCP 서버를 등록합니다:

```powershell
claude mcp add -s user obsidian-agent-bridge -e PYTHONPATH=D:\obsidian-agent-bridge -- python -m mcp_server.server
```

`.claude-plugin/plugin.json`도 포함되어 있습니다. Claude Code 플러그인 마켓플레이스/워크플로에 이 저장소를 추가하면 플러그인 소스로 사용할 수 있게 준비해 둔 상태입니다.

### Codex

npm으로 GitHub 저장소를 전역 설치할 수 있습니다:

```powershell
npm install -g github:pinkpanther7929/obsidian-agent-bridge
```

그다음 Codex MCP 설정을 등록합니다:

```powershell
git clone https://github.com/pinkpanther7929/obsidian-agent-bridge.git D:\obsidian-agent-bridge
cd D:\obsidian-agent-bridge
.\scripts\write-config.ps1 -Vault "$env:USERPROFILE\Documents\Obsidian Vault" -Language ko
.\scripts\install-codex.ps1
```

등록 후 Codex를 재시작해야 합니다. 설치 스크립트는 `~/.codex/config.toml`에 아래 블록이 없으면 추가합니다:

```toml
[mcp_servers.obsidian_agent_bridge]
command = 'powershell.exe'
args = ['-NoProfile', '-File', 'D:\obsidian-agent-bridge\scripts\run-mcp.ps1']
startup_timeout_sec = 30
```

npm 전역 설치 후 사용할 수 있는 명령:

```powershell
obs-agent route --request "Update project memory" --json
obs-agent-mcp
```

## 기능

- `cwd`, 파일 경로, 요청 문장을 보고 프로젝트/카테고리를 라우팅합니다.
- 에이전트가 Vault 전체를 읽지 않도록 최소 `read_set`을 반환합니다.
- 완료된 작업을 `projects/<project>/<category>/history/`에 기록합니다.
- daily note에는 중복 없는 backlink 하나만 추가합니다.
- `archive/`를 기본 제외하고 Vault 노트를 읽고 검색합니다.
- 누락/모호한 노트 링크, 중복 daily backlink, secret처럼 보이는 내용을 점검합니다.
- config로 영어/한국어 메시지를 지원합니다.
- OAB 자동 메모리 상태를 CLI/MCP에서 확인하고 켜거나 끌 수 있습니다.

## 저장소 구조

```text
obsidian-agent-bridge/
  .claude-plugin/plugin.json
  bin/                  # npm 명령 wrapper
  cli/                  # CLI 구현
  mcp_server/           # 의존성 없는 stdio MCP 서버
  scripts/              # 설치/실행 helper
  agents/
  skills/
  examples/
  tests/
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
  "autoRecord": true,
  "memoryRecorderAgent": true,
  "includePrompt": true,
  "categoryHints": {
    "projects/engineering/backend": ["backend", "api", "auth", "database"],
    "projects/ai/agents": ["agent", "mcp", "tool", "memory"]
  }
}
```

`language`는 `en`, `ko`를 지원합니다. `--vault`는 config보다 우선합니다. 라우팅은 `projects/*/*/index.md`의 카테고리 이름, heading, wikilink도 힌트로 사용합니다.

## CLI

```powershell
obs-agent route --cwd C:\work\app --request "Fix stale login sessions" --json
obs-agent read --path CODEX.md --json
obs-agent search --query "session" --path-prefix projects --json
obs-agent record --category engineering/backend --title "auth session fix" --summary "Fixed stale session cleanup." --dry-run --json
obs-agent check --json
obs-agent oab status --json
obs-agent oab off --json
obs-agent oab on --json
```

npm 설치 없이 쓸 때:

```powershell
python cli\obs_agent.py route --request "Fix stale login sessions" --json
```

## MCP Tools

서버 실행:

```powershell
python -m mcp_server.server
# 또는
obs-agent-mcp
```

도구:

- `obs_route`
- `obs_read`
- `obs_search`
- `obs_record`
- `obs_check`
- `obs_oab`

권장 에이전트 흐름:

1. `obs_route` 호출
2. 반환된 `read_set`만 `obs_read`로 읽기
3. 사용자 작업 수행
4. `obs_record`에 `dry_run: true`로 미리보기
5. 최종 작업을 `obs_record`로 기록
6. 필요하면 `obs_check` 실행

`/oab status`, `/oab on`, `/oab off`, `/oab set ...` 요청은 `obs_oab` 또는 `obs-agent oab`로 처리하면 됩니다.

Claude/Codex 설정 예시는 [`examples/`](examples/)에 있고, 프로젝트 지시문 예시는 [`examples/AGENTS.md`](examples/AGENTS.md)에 있습니다.

## 개발

```powershell
python -m unittest discover -s tests
python -m py_compile cli\*.py mcp_server\*.py
```
