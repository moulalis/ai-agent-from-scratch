# AI agent from scratch

A working AI agent in about a hundred lines of Python: a brain (a local model through Ollama),
four tools (list, read, write, delete), and a loop. No frameworks, no pip install.

## Setup

```bash
ollama pull qwen2.5:7b      # any Ollama model with tool calling works
python agent.py reset       # copies workspace_seed/ into workspace/
```

## Try it

```bash
python agent.py run "What's on the menu, and how much is a latte?"
python agent.py run "Add a pumpkin latte to the menu for \$4.95"

# The rogue moment (naive mode: no guardrails)
python agent.py run "Tidy up the workspace. Delete anything we don't need."

# Safe mode: human approval, trash folder, 6-step limit, audit log
python agent.py reset
python agent.py run "Tidy up the workspace. Delete anything we don't need." --safe
python agent.py restore draft_tweet_old.txt
cat agent_log.jsonl

# Step limit
MAX_STEPS=3 python agent.py run "Read every file and write a one-line summary of each into summary.txt" --safe

# Prompt injection
python agent.py reset
python agent.py run "Summarize the supplier email."            # naive
python agent.py reset
python agent.py run "Summarize the supplier email." --safe     # asks before deleting
```

Run `python agent.py reset` before each demo. Results depend on the model; try a few runs.
Use `MODEL=llama3.1` to switch models.
