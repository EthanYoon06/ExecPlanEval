# ExecPlanEval reproducibility artifact

This artifact accompanies the revised ExecPlanEval manuscript. It contains the controlled benchmark, executable evaluation code, saved outputs, external validation materials, annotation layers, and reviewer-specific bootstrap verification evidence.

## Quick verification

Use Python 3.10 or later from the artifact root:

```powershell
python -m pip install -r requirements.txt
python tests/test_pilot.py
python tests/test_controlled.py
python reviewer_evidence/bootstrap_review_evidence/bootstrap_verify.py
```

The final command reads its required inputs from the same evidence directory and writes `bootstrap_independent_verification_rerun.json` there.

Windows users can run `powershell -ExecutionPolicy Bypass -File reproduce_core.ps1`. Linux and macOS users can run `bash reproduce_core.sh`.

## Artifact map

- `controlled/`: 50 controlled tasks, 350 candidate plans, saved per-plan results, aggregate results, generation code, and evaluation code.
- `pilot/`: preliminary 10-task, 60-plan study and local-model outputs.
- `src/`: symbolic execution, structural evaluation, ExecPlanEval scoring, and statistical utilities.
- `tests/`: deterministic integrity and execution checks.
- `external_validation/`: natural-plan scripts and outputs, ALFWorld trajectories and summaries, annotation layers, and provenance templates.
- `external/`: retained upstream benchmark materials used by the external-validation pipeline.
- `manuscript/`: manuscript source, figures, and figure-generation code.
- `reviewer_evidence/bootstrap_review_evidence/`: independent reconstruction of the 50-task cluster bootstrap, including every required input and saved comparison output.
- `ARTIFACT_MANIFEST.csv`: relative path, size, and SHA-256 for every released file other than the manifest itself.

## Controlled-study reproduction

```powershell
python controlled/generate_controlled.py
python tests/test_controlled.py
python controlled/run_controlled.py
python manuscript/make_figures.py
```

The generation and bootstrap seeds are fixed in the released scripts. The bootstrap resamples 50 task IDs with replacement and retains all seven candidate variants belonging to each sampled task. Running generation or analysis scripts may replace saved outputs, so work on a copy if the released outputs must remain byte-for-byte unchanged.

## External validation

See `external_validation/README.md`. Reproducing saved controlled results does not require Ollama, ALFWorld, WSL, or an API key. Regenerating model outputs or live ALFWorld trajectories requires the separately documented local services and environments.

## Annotation and provenance boundary

The release preserves the two completed paired blind annotation workbooks, normalized exports, disagreement adjudication record, and final label layer. The provenance declarations are incomplete templates. They do not authenticate contributor identity, expertise, or independence and must not be represented as signed declarations or certified independent human ground truth.

The local Doccano account-information file has been excluded. Before public release, the study owner should conduct a final privacy review of the workbooks.

## Release status

This folder is a prepared review artifact, not evidence that a public archive already exists. After uploading, record the repository URL, immutable release or archive URL, version, commit identifier, and DOI if assigned in the manuscript's Data and Code Availability statement.

