# Set up the memory sample

Run from `pro-code/02-agent-memory` after installing dependencies and choosing `PROFILE` as shown
in the [README](README.md). This creates persistent stores, a scheduled pipeline, and an App.
Use an unused name for a fresh setup; do not recreate resources for each conversation.

## 1. Prepare an isolated configuration

```bash
export AGENT_NAME="mem-$(date -u +%m%d%H%M)"
export APP_NAME="agent-bricks-$AGENT_NAME"
export SESSION_STORE="$AGENT_NAME-sessions"
export TRANSCRIPT_STORE="$AGENT_NAME-transcripts"
export MEMORY_NAME="$AGENT_NAME-memory"
export SOURCE="$(mktemp -d)/$AGENT_NAME"
mkdir -p "$SOURCE"
rsync -a --exclude .venv --exclude .env --exclude .agentbricks \
  --exclude __pycache__ --exclude .pytest_cache ./ "$SOURCE/"
mkdir -p "$SOURCE/.agentbricks"
cp .agentbricks/project.toml "$SOURCE/.agentbricks/project.toml"
uv run --frozen agentbricks sessions bind "$SESSION_STORE" --source "$SOURCE"
uv run --frozen agentbricks memory bind "$MEMORY_NAME" --source "$SOURCE"
uv run --frozen agentbricks tracing bind \
  --experiment-name "/Shared/agentbricks_traces/$AGENT_NAME" --source "$SOURCE"
cat > "$SOURCE/app.yaml" <<APP_CONFIG
command: ["uv", "run", "start-server"]
env:
  - name: MEMORY_WRITE_MODE
    value: pipeline
  - name: MEMORY_AUTO_RECALL
    value: "false"
  - name: AGENT_TRANSCRIPT_STORE
    value: "$TRANSCRIPT_STORE"
APP_CONFIG
```

This requires `rsync`. The copy keeps deployment-generated settings separate from the original sample.

## 2. Create the stores

```bash
time uv run --frozen agentbricks --profile "$PROFILE" --output json sessions stores create \
  --name "$SESSION_STORE"
time uv run --frozen agentbricks --profile "$PROFILE" --output json sessions stores create \
  --name "$TRANSCRIPT_STORE"
time uv run --frozen agentbricks --profile "$PROFILE" --output json memory stores create \
  --display-name "$MEMORY_NAME"
export MEMORY_STORE='memory-stores/REPLACE_WITH_RETURNED_ID'
```

Copy the Memory Store's actual returned `name`; do not assume the display name is its ID.
The checkpoint store holds graph state; the transcript store holds pipeline-readable messages;
the Memory Store holds extracted knowledge.

## 3. Create the pipeline and deploy

```bash
time uv run --frozen agentbricks --profile "$PROFILE" --output json memory pipeline create \
  --session-store "$TRANSCRIPT_STORE" --memory-store "$MEMORY_STORE" \
  --model system.ai.claude-sonnet-4-5 \
  --instructions @resources/memory-instructions.txt --trigger scheduled
export PIPELINE='memory-pipelines/REPLACE_WITH_RETURNED_ID'
time uv run --frozen agentbricks --profile "$PROFILE" deploy "$AGENT_NAME" --source "$SOURCE"
uv run --frozen python scripts/grant_transcript_access.py \
  --profile "$PROFILE" --app "$APP_NAME" --store "$TRANSCRIPT_STORE"
```

Copy the returned pipeline `name`. Deployment creates the App, reconciles checkpoint/memory grants,
and configures tracing. The extra grant covers the transcript store. The App and pipeline run under
different identities: App service principal for chat, pipeline creator for distillation.

Open the returned App URL and continue with [Try it end to end](README.md#try-it-end-to-end), keeping
these variables in the same terminal. Store/pipeline creation and App startup can take time;
distillation is a separate run after a conversation, not part of creating the pipeline.

For later use, recover identifiers with `memory pipeline list` and `deployments get APP_NAME`.
Stop App compute and pause scheduled work using the [README cleanup commands](README.md#inspect-and-stop).
