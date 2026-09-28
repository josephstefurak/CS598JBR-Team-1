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
    regex = r'assert candidate\((.*)\)(?:==| == | ==|== )([a-zA-Z0-9]+)'
    for line in lines:
        if len(line) == 0:
            continue
        line = line.strip()
        is_found = re.match(regex, line)
        if is_found is None:
            continue
        filtered.append(line)
    random_choice = random.choice(filtered)
    matches = re.match(regex, random_choice)
    if matches is None:
        return {}
    candidate = matches[1]
    assertion = matches[2]

    return {
        "candidate": candidate,
        "assertion": assertion
    }

def get_verdict(response_str: str, expected: str) -> bool:
    regex = r"\[Output\](.*)\[\/Output\]"
    matches = re.match(regex, response_str)
    if matches is None:
        return False
    actual = matches[1].lower()
    print(f"Expected: {expected}\tActual: {actual} ")
    return expected == actual


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
            selection = select_assertion(test_string)
            candidate = selection['candidate']
            assertion = selection['assertion']
            canonical_solution = entry['canonical_solution']

            if vanilla:
                prompt = f"""
You are an AI programming assistant. You are an AI programming assistant, utilizing the DeepSeek Coder model, developed by DeepSeek Company, and you only answer questions related to computer science. 
For politically sensitive questions, security and privacy issues, and other non-computer science questions, you will refuse to answer.

### Instruction:

If the string is '{candidate}', what will the following code return?

The return value 'prediction' must be enclosed between [Output] and [/Output] tags. For example : [Output]prediction[/Output]

```python
{ canonical_solution }
```
### Response:
            """
            else:
                prompt = f"""
You are an AI programming assistant. You are an AI programming assistant, utilizing the DeepSeek Coder model, developed by DeepSeek Company, and you only answer questions related to computer science. 
For politically sensitive questions, security and privacy issues, and other non-computer science questions, you will refuse to answer.

### Instruction:

If the string is '{candidate}', what will the following code return?

The return value 'prediction' must be enclosed between [Output] and [/Output] tags and must be a singular value (either an int, string, boolean, or other primative type). For example : [Output]prediction[/Output]. You may (and should) give reasoning as given below to justify the prediction

Before attempting to return a prediction, do the following:
1. Evaluate the given function by going line by line. Come up with a hypothesis about what the function is trying to acompish and give concrete, line-numbered answers to back up the hypothesis
2. Go step by step to solve the problem
3. Give an inital prediction
4. For the given initial prediction, explain clearly why the initial prediction is made
5. Again go through the problem step by step seeing if the initial prediction holds
    a. if it does, return the initial prediction as the final prediction and end
    b. if it doesn't, modify the inital prediction to reflect current understanding and explain the reasoning of why the initial preditiction was off. Form a new prediction
6. If in step 5 the initial prediction was modified, repeat step 5. Repeat until ready to give your final prediction. Remember, the final return value 'prediction' must be enclosed between [Output] and [/Output] tags. For example : [Output]prediction[/Output]


You are allowed (and encoraged to) convert the input string into the appropriate type (array, int, object, float, boolean). Assume that if you ar
The code:
```python
{ canonical_solution }
```
### Response:
            """

            input_ids = tokenizer(prompt, return_tensors="pt").input_ids.to(model.device)
            
            # TODO: prompt the model and get the response
            outputs = model.generate(
                input_ids,
                max_length=500000,
                do_sample=False,
                eos_token_id=tokenizer.eos_token_id,
                pad_token_id=tokenizer.eos_token_id
            )
            response = tokenizer.decode(outputs[0][input_ids.shape[1]:], skip_special_tokens=True)

            # TODO: process the response and save it to results
            verdict = get_verdict(response, assertion)

            print(f"Task_ID {entry['task_id']}:\nprompt:\n{prompt}\nresponse:\n{response}\nis_correct:\n{verdict}")
            results.append({
                "task_id": entry["task_id"],
                "prompt": prompt,
                "response": response,
                "is_correct": verdict
            })
        except Exception as e:
            print(f"Exception rasied: {e}")
        
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
