###################################################################
# This is a list of all commands you need to run for MP3 on Colab.
# Run each section as a separate cell on a T4 GPU runtime.
###################################################################

# ---------------- Cell 1: clone the repository ----------------
%cd /content

# Clone your GitHub repository
! git clone https://github.com/josephstefurak/CS598JBR-Team-1
%cd /content/CS598JBR-Team-1/MP3
! git pull --rebase

# Seed generated in MP1
seed = "207031459373254362480952325552707923931"

humaneval_input_dataset = "selected_humaneval_" + seed + ".jsonl"

# ---------------- Cell 2: setup ----------------
# Set up requirements for dataset generation
! bash -x setup_dataset.sh

# Set up requirements for model prompting
! bash -x setup_models.sh

# Re-create our team's MP1 dataset (selected_humaneval_[seed].jsonl) in this folder
NetIDs = ["joseph93", "jtrader3", "rossam2"]
NetIDs_str = " ".join(NetIDs)
! python3 dataset_generation.py {NetIDs_str} |& tee dataset_generation.log

# ---------------- Cell 3: Task 1 (code translation, Python -> Java) ----------------

# The {humaneval_input_dataset} is the JSON file consisting of 20 unique programs for your group that you generated in MP1 (selected_humaneval_[seed].jsonl)
! python3 humanevalx_dataset_generation.py {humaneval_input_dataset} |& tee humanevalx_dataset_generation.log

input_python_dataset = "selected_humanevalx_python_" + seed + ".jsonl"
input_java_dataset = "selected_humanevalx_java_" + seed + ".jsonl"

# JUnit standalone jar on the javac classpath used by task_1.py to compile and run the translated code
! rm -f junit-platform-console-standalone.jar
! wget -O junit-platform-console-standalone.jar https://repo.maven.apache.org/maven2/org/junit/platform/junit-platform-console-standalone/1.11.4/junit-platform-console-standalone-1.11.4.jar

task_1_vanilla_jsonl = "task_1_" + seed + "_vanilla.jsonl"
task_1_crafted_jsonl = "task_1_" + seed + "_crafted.jsonl"

! python3 task_1.py {input_python_dataset} {input_java_dataset} "deepseek-ai/deepseek-coder-6.7b-instruct" {task_1_vanilla_jsonl} "True" |& tee task_1_vanilla.log
! python3 task_1.py {input_python_dataset} {input_java_dataset} "deepseek-ai/deepseek-coder-6.7b-instruct" {task_1_crafted_jsonl} "False" |& tee task_1_crafted.log

# ---------------- Cell 4: Task 2 (bug detection) ----------------

# The {humaneval_input_dataset} is the JSON file consisting of 20 unique programs for your group that you generated in MP1 (selected_humaneval_[seed].jsonl)
! python3 humanevalpack_dataset_generation.py {humaneval_input_dataset} |& tee humanevalpack_dataset_generation.log

task_2_vanilla_json = "task_2_" + seed + "_vanilla.jsonl"
task_2_crafted_json = "task_2_" + seed + "_crafted.jsonl"
humanevalpack_input_dataset = "selected_humanevalpack_" + seed + ".jsonl"

# The crafted run uses the final two-stage prompt chain ("chain" variant, the default).
# Other variants can be selected with an optional 5th argument: "checklist" or "steps".
! python3 task_2.py {humanevalpack_input_dataset} "deepseek-ai/deepseek-coder-6.7b-instruct" {task_2_vanilla_json} "True" |& tee task_2_vanilla.log
! python3 task_2.py {humanevalpack_input_dataset} "deepseek-ai/deepseek-coder-6.7b-instruct" {task_2_crafted_json} "False" |& tee task_2_crafted.log

# Note: our submitted Task 2 results were produced before a fix to the verdict parser's
# fallback and were re-scored (responses unchanged) with:
#   python3 rescore_task_2.py {task_2_vanilla_json} task_2_vanilla.log
#   python3 rescore_task_2.py {task_2_crafted_json} task_2_crafted.log
# A fresh run with the current task_2.py does not need this step.

# ---------------- Cell 5: push results ----------------
# git push all necessary files (e.g., *jsonl, *log) to your GitHub repository
# (GITHUB_TOKEN is stored in Colab Secrets, not in the notebook)
from google.colab import userdata
token = userdata.get('GITHUB_TOKEN')

%cd /content/CS598JBR-Team-1
! git add MP3
! git commit -m "Add MP3 results"
! git pull --rebase https://{token}@github.com/josephstefurak/CS598JBR-Team-1.git main
! git push https://{token}@github.com/josephstefurak/CS598JBR-Team-1.git main
