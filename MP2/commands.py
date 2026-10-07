###################################################################
# This is a list of all commands you need to run for MP2 on Colab.
# Run each section as a separate cell on a T4 GPU runtime.
###################################################################

# ---------------- Cell 1: setup ----------------
# Always start from /content so reruns don't create nested clones
%cd /content

# TODO: Clone your GitHub repository
! git clone https://github.com/josephstefurak/CS598JBR-Team-1
%cd /content/CS598JBR-Team-1
! git pull
%cd MP2

# TODO: Replace the file path of selected_humaneval_[seed].jsonl generated in MP1
# (the validator also requires this file inside MP2/)
! cp ../MP1/selected_humaneval_207031459373254362480952325552707923931.jsonl .
input_dataset = "selected_humaneval_207031459373254362480952325552707923931.jsonl"

# Set up requirements for model prompting
! bash -x setup_models.sh

# TODO: add your seed generated in MP1
seed = "207031459373254362480952325552707923931"
task_1_vanilla_json = "task_1_" + seed + "_vanilla.jsonl"
task_1_crafted_json = "task_1_" + seed + "_crafted.jsonl"
task_2_vanilla_json = "task_2_" + seed + "_vanilla.jsonl"
task_2_crafted_json = "task_2_" + seed + "_crafted.jsonl"

! pip install -q pytest-timeout

# ---------------- Cell 2: Task 1 (code execution reasoning) ----------------
# Prompt the models, you can modify `MP2/task_1.py, MP2/task_2.py`
# The {input_dataset} is the JSON file consisting of 20 unique programs for your group that you generated in MP1 (selected_humaneval_[seed].jsonl)
! python3 task_1.py {input_dataset} "deepseek-ai/deepseek-coder-6.7b-instruct" {task_1_vanilla_json} "True" |& tee task_1_vanilla.log
! python3 task_1.py {input_dataset} "deepseek-ai/deepseek-coder-6.7b-instruct" {task_1_crafted_json} "False" |& tee task_1_crafted.log

# ---------------- Cell 3: Task 2 (test generation) ----------------
# Commands to generate coverage reports:
# task_2.py runs `pytest {ID}_test.py --cov {ID} --cov-report json:Coverage/{ID}_test_{vanilla/crafted}.json`
# for every problem and saves the 40 reports under MP2/Coverage/
! python3 task_2.py {input_dataset} "deepseek-ai/deepseek-coder-6.7b-instruct" {task_2_vanilla_json} "True" |& tee task_2_vanilla.log
! python3 task_2.py {input_dataset} "deepseek-ai/deepseek-coder-6.7b-instruct" {task_2_crafted_json} "False" |& tee task_2_crafted.log
! ls Coverage | wc -l   # should be 41 (40 reports + README.md)

# ---------------- Cell 4: push results ----------------
# git push all necessary files (e.g., *jsonl, *log) to your GitHub repository
# (GITHUB_TOKEN is stored in Colab Secrets, not in the notebook)
from google.colab import userdata
token = userdata.get('GITHUB_TOKEN')

%cd /content/CS598JBR-Team-1
! git config user.email "your_github_email@example.com"
! git config user.name "Your Name"
! git add MP2
! git commit -m "Add MP2 results"
! git pull --rebase https://{token}@github.com/josephstefurak/CS598JBR-Team-1.git main
! git push https://{token}@github.com/josephstefurak/CS598JBR-Team-1.git main
