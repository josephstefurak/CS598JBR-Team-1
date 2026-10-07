import ast
import json
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

import jsonlines

#####################################################
# Please finish all TODOs in this file for MP2;
#####################################################

SYSTEM_PROMPT = (
    "You are an AI programming assistant. You are an AI programming assistant, utilizing the "
    "DeepSeek Coder model, developed by DeepSeek Company, and you only answer questions related "
    "to computer science. For politically sensitive questions, security and privacy issues, and "
    "other non-computer science questions, you will refuse to answer."
)

# Folders (relative to MP2/, where commands.py runs this script)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
COVERAGE_DIR = os.path.join(SCRIPT_DIR, "Coverage")
GENERATED_DIR = os.path.join(SCRIPT_DIR, "generated_tests")

PYTEST_TIMEOUT_SECONDS = 120


def save_file(content, file_path):
    with open(file_path, 'w') as file:
        file.write(content)


def module_name_for(task_id):
    """'HumanEval/133' -> 'HumanEval_133' (a valid Python module / file name)."""
    return task_id.replace("/", "_")


def full_program(entry):
    """The complete program under test: signature + docstring (prompt) + body (canonical_solution)."""
    return entry["prompt"] + entry["canonical_solution"]


def strip_docstrings(code):
    """Return the code without docstrings (used for the vanilla prompt, matching the MP2 example)."""
    tree = ast.parse(code)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module)):
            body = node.body
            if body and isinstance(body[0], ast.Expr) and isinstance(getattr(body[0], "value", None), ast.Constant) \
                    and isinstance(body[0].value.value, str):
                node.body = body[1:] or [ast.Pass()]
    return ast.unparse(tree)


def build_prompt(entry, vanilla):
    program = full_program(entry)
    module = module_name_for(entry["task_id"])
    entry_point = entry["entry_point"]

    if vanilla:
        # Vanilla prompt: the example from the MP2 description, code only.
        instruction = (
            "Generate a pytest test suite for the following code.\n"
            "Only write unit tests in the output and nothing else.\n"
            f"{strip_docstrings(program)}"
        )
    else:
        # Crafted prompt: give the full specification (docstring), the import path, and
        # explicit guidance on deriving expected values and covering every branch.
        instruction = f"""Generate a pytest test suite for the function `{entry_point}` below.

The code is saved in a module named `{module}`. Start the test file with:
from {module} import *

Follow these steps:
1. Read the docstring carefully. It is the specification: every example in it must become a test with exactly the expected value it states.
2. Go through the code line by line and list every branch (each if/elif/else, loop, early return, and edge case such as empty input, a single element, zero, negative numbers, and boundary values).
3. Write at least one test for every branch you listed, so that together the tests execute every line of the code.
4. Compute each expected value by tracing the code by hand for that input. Do not guess. Only test inputs that the specification allows; do not test invalid types or inputs that the code is not designed to handle.

Rules for the output:
- Output a single ```python code block containing only the test file.
- Do not copy or redefine `{entry_point}` or any other function from the code; import them as shown above.
- Write each test as a separate function whose name starts with `test_`, with a short descriptive name.

The code:
```python
{program.strip()}
```"""

    return f"{SYSTEM_PROMPT}\n### Instruction:\n{instruction}\n### Response:\n"


def extract_test_code(response):
    """Pull the test code out of the model's response (handles markdown fences and prose)."""
    blocks = re.findall(r"```(?:python|py)?[ \t]*\n(.*?)```", response, re.DOTALL)
    if not blocks:
        # Unterminated fence (e.g., response cut off by the token limit)
        unterminated = re.search(r"```(?:python|py)?[ \t]*\n(.*)", response, re.DOTALL)
        blocks = [unterminated.group(1)] if unterminated else [response]
    # Prefer blocks that actually contain tests; join them if the model split the suite up
    test_blocks = [b for b in blocks if "def test" in b or "class Test" in b]
    return "\n\n".join(test_blocks or blocks).strip() + "\n"


def make_parsable(code):
    """If the code was cut off mid-test, drop trailing lines until it parses."""
    lines = code.split("\n")
    while lines:
        candidate = "\n".join(lines)
        try:
            ast.parse(candidate)
            return candidate
        except SyntaxError:
            lines.pop()
    return code


def prepare_test_file(test_code, entry):
    """Post-process the test code so it tests the real module:
    - drop any copy of the program's functions the model pasted in (otherwise the tests
      exercise the copy, and the module's coverage stays at 0%)
    - drop imports of the program's functions from a placeholder module the model made up
      (e.g. `from your_module import fizz_buzz`), which would fail with ModuleNotFoundError
    - make sure the module under test is imported
    """
    module = module_name_for(entry["task_id"])
    program_functions = {
        node.name for node in ast.parse(full_program(entry)).body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }

    def is_wrong_import(node):
        # `from your_module import f` where f is one of the program's functions
        if isinstance(node, ast.ImportFrom) and node.module != module:
            return any(alias.name in program_functions or alias.name == "*" and node.module
                       and "module" in node.module for alias in node.names)
        # `import your_module`
        if isinstance(node, ast.Import):
            return any("your_module" in alias.name for alias in node.names)
        return False

    test_code = make_parsable(test_code)
    try:
        tree = ast.parse(test_code)
        tree.body = [
            node for node in tree.body
            if not (isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in program_functions)
            and not is_wrong_import(node)
        ]
        test_code = ast.unparse(tree)
    except SyntaxError:
        pass  # leave it as is; pytest will report the collection error

    header = ""
    if "import pytest" not in test_code:
        header += "import pytest\n"
    if not re.search(rf"^\s*(from {module} import|import {module})", test_code, re.MULTILINE):
        header += f"from {module} import *\n"
    return header + "\n" + test_code + "\n"


def run_tests_with_coverage(entry, test_code, mode):
    """Write {ID}.py and {ID}_test.py, run pytest with coverage, and return the results."""
    module = module_name_for(entry["task_id"])
    work_dir = os.path.join(GENERATED_DIR, mode)
    os.makedirs(work_dir, exist_ok=True)
    os.makedirs(COVERAGE_DIR, exist_ok=True)

    save_file(full_program(entry), os.path.join(work_dir, f"{module}.py"))
    test_file = f"{module}_test.py"
    save_file(test_code, os.path.join(work_dir, test_file))

    coverage_report = os.path.join(COVERAGE_DIR, f"{module}_test_{mode}.json")
    junit_report = os.path.join(work_dir, f"{module}_junit.xml")
    for stale in (coverage_report, junit_report, os.path.join(work_dir, ".coverage")):
        if os.path.exists(stale):
            os.remove(stale)

    cmd = [
        sys.executable, "-m", "pytest", test_file,
        f"--cov={module}", f"--cov-report=json:{coverage_report}",
        f"--junitxml={junit_report}", "-q", "-p", "no:cacheprovider",
    ]
    try:
        proc = subprocess.run(cmd, cwd=work_dir, capture_output=True, text=True, timeout=PYTEST_TIMEOUT_SECONDS)
        pytest_output = proc.stdout + proc.stderr
    except subprocess.TimeoutExpired:
        pytest_output = f"pytest timed out after {PYTEST_TIMEOUT_SECONDS} seconds"

    # Coverage percentage (0 if the tests could not run at all)
    coverage = 0.0
    if os.path.exists(coverage_report):
        with open(coverage_report) as f:
            coverage = round(json.load(f)["totals"]["percent_covered"], 2)
    else:
        # Still produce the required report file so all 40 reports exist
        save_file(json.dumps({"totals": {"percent_covered": 0.0}, "note": "tests could not run"}), coverage_report)

    # Test counts from the JUnit report
    counts = {"tests_total": 0, "tests_passed": 0, "tests_failed": 0, "tests_errored": 0, "tests_skipped": 0}
    if os.path.exists(junit_report):
        root = ET.parse(junit_report).getroot()
        suite = root if root.tag == "testsuite" else root.find("testsuite")
        if suite is not None:
            total = int(suite.get("tests", 0))
            failed = int(suite.get("failures", 0))
            errored = int(suite.get("errors", 0))
            skipped = int(suite.get("skipped", 0))
            counts = {
                "tests_total": total,
                "tests_passed": total - failed - errored - skipped,
                "tests_failed": failed,
                "tests_errored": errored,
                "tests_skipped": skipped,
            }

    return coverage, counts, pytest_output


def load_model(model_name):
    import torch
    from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig

    # TODO: download the model
    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    # TODO: load the model with quantization
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
    )
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        quantization_config=bnb_config,
        device_map="auto",
        torch_dtype=torch.bfloat16,
        trust_remote_code=True,
    )
    return tokenizer, model


def generate(tokenizer, model, prompt, max_new_tokens=1024):
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
    outputs = model.generate(
        **inputs,
        max_new_tokens=max_new_tokens,
        do_sample=False,  # greedy decoding (temperature 0) for reproducibility
        eos_token_id=tokenizer.eos_token_id,
        pad_token_id=tokenizer.eos_token_id,
    )
    return tokenizer.decode(outputs[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)


def prompt_model(dataset, model_name = "deepseek-ai/deepseek-coder-6.7b-instruct", vanilla = True):
    print(f"Working with {model_name} prompt type {vanilla}...")
    mode = "vanilla" if vanilla else "crafted"

    tokenizer, model = load_model(model_name)

    results = []
    for entry in dataset:
        # TODO: create prompt for the model
        prompt = build_prompt(entry, vanilla)

        # TODO: prompt the model and get the response
        try:
            response = generate(tokenizer, model, prompt)
        except Exception as e:
            response = ""
            print(f"Generation failed for {entry['task_id']}: {e}")

        # TODO: process the response, generate coverage and save it to results
        test_code = prepare_test_file(extract_test_code(response), entry)
        coverage, counts, pytest_output = run_tests_with_coverage(entry, test_code, mode)

        print(f"Task_ID {entry['task_id']}:\nprompt:\n{prompt}\nresponse:\n{response}\n"
              f"processed test file:\n{test_code}\npytest output:\n{pytest_output}\n"
              f"tests: {counts}\ncoverage:\n{coverage}\n")
        results.append({
            "task_id": entry["task_id"],
            "prompt": prompt,
            "response": response,
            "coverage": coverage,
            **counts,
        })

    return results

def read_jsonl(file_path):
    dataset = []
    with jsonlines.open(file_path) as reader:
        for line in reader: 
            dataset.append(line)
    return dataset

def write_jsonl(results, file_path):
    with jsonlines.open(file_path, "w") as f:
        for item in results:
            f.write_all([item])

if __name__ == "__main__":
    """
    This Python script is to run prompt LLMs for code synthesis.
    Usage:
    `python3 task_2.py <input_dataset> <model> <output_file> <if_vanilla>`|& tee prompt.log

    Inputs:
    - <input_dataset>: A `.jsonl` file, which should be your team's dataset containing 20 HumanEval problems.
    - <model>: Specify the model to use. Options are "deepseek-ai/deepseek-coder-6.7b-base" or "deepseek-ai/deepseek-coder-6.7b-instruct".
    - <output_file>: A `.jsonl` file where the results will be saved.
    - <if_vanilla>: Set to 'True' or 'False' to enable vanilla prompt
    
    Outputs:
    - You can check <output_file> for detailed information.
    """
    args = sys.argv[1:]
    input_dataset = args[0]
    model = args[1]
    output_file = args[2]
    if_vanilla = args[3] # True or False
    
    if not input_dataset.endswith(".jsonl"):
        raise ValueError(f"{input_dataset} should be a `.jsonl` file!")
    
    if not output_file.endswith(".jsonl"):
        raise ValueError(f"{output_file} should be a `.jsonl` file!")
    
    vanilla = True if if_vanilla == "True" else False
    
    dataset = read_jsonl(input_dataset)
    results = prompt_model(dataset, model, vanilla)
    write_jsonl(results, output_file)
