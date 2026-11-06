# Stage 3
from appworld import AppWorld
from openai import OpenAI
import json, os, time, sys
import yaml

with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.yaml"), encoding="utf-8") as f:
    CFG = yaml.safe_load(f)

experiment_name = "llm_agent_3"
client = OpenAI(
    api_key=os.environ["GEMINI_API_KEY"],
    base_url=CFG["base_url"],
)
MODEL = CFG["model"]
    
ALLOWED_APPS = {"supervisor", "spotify"}
MAX_LLM_CALLS = CFG["max_llm_calls"]
MAX_API_CALLS = CFG["max_api_calls"]
SEPARATOR = "__"
# TRAIN_TASK_IDS = ["b7a9ee9_3", "ce359b5_2", "692c77d_2", "b0a8eae_2", "22cc237_2", "29caf6f_3", "22cc237_2", "229360a_3", ""]
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "app_func_list",
            "description": "List the functions of one app: name and one-line description.",
            "parameters": {"type": "object",
                           "properties": {"app": {"type": "string"}},
                           "required": ["app"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "call_function",
            "description": "Call an app function. 'args' is a JSON object encoded as a string.",
            "parameters": {"type": "object",
                           "properties": {"name": {"type": "string"}, "args": {"type": "string", "description": "JSON object, e.g. {\"id\": 1}"}},
                           "required": ["name"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_func_doc",
            "description": "Get the full documentation (parameters, types, required fields) of one function.",
            "parameters": {"type": "object",
                           "properties": {"name": {"type": "string", "description": "Full function name."}},
                           "required": ["name"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "Get the current date and time in this world. Use it to resolve words like today, yesterday, this week.",
            "parameters": {"type": "object",
                           "properties": {}}
        }
    }
]
GATE_MSG = ("Error: read the documentation of supervisor__complete_task with get_func_doc before calling it. ")

AppWorld.init_defaults.include_direct_functions = True
AppWorld.init_defaults.direct_function_separator = SEPARATOR

SYSTEM = ("You are an agent that carries out the user's tasks by calling app functions. "
          "App functions are called only through call_function(name, args); app_func_list and get_func_doc are separate tools. "
          "Take all data only from function responses, do not make anything up, and copy IDs from the responses. "
          "If you need credentials or other data to log in to an app, find them using the available functions; never guess or invent passwords or other credentials. "
          "When several calls do not depend on each other's results, you can request them together in one step. "
          "Calls that need a result of another call must wait for it. "
          "Lists are returned in pages. If a call returns as many items as page_limit, there may be more: request the next page_index until a page has fewer items than page_limit. "
          "Follow each function's documentation exactly: use only the parameters it lists, and pass optional parameters only when the task needs them. "
          "Read a function's documentation with get_func_doc before calling it for the first time. "
          "When the task is done, finish it by calling the task-completion function.")

def catalog(world):
    d = dict(world.task.app_descriptions)
    d.pop("api_docs", None)
    return json.dumps(d, ensure_ascii=False, indent=1)

def build_docs(world):
    return {d["function"]["name"]: d["function"] for d in world.task.api_docs.function_calling()}

def app_func_list(docs, app_name):
    lines = [f"{n}: {(f.get('description') or '').strip()}" for n, f in docs.items() if n.split(SEPARATOR)[0] == app_name]
    if not lines:
        apps = sorted({n.split(SEPARATOR)[0] for n in docs})
        return f"Error: unknown app '{app_name}'. Available apps: {apps}"
    return "\n".join(lines)

def get_func_doc(docs, f_name, seen_before_complete_docs):
    f = docs.get(f_name)
    seen_before_complete_docs.add(f_name)
    if f is None:
        return f"Error: unknown function '{f_name}'. Use app_func_list to see real names."
    return json.dumps(f, ensure_ascii=False)

def get_current_time(world):
    return str(world.execute("print(apis.phone.get_current_date_and_time())"))

def normalize(raw):
    try:
        d = json.loads(raw or "{}")
    except json.JSONDecodeError:
        return raw
    if isinstance(d, dict) and isinstance(d.get("args"), str):
        try:
            d["args"] = json.loads(d["args"] or "{}")
        except json.JSONDecodeError:
            pass
    return d 

def check_repeat(logs, fn_name, fn_args):
    n = 0
    if fn_name == "call_function":
        target = normalize(fn_args)
        for log in logs:
            if (log.get("call") == "call_function" and target == normalize(log.get("args"))) and log.get("result").startswith(("Error", "Execution failed")) and log.get("result") != GATE_MSG:
                n += 1
    return n

def check_args(docs, fn_name, fn_args):
    params = docs[fn_name].get("parameters", {})
    props = params.get("properties", {})
    required = params.get("required", [])
    unknown = [k for k in fn_args if k not in props]
    missing = [k for k in required if k not in fn_args]
    if unknown or missing:
        parts = []
        if unknown:
            parts.append(f"unknown parameters {unknown}")
        if missing:
            parts.append(f"missing required parameters {missing}")
        return (f"Error: {'; '.join(parts)}. "
                f"Allowed parameters of {fn_name}: {list(props)}.")
    return None

def page_info(docs, fn_name, fn_args):
    props = docs[fn_name].get("parameters", {}).get("properties", {})
    if "page_index" in props and "page_limit" in props:
        limit = fn_args.get("page_limit", props["page_limit"].get("default"))
        return limit
    return None

def execute_tool(world, docs, name, raw_args, seen_before_complete_docs):
    try:
        args = json.loads(raw_args or "{}")
    except json.JSONDecodeError:
        return "Error: arguments are not valid JSON."
    if name == "app_func_list":
        return app_func_list(docs, args.get("app", ""))
    if name == "get_func_doc":
        return get_func_doc(docs, args.get("name", ""), seen_before_complete_docs)
    if name == "get_current_time":
        return get_current_time(world)
    if name == "call_function":
        fn = args.get("name", "")

        if fn not in docs:
            return (f"Error: '{fn}' is not an app function. Find names with app_func_list; "
                    "app_func_list and get_func_doc are separate tools.")

        if fn == f"supervisor{SEPARATOR}complete_task" and fn not in seen_before_complete_docs:
            return GATE_MSG
        
        try:
            fn_args = args.get("args", {})
            if isinstance(fn_args, str):
                fn_args = json.loads(fn_args or "{}")
            if not isinstance(fn_args, dict):
                return "Error: 'args' must be a JSON object."
        except json.JSONDecodeError:
            return "Error: 'args' must be a JSON object string."

        err = check_args(docs, fn, fn_args)
        if err:
           return err
        
        out = world.execute(f"print({fn}(**{fn_args!r}))")

        limit = page_info(docs, fn, fn_args)
        if limit is not None:
            try:
                items = json.loads(out)
            except json.JSONDecodeError:
                return out

            if len(items) == limit:
                return out + f"\n[Note: the page is full ({limit} items), there may be more. Request next page.]"

        return str(out)
    return f"Error: unknown tool '{name}'. Available tools: app_func_list, get_func_doc, call_function, get_current_time."

def run_task(task, path):
    stop = "max_llm_calls"
    log = []
    seen_before_complete_docs = set()
    with AppWorld(task_id=task, experiment_name=experiment_name) as world:
        task_ins = world.task.instruction
        docs = build_docs(world)
        log.append({"instruction": task_ins})
        api_calls = 0
        messages = [
            {"role": "system", "content": SYSTEM + "\n\nAvailable apps:\n" + catalog(world)},
            {"role": "user", "content": task_ins},
        ]
        for step in range(MAX_LLM_CALLS):
            resp = client.chat.completions.create(model=MODEL, messages=messages, tools=TOOLS, temperature=CFG.get("temperature"))
            msg = resp.choices[0].message
            messages.append(msg)
            log.append({"step": step, "text": msg.content, "usage": resp.usage.model_dump() if resp.usage else None})

            if not msg.tool_calls:
                messages.append({"role": "user", "content": "Call a function or complete the task."})
                continue

            done = False
            for tc in msg.tool_calls:
                count_of_repeat = check_repeat(log, tc.function.name, tc.function.arguments)
                if count_of_repeat >= 1:
                    result = ("Error: you already made this exact call and it did not help. "
                              "Change the arguments or use another function.")
                else:
                    result = execute_tool(world, docs, tc.function.name, tc.function.arguments, seen_before_complete_docs)

                if tc.function.name == "call_function":
                    api_calls += 1
                    try:
                        inner = json.loads(tc.function.arguments or "{}").get("name")
                    except json.JSONDecodeError:
                        inner = None
                    if inner == f"supervisor{SEPARATOR}complete_task" and not result.startswith(("Error", "Execution failed")):
                        done = True
                messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})
                log.append({"step": step, "call": tc.function.name, "args": tc.function.arguments, "result": result})
            if done:
                stop = "completed"
                break
            if api_calls >= MAX_API_CALLS:
                stop = "max_api_calls"
                break

            time.sleep(CFG.get("sleep_between_steps", 4))
        report = world.evaluate()
    os.makedirs("runs", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"task_id": task, "stop": stop, "log": log, "success": bool(report.success), "failures": report.failures}, f, ensure_ascii=False, indent=2)
    print(report)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Использование: python agent_3.py <task_id>")
    task = sys.argv[1]
    out = f"runs/single_B/{task}.json"
    os.makedirs(os.path.dirname(out), exist_ok=True)
    run_task(task, out)