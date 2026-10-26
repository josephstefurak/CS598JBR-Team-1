import re
import sys

import jsonlines

#####################################################
# Please finish all TODOs in this file for MP3/task_2;
#####################################################

SYSTEM_PROMPT = (
    "You are an AI programming assistant. You are an AI programming assistant utilizing the "
    "DeepSeek Coder model, developed by DeepSeek Company, and you only answer questions related "
    "to computer science. For politically sensitive questions, security and privacy issues, and "
    "other non-computer science questions, you will refuse to answer."
)

# Ground truth: every program in HumanEvalPack's `buggy_solution` field contains a bug.
EXPECTED_VERDICT = "buggy"


def save_file(content, file_path):
    with open(file_path, 'w') as file:
        file.write(content)


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------

def wrap(instruction):
    """DeepSeek-Coder-instruct prompt format."""
    return f"{SYSTEM_PROMPT}\n### Instruction:\n{instruction}\n### Response:\n"


def example_asserts(entry):
    """Expected-behavior examples taken from the dataset's `example_test` field
    (one `assert f(x) == y` per line, with the debugging messages removed)."""
    lines = []
    for line in entry.get("example_test", "").splitlines():
        line = line.strip()
        if not line.startswith("assert ") or line == "assert True" or line.startswith("assert True,"):
            continue
        # drop trailing assertion messages:  assert f(x) == y, "message"
        line = re.sub(r""",\s*(["']).*\1\s*$""", "", line)
        lines.append(line)
    return lines


# One correct and one buggy demonstration, so the in-context examples do not bias the
# model toward either answer. Neither problem (HumanEval/2, HumanEval/0) is in our dataset.
FEW_SHOT = '''Here are two examples of the analysis I want.

=== Example 1 ===
Specification and code:
```python
def truncate_number(number: float) -> float:
    """ Given a positive floating point number, it can be decomposed into
    an integer part (largest integer smaller than given number) and decimals
    (leftover part always smaller than 1).
    Return the decimal part of the number.
    >>> truncate_number(3.5)
    0.5
    """
    return number % 1.0
```
Examples of expected behavior:
assert truncate_number(3.5) == 0.5

Analysis:
Step 1 - Requirement: return only the fractional part of a positive float, a value in [0, 1).
Step 2 - Trace the examples:
- truncate_number(3.5): 3.5 % 1.0 = 0.5. Expected 0.5. MATCH.
Step 3 - Check each line: `number % 1.0` removes the integer part of a positive number and leaves the fractional part, which is always in [0, 1). This matches every requirement. Edge case: for a whole number such as 4.0 it returns 0.0, which is correct.
Step 4 - All examples match and no line contradicts the specification.
<start>Correct<end>

=== Example 2 ===
Specification and code:
```python
from typing import List

def has_close_elements(numbers: List[float], threshold: float) -> bool:
    """ Check if in given list of numbers, are any two numbers closer to each other than
    given threshold.
    >>> has_close_elements([1.0, 2.0, 3.0], 0.5)
    False
    >>> has_close_elements([1.0, 2.8, 3.0, 4.0, 5.0, 2.0], 0.3)
    True
    """
    for idx, elem in enumerate(numbers):
        for idx2, elem2 in enumerate(numbers):
            if idx != idx2:
                distance = elem - elem2
                if distance < threshold:
                    return True

    return False
```
Examples of expected behavior:
assert has_close_elements([1.0, 2.0, 3.0], 0.5) == False
assert has_close_elements([1.0, 2.8, 3.0, 4.0, 5.0, 2.0], 0.3) == True

Analysis:
Step 1 - Requirement: return True if two different elements are closer than `threshold`, i.e. |a - b| < threshold; otherwise False.
Step 2 - Trace the examples:
- has_close_elements([1.0, 2.0, 3.0], 0.5): first pair idx=0, idx2=1: distance = 1.0 - 2.0 = -1.0, and -1.0 < 0.5, so it returns True. Expected False. MISMATCH.
Step 3 - Check each line: the distance is computed as `elem - elem2` without abs(), so it can be negative and any pair where elem < elem2 is wrongly counted as close. The specification needs the absolute difference.
Step 4 - Example 1 does not match and the distance line contradicts the specification.
<start>Buggy<end>

=== Your task ===
'''


def build_prompt(entry, vanilla):
    if vanilla:
        # Vanilla prompt from the MP3 description: the code only (no docstring), plus the question.
        code = (entry["declaration"] + entry["buggy_solution"]).strip()
        instruction = (
            f"{code}\n\n"
            "Is the above code buggy or correct? Please explain your step by step reasoning. "
            "The prediction should be enclosed within <start> and <end> tags. "
            "For example: <start>Buggy<end>"
        )
        return wrap(instruction)

    # Crafted prompt, iteration 1 ('steps' variant; scored below vanilla, kept for the report):
    #  - include the specification (docstring) with the code, since bugs are only defined
    #    relative to the specification;
    #  - include concrete expected input/output pairs (`example_test`);
    #  - spell out each reasoning step (requirement -> trace examples -> line-by-line check ->
    #    decision rule) instead of just "think step by step";
    #  - two in-context examples, one Correct and one Buggy, to show the format without
    #    biasing the answer;
    #  - neutral wording: the prompt never says the code contains a bug.
    code = (entry["prompt"] + entry["buggy_solution"]).strip()
    asserts = example_asserts(entry)
    examples_block = (
        "Examples of expected behavior:\n" + "\n".join(asserts)
        if asserts else
        "Examples of expected behavior: use the examples in the docstring (if any)."
    )
    instruction = f"""You are reviewing a Python function against its specification. The specification is the docstring together with the examples of expected behavior. Decide whether the implementation is Correct (it satisfies the specification for every valid input) or Buggy (at least one valid input gives a result that differs from the specification).

Follow these steps exactly and write each one out:
Step 1 - Requirement: in one or two sentences, state precisely what the function must return according to the docstring.
Step 2 - Trace the examples: for each example of expected behavior (and each docstring example), execute the code by hand line by line, write down the value the code actually returns, compare it with the expected value, and write MATCH or MISMATCH. Compute the values carefully; do not assume the code is right.
Step 3 - Check each line: go through the code line by line and check every operator, comparison, constant, loop range, index, variable name, initial value and return value against the requirement. Also consider edge cases the docstring mentions (empty input, zero, negative numbers, boundaries).
Step 4 - Decide: answer Buggy if any example is a MISMATCH or any line contradicts the specification. Answer Correct only if every example matches and every line implements the specification.

End with exactly one verdict tag, either <start>Buggy<end> or <start>Correct<end>, and nothing after it.

{FEW_SHOT}Specification and code:
```python
{code}
```
{examples_block}

Now write the analysis for this function, starting with Step 1 and ending with the verdict tag."""
    return wrap(instruction)



# ---------------------------------------------------------------------------
# Crafted prompt, iteration 2 (default): two-stage prompt chain
#   Stage 1 - the model writes its own reference implementation from the docstring
#             only (it never sees the code under review), which is the task it is best at.
#   Stage 2 - the model compares the code under review with that reference, lists
#             behavioral differences, evaluates each difference on a concrete input,
#             and judges the outputs against the specification.
# ---------------------------------------------------------------------------

def build_reference_prompt(entry):
    instruction = (
        "Complete the following Python function so that it satisfies its docstring. "
        "Return the complete function (including any helper functions shown) in a single "
        "```python code block, with no explanation.\n"
        f"```python\n{entry['prompt'].strip()}\n```"
    )
    return wrap(instruction)


def extract_code(response):
    blocks = re.findall(r"```(?:python|py)?[ \t]*\n(.*?)```", response, re.DOTALL)
    if not blocks:
        m = re.search(r"```(?:python|py)?[ \t]*\n(.*)", response, re.DOTALL)
        blocks = [m.group(1)] if m else [response]
    return max(blocks, key=len).strip()


def build_compare_prompt(entry, reference_code):
    candidate = (entry["declaration"] + entry["buggy_solution"]).strip()
    asserts = example_asserts(entry)
    examples_block = ("Examples of expected behavior:\n" + "\n".join(asserts) + "\n\n") if asserts else ""
    instruction = f"""You are reviewing a candidate implementation of a Python function. Below are the specification (the docstring), a reference implementation that was written independently from the specification, and the candidate implementation. Decide whether the candidate is Buggy or Correct.

Specification:
```python
{entry["prompt"].strip()}
```
{examples_block}Reference implementation (written from the specification; it may itself contain mistakes):
```python
{reference_code}
```

Candidate implementation:
```python
{candidate}
```

Follow these steps and write each one out:
Step 1 - Differences: compare the candidate with the reference line by line. List every difference in operators (+, *, **, and/or, ==/!=, </<=), constants and initial values, loop ranges and slice bounds, which variable is used, conditions, return values, and statements that are missing or extra. Ignore differences that are only naming, formatting or style.
Step 2 - Effect: for each difference, choose a concrete valid input (prefer the examples above) and compute, step by step, what the candidate returns and what the reference returns.
Step 3 - Specification: for each input where the two results differ, state which result the specification requires. Trust the specification over the reference.
Step 4 - Decide: if the candidate returns a result that contradicts the specification for any valid input, the candidate is Buggy. If every difference is only stylistic, or the candidate agrees with the specification for all valid inputs, it is Correct.

End with exactly one verdict tag, <start>Buggy<end> or <start>Correct<end>, and nothing after it."""
    return wrap(instruction)


# ---------------------------------------------------------------------------
# Crafted prompt, iteration 3 (alternative): single prompt with a bug-pattern checklist
# and one worked demonstration; the model must compute (not copy) each actual output.
# ---------------------------------------------------------------------------

CHECKLIST_DEMO = """Example review:
```python
def has_close_elements(numbers, threshold):
    \"\"\" Check if in given list of numbers, are any two numbers closer to each other than
    given threshold.
    >>> has_close_elements([1.0, 2.0, 3.0], 0.5)
    False
    \"\"\"
    for idx, elem in enumerate(numbers):
        for idx2, elem2 in enumerate(numbers):
            if idx != idx2:
                distance = elem - elem2
                if distance < threshold:
                    return True
    return False
```
Requirement: True if two different elements satisfy |a - b| < threshold.
Checklist: operators - `elem - elem2` has no abs(), so the distance can be negative. Other items look fine.
Trace has_close_elements([1.0, 2.0, 3.0], 0.5): idx=0, idx2=1: distance = 1.0 - 2.0 = -1.0; -1.0 < 0.5 so the code returns True. The docstring expects False. MISMATCH.
<start>Buggy<end>
"""


def build_checklist_prompt(entry):
    code = (entry["prompt"] + entry["buggy_solution"]).strip()
    asserts = example_asserts(entry)
    examples_block = ("Examples of expected behavior:\n" + "\n".join(asserts) + "\n\n") if asserts else ""
    instruction = f"""Review the Python function below against its docstring and decide whether it is Buggy or Correct. Human-written bugs are usually small: a single wrong operator, constant, comparison, loop bound, variable, or a missing or extra line.

{CHECKLIST_DEMO}
Now review this function:
```python
{code}
```
{examples_block}Write out:
Requirement: one sentence stating exactly what the docstring requires.
Checklist: examine each of these in the code and say whether it matches the requirement - arithmetic operators and exponents; and/or and comparison operators; constants and initial values; range() bounds and slices (off-by-one); which variable is used in each expression; conditions that are missing or extra; the final return value (is anything missing, such as sorting or filtering?).
Trace: for each example above, execute the code by hand one statement at a time and write the value the CODE returns (do not copy the expected value), then compare it with the expected value and write MATCH or MISMATCH.
Verdict: Buggy if any checklist item is wrong or any trace is a MISMATCH; otherwise Correct. End with exactly one tag, <start>Buggy<end> or <start>Correct<end>."""
    return wrap(instruction)


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------

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
        do_sample=False,  # greedy decoding for reproducibility
        eos_token_id=tokenizer.eos_token_id,
        pad_token_id=tokenizer.eos_token_id,
    )
    return tokenizer.decode(outputs[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)


# ---------------------------------------------------------------------------
# Response processing
# ---------------------------------------------------------------------------

VERDICT_WORDS = r"(buggy|correct|incorrect|wrong)"
# An explicit verdict sentence, e.g. "The code is buggy", "the candidate is Buggy",
# "it is not Buggy", "The provided code is correct".
VERDICT_STATEMENT = re.compile(
    r"\b(?:code|candidate|implementation|function|program|it)\s+(?:is|seems to be|appears to be)\s+"
    r"(not\s+)?(?:\w+\s+)?" + VERDICT_WORDS + r"\b",
    re.IGNORECASE)


def normalize_verdict(word, negated=False):
    buggy = word.lower() in ("buggy", "incorrect", "wrong")
    if negated:
        buggy = not buggy
    return "buggy" if buggy else "correct"


def extract_prediction(response):
    """Return 'buggy', 'correct', or None.

    1. The last <start>...<end> tag (tolerating </end>), since the model sometimes
       repeats the format example before giving its own answer.
    2. If there is no usable tag, the last explicit verdict sentence such as
       "The code is buggy" / "the candidate is not Buggy".
    Bare occurrences of the words are deliberately NOT used: "To correct this" or a
    sample input like "Buggy" are not verdicts, and an earlier version of this
    fallback mis-scored such responses."""
    tags = re.findall(r"<start>\s*(.*?)\s*<\s*/?\s*end\s*>", response, re.IGNORECASE | re.DOTALL)
    for tag in reversed(tags):
        word = re.search(r"\b(not\s+)?" + VERDICT_WORDS + r"\b", tag, re.IGNORECASE)
        if word:
            return normalize_verdict(word.group(2), bool(word.group(1)))
    statements = VERDICT_STATEMENT.findall(response)
    if statements:
        negated, word = statements[-1]
        return normalize_verdict(word, bool(negated))
    return None


def prompt_model(dataset, model_name = "deepseek-ai/deepseek-coder-6.7b-instruct", vanilla = True, variant = "chain"):
    if vanilla:
        variant = "vanilla"
    print(f"Working with {model_name} prompt type {vanilla} (variant: {variant})...")

    tokenizer, model = load_model(model_name)

    results = []
    num_correct = 0
    for entry in dataset:
        extra = {}
        try:
            # TODO: create prompt for the model
            if variant == "chain":
                ref_prompt = build_reference_prompt(entry)
                ref_response = generate(tokenizer, model, ref_prompt, max_new_tokens=512)
                reference = extract_code(ref_response)
                prompt = build_compare_prompt(entry, reference)
                extra = {"stage_1_prompt": ref_prompt, "stage_1_response": ref_response}
            elif variant == "checklist":
                prompt = build_checklist_prompt(entry)
            else:  # "vanilla" or "steps"
                prompt = build_prompt(entry, vanilla)

            # TODO: prompt the model and get the response
            response = generate(tokenizer, model, prompt)
        except Exception as e:
            prompt = locals().get("prompt", "")
            response = ""
            print(f"Generation failed for {entry['task_id']}: {e}")

        # TODO: process the response and save it to results
        prediction = extract_prediction(response)
        verdict = prediction == EXPECTED_VERDICT
        num_correct += verdict

        if extra:
            print(f"Task_ID {entry['task_id']} stage 1 (reference implementation):\n"
                  f"{extra['stage_1_prompt']}\n{extra['stage_1_response']}\n")
        print(f"Task_ID {entry['task_id']}:\nprompt:\n{prompt}\nresponse:\n{response}\n"
              f"prediction:\n{prediction}\nis_expected:\n{verdict}")
        results.append({
            "task_id": entry["task_id"],
            "prompt": prompt,
            "response": response,
            "prediction": prediction,
            "is_correct": verdict,
            **extra,
        })

    print(f"\nSummary ({variant}): "
          f"{num_correct}/{len(dataset)} correctly predicted as Buggy "
          f"({100 * num_correct / max(len(dataset), 1):.0f}%)")
    for r in results:
        print(f"  {r['task_id']}: prediction={r['prediction']} is_correct={r['is_correct']}")
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
    This Python script is to run prompt LLMs for bug detection.
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
    variant = args[4] if len(args) > 4 else "chain"

    if not input_dataset.endswith(".jsonl"):
        raise ValueError(f"{input_dataset} should be a `.jsonl` file!")

    if not output_file.endswith(".jsonl"):
        raise ValueError(f"{output_file} should be a `.jsonl` file!")

    vanilla = True if if_vanilla == "True" else False

    dataset = read_jsonl(input_dataset)
    results = prompt_model(dataset, model, vanilla, variant)
    write_jsonl(results, output_file)
