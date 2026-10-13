# Real-environment execution status

## Local checks (2026-08-26)

- Windows host with WSL 2.7.12 and Ubuntu 22.04.
- Windows Python 3.13.9; the isolated ALFWorld environment uses Ubuntu Python 3.10.
- Java and Conda are not installed.
- `pip install --dry-run --index-url https://pypi.org/simple alfworld` reaches ALFWorld 0.4.2,
  but its Jericho/TextWorld build fails under the current Windows/Python toolchain.

## Official requirements

- ALFWorld: https://github.com/alfworld/alfworld
  - Official quickstart recommends an isolated Python 3.9 environment.
  - Text-only evaluation still needs ALFWorld game/PDDL data and TextWorld dependencies.
- WebShop: https://github.com/princeton-nlp/WebShop
  - Official setup specifies Python 3.8.13 and Java.
  - Its setup script downloads product/instruction data and builds a search index.

## Claim allowed now

The completed experiment is an external-benchmark, reference-free plan-generation evaluation with
automatic graph metrics and a protocol for independent human validation.

## Formal live execution evidence

- WSL 2.7.12 and Ubuntu 22.04 are installed.
- ALFWorld text-only environment imports and resets successfully.
- Live `valid_unseen` trajectories are stored as JSON with environment rewards and terminal states.
- The fixed stratified sample contains 120 distinct `valid_unseen` games across all six task types.
- Qwen3-8B succeeds on 35/120 tasks (29.17%, Wilson 95% CI 21.78--37.84%) at 50 steps.
- All selected actions are environment-admissible; median episode length is 50 steps.
- Category success ranges from 0/21 for heat-then-place to 12/18 for look-at-object-in-light.

## Interpretation boundary

Do not call `static_external_score`, graph validity, or catalog validity a real execution success
rate. The ALFWorld result is genuine simulator-execution evidence and is reported separately from
static graph scores. It remains one environment, one local model, one deterministic decoding policy,
and one step budget. WebShop remains uninstalled.
