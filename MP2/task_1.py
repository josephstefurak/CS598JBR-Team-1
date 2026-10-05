import jsonlines
import sys
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
import random
import re

#####################################################
# Please finish all TODOs in this file for MP2;
#####################################################

def save_file(content, file_path):
    with open(file_path, 'w') as file:
        file.write(content)

def select_assertion(test_str: str) -> dict[str, str]:
    lines = test_str.split('\n')
    filtered: list[str] = []
    regex = r'assert\s+candidate\((.*?)\)\s*==\s*(\[[^\]]*\]|\([^)]*\)|"[^"]*"|\'\[^\'\]*\'|\-?\d+|None|True|False|\w+)'
    for line in lines:
        if len(line) == 0:
            continue
        line = line.strip()
        is_found = re.match(regex, line)
        if is_found is None:
            continue
        filtered.append(line)
    if len(filtered) == 0:
        raise RuntimeError(f"test string: {test_str} did not produce any assertions")
    random_choice = random.choice(filtered)

    filtered.remove(random_choice)
    all_other_tests = '\n'.join(filtered)
    matches = re.match(regex, random_choice)
    if matches is None:
        raise RuntimeError(f"Could not parse selected assertion: {random_choice}")
    candidate = matches[1]
    assertion = matches[2]

    return {
        "candidate": candidate,
        "assertion": assertion,
        "reduced_test_string": all_other_tests
    }

def get_verdict(response_str: str, expected: str):
    regex = r"\[Output\]\s*(.*?)\s*\[/Output\]"
    matches = re.findall(regex, response_str, re.DOTALL)

    if len(matches) != 1:
        return False, expected, 'Prediction error: NO MATCHES'

    prediction = matches[-1]
    prediction = prediction.strip().lower().replace(r'\s', '')
    expected = expected.strip().lower().replace(r'\s', '')
    print(f"Expected: {expected}\tPrediction: {prediction}")
    return expected == prediction, expected, prediction


def prompt_model(dataset, model_name = "deepseek-ai/deepseek-coder-6.7b-instruct", vanilla = True):
    print(f"Working with {model_name} prompt type {vanilla}...")
    
    # TODO: download the model
    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    # TODO: load the model with quantization
    bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_use_double_quant=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.bfloat16
    )
    model = AutoModelForCausalLM.from_pretrained(
    model_name,
    quantization_config=bnb_config,
    device_map="auto",
    torch_dtype=torch.bfloat16,
    trust_remote_code=True
    )
    
    results = []
    for entry in dataset:
        try:
            # TODO: create prompt for the model
            # Tip : Use can use any data from the dataset to create 
            #       the prompt including prompt, canonical_solution, test, etc.
            test_string = entry['test']
            task_prompt = entry['prompt']
            entry_point = entry['entry_point']
            selection = select_assertion(test_string)
            candidate = selection['candidate']
            assertion = selection['assertion']
            canonical_solution = entry['canonical_solution']
            example_inputs_and_outputs = selection['reduced_test_string']

            if vanilla:
                prompt = f"""
You are an AI programming assistant. You are an AI programming assistant, utilizing the DeepSeek Coder model, developed by DeepSeek Company, and you only answer questions related to computer science. 
For politically sensitive questions, security and privacy issues, and other non-computer science questions, you will refuse to answer.

### Instruction:

If the string is '{candidate}', what will the following code return?

The return value 'prediction' must be enclosed between [Output] and [/Output] tags. For example : [Output]prediction[/Output]

Your prediction MUST be the last thing you output. Nothing more otherwise your prediction WILL be rejected.

### Example Response:

thoughs
...
Final: [Output]prediction[/Output]

```python
{ canonical_solution }
```
### Response:
"""
            else:
                prompt = f"""
You are an AI programming assistant using DeepSeek Coder.

Determine the exact return value of the Python function below for the given input.

Do the computation yourself. Do not merely describe what the function does.
Do not create additional test cases.
Do not repeat the examples.
Do not provide Python code.
Do not provide multiple answers.

### Function Specification
{task_prompt}

### Function Entry Point
{entry_point}

### Examples
{example_inputs_and_outputs}

These examples are only behavioral examples. The target input is NOT necessarily among them.

### Target Input
{candidate}

### Code
```python
{canonical_solution}
```

### Required Output
Return the exact literal Python value produced by the function.

Your response MUST end with exactly one:
[Output]VALUE[/Output]

Replace VALUE with ONLY the literal return value.

Examples:

[Output]42[/Output]
[Output][1, 2, 3][/Output]
[Output][][/Output]
[Output]"hello"[/Output]

Do not put anything inside [Output] tags except the return value.

The [Output]...[/Output] pair must be the final thing in your response.
"""

            inputs = tokenizer(
                prompt,
                return_tensors="pt"
            )

            input_ids = inputs["input_ids"].to(model.device)
            attention_mask = inputs["attention_mask"].to(model.device)
            
            # TODO: prompt the model and get the response
            outputs = model.generate(
                input_ids=input_ids,
                attention_mask=attention_mask,
                max_new_tokens=1000,
                do_sample=False,
                eos_token_id=tokenizer.eos_token_id,
                pad_token_id=tokenizer.eos_token_id
            )
            response = tokenizer.decode(outputs[0][input_ids.shape[1]:], skip_special_tokens=True)

            # TODO: process the response and save it to results
            verdict, expected, prediction = get_verdict(response, assertion)

            print(f"Task_ID {entry['task_id']}:\nprompt:\n{prompt}\nresponse:\n{response}\nexpected:\n{expected}\nactual:\n{prediction}\nis_correct:\n{verdict}\n\n")
            results.append({
                "task_id": entry["task_id"],
                "prompt": prompt,
                "response": response,
                "is_correct": verdict
            })
        except Exception as e:
            print(f"Exception rasied: {e}")
            results.append({
                "task_id": entry["task_id"],
                "prompt": "Error",
                "response": e,
                "is_correct": False
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
