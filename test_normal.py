import json, random
from collections import defaultdict
from appworld import load_task_ids

SEED = 42
ids = load_task_ids("test_normal")

groups = defaultdict(list)
for t in ids:
    groups[t.rsplit("_", 1)[0]].append(t)

full = sorted(s for s, g in groups.items() if len(g) == 3)
rng = random.Random(SEED)
chosen = sorted(rng.sample(full, 5))
tasks = [t for s in chosen for t in sorted(groups[s])]

with open("test_tasks.json", "w", encoding="utf-8") as f:
    json.dump({"split": "test_normal", "seed": SEED,
               "scenarios": chosen, "tasks": tasks}, f, indent=2)

print(tasks, len(tasks))
