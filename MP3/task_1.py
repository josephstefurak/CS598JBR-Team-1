import jsonlines
import sys
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
import re
import subprocess

from pathlib import Path

current_directory = Path.cwd()

solution_file = current_directory / "Solution.java"
test_file = current_directory / "Main.java"
junit_jar = current_directory / "junit-platform-console-standalone.jar"

#####################################################
# Please finish all TODOs in this file for MP3/task_1;
#####################################################

def save_file(content, file_path):
    with open(file_path, 'w') as file:
        file.write(content)

def get_verdict(response: str, test_content: str):
    generated_test_match = re.findall(r"\[Java Start\](.*?)\[Java End\]", response, re.DOTALL)
    if not generated_test_match:
        return None, False
    generated_test = generated_test_match[-1].strip()
    solution: str = ''.join(['import java.util.*;\n' ,'class Solution {\n', generated_test, '\n}'])

    save_file(solution, solution_file)
    save_file(test_content, test_file)


    try:
        compile_test_command = [
            "javac",
            "-cp", str(junit_jar),
            str(solution_file),
            str(test_file)
        ]

        compile_result = subprocess.run(
            compile_test_command,
            capture_output=True,
            text=True,
            check=False,
            cwd=current_directory
        )

        if compile_result.returncode != 0:
            print("Compliation failed:")
            print(compile_result.stderr)
            return solution, False

        command = [
            "java",
            "-ea",
            "-cp", str(current_directory),
            "Main"
        ]

        test_result = subprocess.run(command, capture_output=True, text=True, check=False, cwd=current_directory)
        if test_result.returncode != 0:
            print("Tests failed:")
            print(test_result.stdout)
            print(test_result.stderr)
            return solution, False
        return solution, True
    except FileNotFoundError as error:
        print(f"Required executable or file not found: {error}")
        return solution, False


def prompt_model(dataset_python, dataset_java, model_name = "deepseek-ai/deepseek-coder-6.7b-instruct", vanilla = True):
    print(f"Working with {model_name} prompt type {vanilla}...")
    
    # TODO: download the model
    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    # TODO: load the model with quantization
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        quantization_config=BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_compute_dtype=torch.bfloat16),
        device_map="auto",
        trust_remote_code=True
    )
    
    results = []
    java_by_id = {
        entry['task_id']: entry
        for entry in dataset_java
    }
    for entry_python in dataset_python:
        # TODO: create prompt for the model
        # Tip : Use can use any data from the dataset to create 
        #       the prompt including prompt, canonical_solution, test, etc.
        prompt = ""
        task_id = entry_python['task_id']
        entry_java = java_by_id[task_id]

        test: str = entry_java["test"]
        declaration = "import java.util.*;\nimport java.lang.*;\n\n"
        test_content = ''.join([declaration, test])

        java_declaration = entry_java['declaration']

        python_prompt = entry_python["prompt"]
        python_canonical_solution = entry_python["canonical_solution"]
        python_code = ''.join([python_prompt, python_canonical_solution])


        system_prompt = """
You are an AI programming assistant utilizing the DeepSeek Coder model, developed by DeepSeek Company, and you only answer questions related to computer science. 
For politically sensitive questions, security and privacy issues, and other non-computer science questions, you will refuse to answer.
        """

        example_output = """
public static int sumEvenNumbers(int[] nums) {
    int total = 0;
    for (int i = 0; i < nums.length; i++) {
        int n = nums[i];
        if (n % 2 == 0) {
            total += n * n;
        }
    }
    return total
}

"""

        if vanilla:
            prompt = f"""
{system_prompt}

### Instruction:
Can you translate the following Python code into Java?
The new Java code must be enclosed between [Java Start] and [Java End]

{python_code}

### Response:
"""
        else:
            prompt = f"""
{system_prompt}

### Instruction:
Translate the following Python function into Java.
Return only the translated Java method, enclosed between [Java Start] and [Java End].
Do not include a class, main method, explanation, or any unrelated code, but preserve Java Method naming conventions (i.e., use camelCase in the translated methods and not snake_case).

The translated method MUST use the exact method name, parameter types, parameter order, and return type from the Java declaration below.

Do not replace List with an array or change any parameter types.
The method must compile with the provided test code.

```java
{java_declaration}
```

### Example Input:
```python
def sum_even_squares(nums):
    total = 0
    for n in nums:
        if n % 2 == 0:
            total += n * n
    return total
```

### Example Output:

[Java Start]{example_output}[Java End]

Now translate this one the same way.
```python
{python_code}
```

### Response
"""
        
        # TODO: prompt the model and get the response
        inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
        outputs = model.generate(
            **inputs, 
            max_new_tokens=1536, 
            do_sample=False, 
            pad_token_id=tokenizer.eos_token_id,
            stop_strings=["[Java End]"],
            tokenizer=tokenizer
        )

        response = tokenizer.decode(outputs[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)

        print(f"Test Content: {test_content}")
        prediction, verdict = get_verdict(response, test_content)

        print(f"Task_ID {entry_python['task_id']}:\nprompt:\n{prompt}\nresponse:\n{response}\nprediction:\n{prediction}\nis_expected:\n{verdict}")
        results.append({
            "task_id": entry_python["task_id"],
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
    This Python script is to run prompt LLMs for code translation.
    Usage:
    `python3 task_1.py <input_dataset_python> <input_dataset_java> <model> <output_file> <if_vanilla>`|& tee prompt.log

    Inputs:
    - <input_dataset_python>: A `.jsonl` file, which should be your team's dataset containing 20 HumanEval problems.
    - <input_dataset_java>: A `.jsonl` file, which should be your team's dataset for all things java
    - <model>: Specify the model to use. Options are "deepseek-ai/deepseek-coder-6.7b-base" or "deepseek-ai/deepseek-coder-6.7b-instruct".
    - <output_file>: A `.jsonl` file where the results will be saved.
    - <if_vanilla>: Set to 'True' or 'False' to enable vanilla prompt
    
    Outputs:
    - You can check <output_file> for detailed information.
    """
    args = sys.argv[1:]
    input_dataset_python = args[0]
    input_dataset_java = args[1]
    model = args[2]
    output_file = args[3]
    if_vanilla = args[4] # True or False
    
    if not input_dataset_python.endswith(".jsonl"):
        raise ValueError(f"{input_dataset_python} should be a `.jsonl` file!")
    
    if not input_dataset_java.endswith(".jsonl"):
        raise ValueError(f"{input_dataset_java} should be a `.jsonl` file!")
    
    if not output_file.endswith(".jsonl"):
        raise ValueError(f"{output_file} should be a `.jsonl` file!")
    
    vanilla = True if if_vanilla == "True" else False
    
    dataset_python = read_jsonl(input_dataset_python)
    dataset_java = read_jsonl(input_dataset_java)
    results = prompt_model(dataset_python, dataset_java, model, vanilla)
    write_jsonl(results, output_file)
