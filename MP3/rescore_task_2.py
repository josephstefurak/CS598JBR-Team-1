"""Re-score saved MP3 Task 2 results with the current verdict parser in task_2.py.

The model responses are not regenerated; only `prediction` and `is_correct` are
recomputed from each saved response. A summary of any changes is appended to the
corresponding log file so the logs stay consistent with the JSONL files.

Usage: python3 rescore_task_2.py <results.jsonl> <log_file>
"""
import sys

from task_2 import EXPECTED_VERDICT, extract_prediction, read_jsonl, write_jsonl

if __name__ == "__main__":
    results_file, log_file = sys.argv[1], sys.argv[2]
    results = read_jsonl(results_file)
    lines = [f"\n===== Re-scored {results_file} with the fixed verdict parser "
             f"(responses unchanged) ====="]
    for r in results:
        new_prediction = extract_prediction(r["response"])
        new_verdict = new_prediction == EXPECTED_VERDICT
        if new_prediction != r.get("prediction") or new_verdict != r["is_correct"]:
            lines.append(f"  {r['task_id']}: prediction {r.get('prediction')} -> {new_prediction}, "
                         f"is_correct {r['is_correct']} -> {new_verdict}")
        r["prediction"], r["is_correct"] = new_prediction, new_verdict
    num_correct = sum(r["is_correct"] for r in results)
    lines.append(f"Summary after re-scoring: {num_correct}/{len(results)} correctly predicted as Buggy "
                 f"({100 * num_correct / max(len(results), 1):.0f}%)")
    for r in results:
        lines.append(f"  {r['task_id']}: prediction={r['prediction']} is_correct={r['is_correct']}")
    write_jsonl(results, results_file)
    with open(log_file, "a") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))
