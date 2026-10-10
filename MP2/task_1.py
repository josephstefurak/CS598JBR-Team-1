import jsonlines
import sys
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
import re
import ast
import copy
import random

#####################################################
# Please finish all TODOs in this file for MP2;
#####################################################

def save_file(content, file_path):
    with open(file_path, 'w') as file:
        file.write(content)

def select_test(entry):
    ns, calls = {}, []
    exec(entry["prompt"] + entry["canonical_solution"], ns)
    fn = ns[entry["entry_point"]]
    def recorder(*args):
        calls.append(copy.deepcopy(args))
        return fn(*args)
    exec(entry["test"], ns)
    random.seed(0)
    ns["check"](recorder)
    inputs = sorted(set(repr(c)[1:-1].rstrip(",") for c in calls), key=lambda s: (len(s), s))[:3]
    args_str = random.Random(entry["task_id"]).choice(inputs)
    expected = eval(f"{entry['entry_point']}({args_str})", ns)
    return args_str, expected

def get_verdict(response, expected):
    preds = re.findall(r"\[Output\](.*?)\[[/\\]Output\]", response, re.DOTALL)
    if not preds:
        return None, False
    pred = preds[-1].strip()
    try:
        return pred, ast.literal_eval(pred) == expected
    except Exception:
        return pred, pred == expected

def prompt_model(dataset, model_name = "deepseek-ai/deepseek-coder-6.7b-instruct", vanilla = True):
    print(f"Working with {model_name} prompt type {vanilla}...")
    
    # TODO: download the model
    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    # TODO: load the model with quantization
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        quantization_config=BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_compute_dtype=torch.bfloat16),
        device_map="auto",
        trust_remote_code=True,
    )
    
    results = []
    for entry in dataset:
        # TODO: create prompt for the model
        # Tip : Use can use any data from the dataset to create 
        #       the prompt including prompt, canonical_solution, test, etc.
        prompt = ""
        args_str, expected = select_test(entry)
        program = entry["prompt"] + entry["canonical_solution"]
        system = ("You are an AI programming assistant. You are an AI programming assistant, utilizing the "
                  "DeepSeek Coder model, developed by DeepSeek Company, and you only answer questions related "
                  "to computer science. For politically sensitive questions, security and privacy issues, and "
                  "other non-computer science questions, you will refuse to answer.")
        if vanilla:
            code = re.sub(r'("""|\'\'\')[\s\S]*?\1', "", program)
            prompt = f"""{system}
### Instruction:
If the input is {args_str}, what will the following code return?
The return value prediction must be enclosed between [Output] and [/Output] tags. For example : [Output]prediction[/Output]

{code}
### Response:
"""
        else:
            prompt = f"""{system}
### Instruction:
Predict the exact return value of a Python function call by tracing its execution step by step like the Python interpreter.

Example:
```python
def sum_even_squares(nums):
    total = 0
    for n in nums:
        if n % 2 == 0:
            total += n * n
    return total
```
Call: sum_even_squares([1, 2, 3, 4])
Execution trace:
1. Arguments: nums = [1, 2, 3, 4]
2. total = 0
3. n = 1: 1 % 2 == 0 -> False. total = 0
   n = 2: 2 % 2 == 0 -> True. total = 0 + 4 = 4
   n = 3: 3 % 2 == 0 -> False. total = 4
   n = 4: 4 % 2 == 0 -> True. total = 4 + 16 = 20
4. return 20
[Output]20[/Output]

Now trace this one the same way.
```python
{program.strip()}
```
Call: {entry['entry_point']}({args_str})

Rules: arguments are Python literals. Trace every loop iteration and write each variable change. For each condition write the compared values and True/False. Use the docstring examples to sanity check, but the code decides. End with the return value as a Python literal inside [Output] and [/Output].
### Response:
Execution trace:
1. Arguments:"""
        
        # TODO: prompt the model and get the response
        response = ""
        inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
        outputs = model.generate(**inputs, max_new_tokens=1536, do_sample=False,
                                 pad_token_id=tokenizer.eos_token_id,
                                 stop_strings=["[/Output]"], tokenizer=tokenizer)
        response = tokenizer.decode(outputs[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)

        # TODO: process the response and save it to results
        prediction, verdict = get_verdict(response, expected)

        print(f"Task_ID {entry['task_id']}:\nprompt:\n{prompt}\nresponse:\n{response}\n" f"expected:\n{expected!r}\nprediction:\n{prediction}\nis_correct:\n{verdict}")
        results.append({
            "task_id": entry["task_id"],
            "prompt": prompt,
            "response": response,
            "is_correct": verdict
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
    `python3 Task_1.py <input_dataset> <model> <output_file> <if_vanilla>`|& tee prompt.log

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