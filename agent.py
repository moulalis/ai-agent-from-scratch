"""An AI agent from scratch: a brain, four tools and a loop. No frameworks."""
import json, os, shutil, sys, time, urllib.request

MODEL = os.environ.get("MODEL", "qwen2.5:7b")
OLLAMA = os.environ.get("OLLAMA_URL", "http://localhost:11434")
HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.join(HERE, "workspace")
TRASH = os.path.join(HERE, ".trash")
LOG = os.path.join(HERE, "agent_log.jsonl")
SAFE = "--safe" in sys.argv
SYSTEM = "You manage files for the Byte & Bean coffee shop. Use the tools."


# ---- The hands: four tools, all plain Python ----

def safe_path(name):
    # Guardrail zero: every path must stay inside the workspace folder.
    path = os.path.realpath(os.path.join(WORK, name))
    if not path.startswith(os.path.realpath(WORK) + os.sep):
        raise ValueError(f"{name} is outside the workspace")
    return path

def list_files():
    return "\n".join(sorted(os.listdir(WORK)))

def read_file(name):
    with open(safe_path(name)) as f:
        return f.read()

def write_file(name, content):
    if SAFE and not approve(f"write {name}"):
        return "DENIED by human"
    with open(safe_path(name), "w") as f:
        f.write(content)
    return f"wrote {name}"

def delete_file(name):
    path = safe_path(name)
    if not SAFE:
        os.remove(path)
        return f"deleted {name}"
    if not approve(f"delete {name}"):
        return "DENIED by human"
    os.makedirs(TRASH, exist_ok=True)
    shutil.move(path, os.path.join(TRASH, name))  # reversible: moved, not destroyed
    return f"moved {name} to trash"

TOOLS = {"list_files": list_files, "read_file": read_file,
         "write_file": write_file, "delete_file": delete_file}


# ---- The menu: tool schemas the model reads ----

def schema(tool, description, **params):
    props = {p: {"type": "string", "description": d} for p, d in params.items()}
    return {"type": "function", "function": {
        "name": tool, "description": description,
        "parameters": {"type": "object", "properties": props,
                       "required": list(params)}}}

TOOL_SCHEMAS = [
    schema("list_files", "List every file in the workspace."),
    schema("read_file", "Read one file and return its text.",
           name="file name, e.g. menu.md"),
    schema("write_file", "Create or overwrite a file.",
           name="file name", content="the full new text"),
    schema("delete_file", "Delete a file from the workspace.",
           name="file name"),
]


# ---- Guardrails ----

def approve(action):
    answer = input(f"  Agent wants to {action}. Allow? [y/n] ")
    return answer.strip().lower() == "y"

def log(step, tool, args, result):
    with open(LOG, "a") as f:
        entry = {"time": time.strftime("%H:%M:%S"), "step": step,
                 "tool": tool, "args": args, "result": result[:80]}
        f.write(json.dumps(entry) + "\n")


# ---- The loop ----

def chat(messages):
    body = {"model": MODEL, "messages": messages, "tools": TOOL_SCHEMAS,
            "stream": False, "options": {"temperature": 0}}
    req = urllib.request.Request(f"{OLLAMA}/api/chat", json.dumps(body).encode(),
                                 {"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req))["message"]

def run(task):
    messages = [{"role": "system", "content": SYSTEM},
                {"role": "user", "content": task}]
    max_steps = int(os.environ.get("MAX_STEPS", 6 if SAFE else 50))
    for step in range(1, max_steps + 1):
        msg = chat(messages)
        messages.append(msg)
        if not msg.get("tool_calls"):
            return msg["content"]  # no tool requested: the job's done
        for call in msg["tool_calls"]:
            name, args = call["function"]["name"], call["function"]["arguments"]
            shown = ", ".join(f"{k}={v!r}" for k, v in args.items()
                              if k != "content")
            print(f"step {step}  {name}({shown})")
            try:
                result = TOOLS[name](**args)
            except Exception as e:
                result = f"error: {e}"
            log(step, name, args, result)
            messages.append({"role": "tool", "content": result})
    return "Stopped: step limit reached."


# ---- Commands: run, reset, restore ----

def reset():
    shutil.rmtree(WORK, ignore_errors=True)
    shutil.rmtree(TRASH, ignore_errors=True)
    shutil.copytree(os.path.join(HERE, "workspace_seed"), WORK)
    if os.path.exists(LOG):
        os.remove(LOG)
    print("workspace reset:")
    for name in sorted(os.listdir(WORK)):
        print("  " + name)

def restore(only=None):
    for name in sorted(os.listdir(TRASH)) if os.path.isdir(TRASH) else []:
        if only and name != only:
            continue
        shutil.move(os.path.join(TRASH, name), safe_path(name))
        print(f"restored {name}")

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "run":
        print("\n" + run(sys.argv[2]))
    elif cmd == "reset":
        reset()
    elif cmd == "restore":
        restore(sys.argv[2] if len(sys.argv) > 2 else None)
    else:
        print('usage: agent.py run "task" [--safe] | reset | restore [file]')
