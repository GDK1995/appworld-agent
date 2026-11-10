import yaml
import os, json
from test_normal import test_sample
import agent_3 as agent
import agent_2 as base

with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.yaml"), encoding="utf-8") as f:
    CFG = yaml.safe_load(f)

MAX_TOKEN = CFG["budget_max_total_tokens"]

def usage_of(path):
    r = json.load(open(path))
    used = [log["usage"] for log in r["log"] if log.get("usage")]
    return sum(u["total_tokens"] for u in used)

def main():
    test_sample()
    tasks = json.load(open("test_tasks.json"))["tasks"]

    out_dir_agent = f"runs/exp/A_3"
    os.makedirs(out_dir_agent, exist_ok=True)

    used_tokens = 0

    for task in tasks:
        out = f"{out_dir_agent}/{task}.json"
        if used_tokens > MAX_TOKEN:
            print("Budget exhausted, stopping.")
            break
        base.run_task(task, out)
        tokens = usage_of(out)
        used_tokens += tokens

if __name__ == "__main__":
    main()