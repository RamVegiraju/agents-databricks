# Lower-code agents

[Northstar retail Genie Agents](genie-agents/README.md) demonstrates separate curated agents for sales and inventory, plus a combined retail configuration for the full-stack sample. Genie owns SQL generation, warehouse execution, and conversation handling; you curate data and business context. No custom server or agent loop is required.

The pro-code supervisor examples can call these same agents by space ID. Genie conversation history is separate from an Agent Bricks Session Store and is not automatically ingested into an Agent Bricks memory pipeline.
