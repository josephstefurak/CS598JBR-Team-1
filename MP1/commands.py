###################################################################
# This is a list of all commands you need to run for MP1 on Colab.
###################################################################
%cd /content

NetIDs = ["joseph93", "jtrader3", "rossam2"]
NetIDs_str = " ".join(NetIDs)

! git clone https://github.com/josephstefurak/CS598JBR-Team-1
%cd CS598JBR-Team-1

# Set up requirements for dataset generation
! bash -x MP1/setup_dataset.sh

# Fixes for newer Colab environment (Python 3.13):
# human-eval's setup.py needs pkg_resources (removed in setuptools 81+) and its entry point lacks ":main";
# huggingface_hub 1.x rejects the "openai_humaneval" dataset name
! pip install -q "setuptools<81" "huggingface_hub>=0.34,<1.0"
! sed -i 's/human_eval.evaluate_functional_correctness"/human_eval.evaluate_functional_correctness:main"/' human-eval/setup.py
! pip install -q --no-build-isolation ./human-eval
! cp -r human-eval/data "$(python3 -c 'import human_eval, os; print(os.path.dirname(os.path.dirname(human_eval.__file__)))')/"

# dataset generation
! python3 MP1/dataset_generation.py {NetIDs_str} |& tee dataset_generation.log