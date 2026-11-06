from agent_3 import run_task
import os
# "37a8675_1", "0d8a4ee_3", "50e1ac9_1", "b119b1f_2", "530b157_1", "fac291d_1", "4fab96f_2", "6c2c621_3", "0d8a4ee_1", "4fab96f_3"
DEV_TASK = ["37a8675_1", "0d8a4ee_3", "50e1ac9_1", "b119b1f_2", "530b157_1", "fac291d_1", "4fab96f_2", "6c2c621_3", "0d8a4ee_1", "4fab96f_3"]

os.makedirs(f"runs/dev_experiment_2", exist_ok=True)
for t_id in DEV_TASK:
    out = f"runs/dev_experiment_2/{t_id}.json"
    run_task(t_id, out)
