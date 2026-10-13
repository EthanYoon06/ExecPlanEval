# External validation pipeline

1. `python external_validation/prepare_benchmarks.py --per-subset 20`
2. Start Ollama and run `python external_validation/generate_plans.py --model qwen3:8b --runs 3 --resume`
3. `python external_validation/evaluate_plans.py`
4. `python external_validation/summarize_results.py`
5. Copy the blind annotation workbook once for annotator A and once for annotator B. They work independently.
6. Export the two `Annotations` sheets as CSV and run `python external_validation/annotation_agreement.py annotator_a.csv annotator_b.csv`.

The generator never exposes the reference plan to the model. Raw responses are retained.
The external static score checks graph integrity and catalog membership; it is not itself
an execution-success measure. ALFWorld is evaluated separately through live TextWorld execution.

## Completed local run

- Model: `qwen3:8b` Q4_K_M through Ollama.
- Tasks: 120 (20 from each of six subsets).
- Repetitions: 3 per task; 360 generations total.
- Outputs: `results/natural_plans.jsonl`, `results/external_scores.csv`, and
  `results/summary_by_subset.csv`.
- The annotation workbook contains one fixed run per task (120 shuffled rows); model identity,
  automatic scores, and reference plans are omitted.

## Interpretation boundary

TaskBench and WorFBench provide external benchmark evidence. They do not by themselves establish
live-environment execution success. ALFWorld is now installed under WSL and is reported separately
from the static graph/tool checks. The official WebShop environment has not been executed, so no
WebShop environment-success claim is made.

## ALFWorld live environment

The Windows host now has WSL 2.7.12 with Ubuntu 22.04. ALFWorld 0.4.2, TextWorld 1.7.0,
Jericho 3.3.1, Fast Downward, and the text-only ALFWorld data are installed in:

- Python environment: `/opt/alfworld-venv`
- Game data: `/opt/alfworld-data` (about 2.1 GB)

`run_alfworld_agent.py` connects Windows Ollama to an actual ALFWorld `valid_unseen` TextWorld
process through a JSON-lines worker. Every action, observation, admissibility decision, reward,
termination flag, and trajectory DAG is retained. State-action pairs that already failed in an
identical observation are removed from the next candidate list as an explicit loop-avoidance rule.

The formal evaluation contains 120 distinct `valid_unseen` games and uses a 50-step budget. Because
two categories contain fewer than 20 games, the fixed quotas are 22, 18, 21, 21, 21, and 17; the
two smallest categories are censused. Sampling is without replacement with seed 20260826.

Run and summarize the resumable batch with:

```text
python external_validation/run_alfworld_batch.py --target-total 120 --seed 20260826 --model qwen3:8b --max-steps 50
python external_validation/summarize_alfworld_formal.py
```

Qwen3-8B succeeds on 35/120 tasks (29.17%, Wilson 95% CI 21.78--37.84%). All recorded actions are
admissible. The manifest, episode table, category table, summary, and raw trajectories are retained
under `results/`.

## Frozen-plan execution

The frozen protocol separates plan generation from control. The model sees only the task objective,
initial observation, and initial admissible-command list. It emits one complete action sequence;
the runner executes that sequence verbatim without exposing later observations, replanning,
repairing invalid commands, or substituting actions.

```text
python external_validation/run_alfworld_frozen_batch.py --model qwen3:8b --per-type 5 --max-actions 30
python external_validation/summarize_alfworld_frozen.py
```

The fixed sample contains five games from each of the six task types and is matched to existing
reactive trajectories. Qwen3-8B succeeds on 0/30 frozen plans versus 8/30 matched reactive runs
(two-sided exact McNemar p=0.0078125). The frozen plans nevertheless have mean pre-execution score
0.934, showing that the limited static checker does not model hidden-state search or contingent
replanning. Raw files and the machine-readable summary are under `results/alfworld_frozen/`.

## Non-Qwen sensitivity run

Gemma3-1B was run once on the same 120 external tasks with JSON-constrained decoding. The original
Qwen run was unconstrained, so this is a pipeline-sensitivity diagnostic rather than a controlled
model-family comparison.

```text
python external_validation/generate_plans.py --model gemma3:1b --runs 1 --json-format --output external_validation/results/natural_plans_gemma3_1b.jsonl
python external_validation/evaluate_plans.py --plans external_validation/results/natural_plans_gemma3_1b.jsonl --output external_validation/results/external_scores_gemma3_1b.csv
python external_validation/summarize_cross_model.py external_validation/results/external_scores.csv external_validation/results/external_scores_gemma3_1b.csv --output external_validation/results/cross_model_summary.json
```

The sensitivity run contains 120 plans: 97.5% parse, 58.3% valid DAGs, mean node F1 0.187, mean
edge F1 0.002, and mean catalog validity 0.314. All raw outputs, including three parse failures,
are retained.
