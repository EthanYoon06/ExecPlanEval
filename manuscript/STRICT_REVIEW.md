# Strict review and revision record

## Recommendation before revision: Major revision

1. **External validity was easy to overread.** The controlled benchmark can establish construct behavior under known semantics, but it cannot establish open-world accuracy. The natural-plan and ALFWorld studies use different observables and must not be pooled into a single validation claim.
   - **Resolution:** Added VQ1/VQ2, an explicit evidence hierarchy, and repeated disclaimers that no external AUROC for ExecPlanEval is estimated.

2. **AI judgments are not human ground truth.** Both annotators are from the Qwen3 family, and Qwen3-8B also generated the plans. Moderate agreement therefore measures repeatability under correlated model bias, not semantic validity.
   - **Resolution:** Raw AI labels, disagreements, bootstrap confidence intervals, self-evaluation risk, and the separate audit layer are disclosed. The paper explicitly says that independent human assessment remains open work.

3. **Perfect controlled AUROC risks circularity.** Candidate transformations and evaluation contracts share symbolic semantics.
   - **Resolution:** The manuscript now treats the result as a narrow construct test, explains why perfect separation occurs, and avoids presenting it as an open-world estimate.

4. **The ALFWorld experiment does not directly evaluate the proposed static score.** It tests a reactive policy with admissible actions and terminal rewards.
   - **Resolution:** Reframed it as a behavioral sanity check and explicitly excluded it from the controlled metric correlations.

5. **Sampling and annotation protocols needed more detail.** Without exact selection rules and blinded inputs, the external study is difficult to audit.
   - **Resolution:** Added seeded stratified sampling details, visible annotation inputs, withheld information, deterministic decoding, immutable raw labels, and 2,000 bootstrap resamples.

6. **The contribution count and title did not match the expanded study.** The introduction said three contributions while listing four, and the title under-described external evidence.
   - **Resolution:** Corrected the count and revised the title.

## Remaining structural limitation

The artifact is substantially more credible and reproducible after revision, but it still lacks independent human annotation and multi-environment replication. Those are new experiments, not wording defects. A strict reviewer may therefore still request major revision; acceptance cannot be guaranteed from the current evidence alone.

## Second-round strict review

### Additional analyses completed

- Added task-level bootstrap intervals for the exploratory external-label analysis.
- Added fuzzy-node, node--edge overlap, and catalog-validity baselines.
- Added subset-stratified label counts and within-subset centered rank analysis.
- Added a 21-point dependency/executability weight sweep.
- Added concrete high/low structural-agreement diagnostic cases.
- Explicitly separated the reactive ALFWorld policy from pre-generated DAG evaluation.

### Material finding introduced by the revision

The pooled node-F1 correlation with the audited AI-assisted label is 0.496, but the within-subset centered correlation is -0.030. Edge F1 falls from 0.231 pooled to -0.095 within subsets. The paper now reports this negative result prominently: the original pooled association is dominated by benchmark representation and label imbalance.

### Problems that cannot be truthfully closed with the present artifact

1. Independent human labels have not been collected.
2. Natural tasks do not expose the complete symbolic contracts needed to compute all ExecPlanEval components.
3. ALFWorld trajectories came from a reactive policy rather than a frozen plan evaluated before execution.
4. Multi-environment and multi-model replication remains absent.

### Updated recommendation

**Major revision / workshop-ready, but not yet a secure journal acceptance.** The manuscript is now much more defensible because it exposes rather than hides confounding and evaluator instability. A journal-level claim that ExecPlanEval outperforms existing metrics on natural tasks still requires the four experiments above.

## Third-round audit after receipt of two completed annotation workbooks

### Evidence added

- Both workbooks contain 120 unique, aligned records and have no missing categorical labels or rationales.
- Overall-validity agreement is 75.8%, with unweighted Cohen's kappa 0.536 (2,000-resample paired bootstrap 95% CI [0.409, 0.667]).
- Field-level kappa ranges from 0.437 for dependency validity to 0.768 for executability.
- Twenty-nine records disagree on at least one of the seven reported fields; no forced consensus was created.
- Raw workbooks, normalized JSONL files, disagreement records, and deterministic analysis output are retained separately.

### Strict-review finding

The completed tables improve coverage and show that the rubric is usable, but the files alone do not prove that two distinct people worked independently. Both workbooks have one identical batch completion timestamp, and 91 rationales match verbatim. These patterns may reflect a common export process, but without a provenance statement they prevent the manuscript from describing the evidence as certified independent human annotation. The revision therefore uses the narrower term **paired blind annotation passes**.

### Remaining action before a strong journal claim

1. Obtain a short provenance record for each annotator: distinct-person confirmation, relevant experience, date range, and a declaration that the first pass was completed without consultation.
2. Send the 29 disagreement cases to a third person for adjudication while preserving both original labels.
3. Only after adjudication, compute correlations and AUROC against the frozen consensus labels.

### Updated recommendation

**Major revision, with a clear path forward.** The paper can now report genuine paired-pass agreement, but it should not claim independent human ground truth until provenance and adjudication are completed.

## Fourth-round audit after adjudication

### Evidence added

- The submitted adjudication record contains exactly the 29 IDs previously flagged for at least one disagreement; there are no duplicates, omissions, blank rationales, or invalid final categories.
- The immutable A/B passes remain separate. The final layer retains 91 fully agreed rows and uses the adjudication decision for 29 rows, leaving zero unresolved cases.
- Final overall-validity counts are 72 valid, 21 partially valid, and 27 invalid.
- Against the final labels, node F1 has Spearman rho 0.240 (95% task-bootstrap CI [0.051, 0.419]) and AUROC 0.572 ([0.473, 0.672]); edge F1 has rho 0.030 ([-0.151, 0.195]) and AUROC 0.458 ([0.362, 0.551]).
- Within-subset centered rho is 0.084 for node F1 and -0.140 for edge F1, so the adjudicated analysis continues to undermine single-reference graph matching rather than merely reproducing the earlier AI audit.

### Strict-review finding

The missing-consensus problem is now closed, and the result is a meaningful improvement: a reviewer can reconstruct every final label from either rater agreement or an explicit adjudication row. The main negative result is also robust to this label revision. However, the files still do not authenticate the identities, expertise, or independence of A, B, or `Adjudicator1`. An identifier and date are useful audit metadata, but they are not provenance evidence. The manuscript correctly describes the result as an **adjudicated label set**, not as certified independent human ground truth.

### Remaining issues

1. Add signed or otherwise auditable, de-identified provenance statements for the two original contributors and the adjudicator.
2. Evaluate frozen pre-generated plans in at least one external execution environment; the current ALFWorld policy is reactive.
3. Add another model family and, ideally, another interactive environment to establish that results are not Qwen- or ALFWorld-specific.
4. Pre-register or freeze the external metric specification before any weight calibration; natural tasks still lack complete contracts for the full ExecPlanEval score.

### Updated recommendation

**Borderline major revision.** The paper now has a complete, reproducible adjudicated analysis and a stronger external negative result. It is substantially closer to journal quality, but a strict SCI journal reviewer can still reject the phrase “independent human validation” unless contributor provenance is documented, and can still request direct external evaluation of the proposed full metric.

## Fifth-round methods audit

### Major defects found and corrected

1. **The controlled bootstrap unit was mislabeled and statistically weak.** The manuscript described task clustering, while the implementation resampled only five topology levels. Because each topology had the same constructed class balance, this produced misleadingly narrow intervals and only five effective clusters.
   - **Correction:** The implementation now resamples all 50 task IDs and keeps the seven variants of each task together. All controlled confidence intervals and the metric figure were regenerated. The manuscript explicitly states that topology is a fixed design factor and that the intervals are conditional on the synthetic task generator.

2. **The executability definition did not match the code.** The manuscript defined executability as the fraction of nodes completed before failure, but the implementation used static schema/catalog validity in both the static and full scores.
   - **Correction:** The method now defines the implemented component as schema executability: graph integrity, acyclicity, tool membership, and exact declared-contract checks. It explicitly states that partial dynamic progress is not scored. The full-score equation now uses `X_static`, matching the implementation.

3. **The abstract was overlong and mixed incompatible evidence levels.** It gave similar rhetorical weight to controlled causal evidence, model-judge repeatability, unverified paired annotations, adjudication, and reactive ALFWorld execution.
   - **Correction:** The abstract was reduced to approximately 280 words and organized around the controlled result, external diagnostics, and a direct non-generalization statement. It now says that both external F1 AUROC intervals include chance.

4. **Several statements overstated below-chance performance.** An observed edge-F1 AUROC of 0.458 was described as below chance even though its interval included 0.5.
   - **Correction:** The paper now says that edge F1 does not separate the classes in this sample and explicitly notes that both intervals include chance.

5. **Uncertainty language could be misread as population inference.** The synthetic tasks are not a probability sample of deployed workflows, and identical variant structure across tasks limits what bootstrap intervals mean.
   - **Correction:** The limitations now state that controlled intervals measure conditional resampling stability only; external comparisons are exploratory and do not claim multiplicity-adjusted hypothesis tests.

### Remaining rejection risks that cannot be repaired editorially

1. The proposed full metric is not evaluated on a natural benchmark with independently specified tool contracts and execution verifiers.
2. Contributor identity, expertise, and independence remain unauthenticated; completed annotation and adjudication files are not equivalent to documented human provenance.
3. The 350-plan controlled result is intentionally favorable to contract-aware scoring because candidate transformations and the evaluator share semantics.
4. ALFWorld evaluates a reactive policy and reconstructed trajectory, not a frozen DAG scored before execution.
5. External generation relies on one model family and external execution on one environment.

### Recommendation after correction

**Major revision, not acceptance in its present evidentiary form.** The manuscript is now internally consistent, statistically less misleading, and unusually transparent about negative results. It is suitable as a construct-validation or benchmark-methodology submission. For a strong SCI Q2 claim of superior natural-task evaluation, the authors still need authenticated independent annotation and direct external evaluation of the frozen ExecPlanEval metric. No amount of prose polishing can substitute for those experiments.

## Sixth-round core-evidence revision

### External contract evaluation added

The external benchmark files were audited before constructing a new score. A complete natural-task ExecPlanEval score cannot be computed honestly from the available artifacts: WorFBench lacks machine-readable contracts, DailyLife APIs lacks output types, all candidate plans omit argument bindings, and no shared executor supplies terminal goal verification. Deriving these fields from the reference graph would recreate the circularity criticized by the paper.

A narrower non-circular test is possible for 40 TaskBench Multimedia and Hugging Face tasks because their benchmark-authored tool descriptions independently specify input and output types. The revision adds a frozen typed-contract diagnostic based on graph validity, exact catalog membership, and predicted-edge type compatibility. It never uses the gold graph to define tool contracts. All plans have valid graphs and catalog tools; mean edge compatibility is 0.947. Edge compatibility and the composite obtain Spearman rho 0.365 (95% task-bootstrap CI [-0.095, 0.712]) and AUROC 0.631 ([0.470, 0.809]). This is directionally positive but statistically inconclusive.

### Provenance remediation added

The release now contains SHA-256 hashes for the two annotation workbooks and adjudication CSV, plus separate declaration templates for Contributor A, Contributor B, and the adjudicator. The templates require experience, timing, assistance, consultation, conflicts, signature, and custodian verification. They are explicitly marked incomplete. This is the strongest legitimate remediation possible without the real contributors: the files can support future authentication, but the study author or an AI system cannot truthfully attest on another person's behalf.

### Updated assessment

The new typed-contract experiment materially reduces the criticism that every operational result is internally generated: it tests a contract-aware component using independently authored schemas and does not depend on the gold graph. However, it does not evaluate missing dependencies, arguments, goal completion, or execution outcome, and only nine of 40 labels are non-valid. It therefore supports feasibility, not superiority.

**Recommendation remains major revision for a strong Q2 journal, but the path is now narrower.** The remaining decisive work is (1) actual contributor completion and custodian verification of the provenance declarations, and (2) a frozen-plan external execution study or natural benchmark exposing full contracts, arguments, and task verifiers. These cannot be generated from the current files without fabricating evidence or introducing circularity.

## Seventh-round frozen-plan execution audit

### Evidence added

- A fixed 30-game ALFWorld sample contains five games from each task type and is matched by task ID to existing reactive trajectories.
- Each model call sees only the objective, initial observation, and initial admissible commands. One action sequence is then executed verbatim, with no later observation returned to the model, no replanning, no repair, and no action substitution.
- Qwen3-8B completes 0/30 frozen tasks (Wilson 95% CI [0.0, 11.4]) versus 8/30 matched reactive runs (26.7%, [14.2, 44.4]). All eight discordant pairs favor reactive execution; the two-sided exact McNemar p-value is 0.0078125.
- The frozen plans nevertheless obtain mean schema validity 0.995, mean abstract dependency validity 0.872, mean pre-execution score 0.934, and contemporaneous action admissibility 0.728.
- Code, raw plans, verbatim environment traces, and a machine-readable summary are retained. The batch runner is resumable and the analysis reproduces the reported intervals and paired test.

### Strict-review finding

This experiment resolves the earlier procedural objection that the only live trajectories were generated reactively and graphed afterward. More importantly, it produces a credible negative result: a high static score does not imply success when the environment hides state and a plan cannot branch on later observations. The manuscript appropriately narrows the claim instead of treating the all-failure result as support for the proposed score.

The experiment does not directly validate the full ExecPlanEval metric. Its dependency checker is a deliberately limited ALFWorld-specific abstraction, terminal success is constant, and therefore AUROC against success is undefined. The result chiefly identifies a missing construct—observation-contingent control—and shows why static contract compliance is insufficient in partially observable tasks.

### Updated recommendation

**Major revision, with the frozen-plan blocker resolved but the superiority claim still unsupported.** The strongest remaining rejection risks are unauthenticated annotation provenance, reliance on one live environment, non-capacity-matched model comparisons, and the absence of a natural benchmark with complete independently authored contracts, arguments, and goal verifiers. The paper is now stronger as a transparent evaluation-limitations study than as a claim that the current ExecPlanEval score is already a superior general-purpose metric.

## Eighth-round cross-model sensitivity audit

An additional 120-plan Gemma3-1B run covers exactly the same external tasks as Qwen3-8B run 1. It achieves 97.5% parse success but only 58.3% DAG validity, with mean node F1 0.187, edge F1 0.002, and catalog validity 0.314. Qwen-minus-Gemma paired differences are positive with task-bootstrap intervals excluding zero for DAG validity, node F1, edge F1, and catalog validity. Gemma also completes 0/30 frozen ALFWorld tasks, but its mean plan length, admissibility, and static score are much lower than Qwen's.

This closes the narrow criticism that every generation result comes from Qwen. It does not establish model-family invariance: Gemma is 1B rather than 8B and used JSON-constrained decoding after its unconstrained pilot emitted malformed output. The correct interpretation is pipeline sensitivity, not an architectural comparison. A capacity-matched non-Qwen model and reactive execution under the same policy protocol remain desirable.

## Ninth-round claim and positioning audit

The manuscript is now positioned as an evaluation-methodology and limitations study rather than as evidence that ExecPlanEval is already a universally superior metric. The title, abstract, contribution list, audit questions, discussion, and conclusion consistently distinguish four evidence levels: controlled construct validation, descriptive natural-plan diagnostics, annotation reliability, and live execution. ExecPlanEval is presented as one contract-aware diagnostic inside this audit, not as the paper's externally validated winner.

This reframing materially improves defensibility. The strongest results are negative or conditional: a single reference can reject valid alternatives; pooled structural correlations can be benchmark artifacts; static validity does not imply success under partial observability; and model-judge or paired-pass labels require provenance. These findings remain useful even if the proposed diagnostic later changes. A reviewer can therefore accept the methodological contribution without accepting an unsupported superiority claim.
