# get tast samples from test_normal
import json, random, os
from collections import defaultdict
from appworld import load_task_ids
import yaml

with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.yaml"), encoding="utf-8") as f:
    CFG = yaml.safe_load(f)
    
ids = load_task_ids("test_normal")
seed = CFG["seed"]

def test_sample():
    groups = defaultdict(list)
    for t in ids:
        groups[t.rsplit("_", 1)[0]].append(t)

    full = sorted(s for s, g in groups.items() if len(g) == 3)
    rng = random.Random(seed)
    chosen = sorted(rng.sample(full, 5))
    tasks = [t for s in chosen for t in sorted(groups[s])]

    with open("test_tasks.json", "w", encoding="utf-8") as f:
        json.dump({"split": "test_normal", "seed": seed,
                   "scenarios": chosen, "tasks": tasks}, f, indent=2)
