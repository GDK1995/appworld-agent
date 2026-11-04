# STAGE 1.4
# source .venv/bin/activate
# python agent.py ce359b5_2
from appworld import AppWorld
from openai import OpenAI
import json, os, time, sys

experiment_name = "llm_agent"
client = OpenAI(
    api_key=os.environ["GEMINI_API_KEY"],
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
)
MODEL = "gemini-3.5-flash-lite"

ALLOWED_APPS = {"supervisor", "spotify"}
MAX_LLM_CALLS = 30
MAX_API_CALLS = 100
SEPARATOR = "__"
# TASK_IDS = ["b7a9ee9_3", "ce359b5_2", "692c77d_2"]

AppWorld.init_defaults.include_direct_functions = True
AppWorld.init_defaults.direct_function_separator = SEPARATOR

SYSTEM = ("You are an agent that carries out the user's tasks by calling app functions. "
          "Take all data only from function responses, do not make anything up, and copy IDs from the responses. "
          "If you need credentials or other data to log in to an app, find them using the available functions. "
          "When the task is done, finish it by calling the task-completion function.")

def build_tools(world):
    tools = []
    for d in world.task.api_docs.function_calling():
        if d["function"]["name"].split(SEPARATOR)[0] in ALLOWED_APPS:
            tools.append(d)
    return tools

def execute_tool(world, name, raw_args):
    if name.count(SEPARATOR) != 1:
        return f"Error: unknown function '{name}'."
    try:
        args = json.loads(raw_args or "{}")
    except json.JSONDecodeError:
        return "Error: arguments are not valid JSON."
    out = world.execute(f"print({name}(**{args!r}))")
    return str(out)

def run_task(task):
    stop = "max_llm_calls"
    log = []
    with AppWorld(task_id=task, experiment_name=experiment_name) as world:
        tools = build_tools(world)
        task_ins = world.task.instruction
        log.append({"instruction": task_ins})
        api_calls = 0
        messages = [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": task_ins},
        ]
        for step in range(MAX_LLM_CALLS):
            resp = client.chat.completions.create(model=MODEL, messages=messages, tools=tools, temperature=0)
            msg = resp.choices[0].message
            messages.append(msg)
            log.append({"step": step, "text": msg.content, "usage": resp.usage.model_dump() if resp.usage else None})

            if not msg.tool_calls:
                messages.append({"role": "user", "content": "Call a function or complete the task."})
                continue

            done = False
            for tc in msg.tool_calls:
                api_calls +=1
                result = execute_tool(world, tc.function.name, tc.function.arguments)
                messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})
                log.append({"step": step, "call": tc.function.name, "args": tc.function.arguments, "result": result})
                if tc.function.name == f"supervisor{SEPARATOR}complete_task":
                    done = True

            if done:
                stop = "completed"; break
            if api_calls >= MAX_API_CALLS:
                stop = "max_api_calls"; break

            time.sleep(4)

        report = world.evaluate()
    os.makedirs("runs", exist_ok=True)
    with open(f"runs/{task}.json", "w", encoding="utf-8") as f:
        json.dump({"task_id": task, "stop": stop, "log": log,
                   "report": str(report)}, f, ensure_ascii=False, indent=2)
    print(task, "stop:", stop); print(report)

# def run_all():
#     for task in TASK_IDS:
#         run_task(task)

if __name__ == "__main__":
    run_task(sys.argv[1])