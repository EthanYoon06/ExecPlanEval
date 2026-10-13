import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const root = process.cwd();
const taskLines = (await fs.readFile(path.join(root, "external_validation/data/external_tasks.jsonl"), "utf8"))
  .trim().split(/\r?\n/).map(JSON.parse);
const planLines = (await fs.readFile(path.join(root, "external_validation/results/natural_plans.jsonl"), "utf8"))
  .trim().split(/\r?\n/).map(JSON.parse);
const taskById = new Map(taskLines.map((task) => [task.task_id, task]));

function stableHash(text) {
  let value = 2166136261;
  for (const char of text) value = Math.imul(value ^ char.charCodeAt(0), 16777619) >>> 0;
  return value;
}

const annotationPlans = planLines
  .filter((record) => Number(record.run) === 1)
  .sort((left, right) => stableHash(left.task_id) - stableHash(right.task_id));

if (annotationPlans.length !== 120) throw new Error(`Expected 120 plans, found ${annotationPlans.length}`);

const headers = [
  "annotation_id", "task_id", "benchmark", "subset", "instruction", "candidate_plan",
  "overall_validity", "tool_selection", "dependency_validity", "executability",
  "goal_completion", "alternative_valid_plan", "primary_error_type", "rationale",
  "annotator_id", "completed_at",
];

const navy = "#17365D";
const blue = "#D9EAF7";
const pale = "#F4F7FA";
const gold = "#FFF2CC";
const border = "#B8C4CE";

function sourceRows(annotatorId) {
  return annotationPlans.map((record, index) => {
    const task = taskById.get(record.task_id);
    if (!task) throw new Error(`Task not found: ${record.task_id}`);
    const plan = record.plan || { nodes: [], edges: [] };
    const nodes = (plan.nodes || []).map((node) => `${node.id}. ${node.label || node.tool || ""}`).join("\n");
    const edges = (plan.edges || []).map((edge) => `${edge.source} -> ${edge.target}`).join("; ") || "No dependency edges";
    return [
      `P${String(index + 1).padStart(4, "0")}`,
      task.task_id,
      task.benchmark,
      task.subset,
      task.instruction,
      `${nodes}\nDependency edges: ${edges}`,
      "", "", "", "", "", "", "", "", annotatorId, "",
    ];
  });
}

function buildWorkbook(annotatorId) {
  const workbook = Workbook.create();
  const protocol = workbook.worksheets.add("Protocol");
  const annotations = workbook.worksheets.add("Annotations");
  const codebook = workbook.worksheets.add("Codebook");
  const rows = sourceRows(annotatorId);

  protocol.showGridLines = false;
  protocol.getRange("A1:B1").merge();
  protocol.getRange("A1").values = [[`Independent Blind Annotation Protocol — Annotator ${annotatorId}`]];
  protocol.getRange("A1:B1").format = {
    fill: navy, font: { bold: true, color: "#FFFFFF", size: 16 },
    rowHeight: 30, verticalAlignment: "center",
  };
  const protocolRows = [
    ["Purpose", "Independently judge whether each candidate plan is correct, executable, and sufficient to complete the stated goal."],
    ["Blinding", "Do not inspect model identity, automatic scores, or the gold/reference plan."],
    ["Independence", "Annotators A and B must work separately and must not discuss individual cases before the first-pass annotation is complete."],
    ["How to annotate", "Edit only the yellow columns in the Annotations sheet. Select one value for every categorical field and provide a 1–3 sentence rationale."],
    ["Dependency meaning", "An edge source -> target means that target can be executed only after source has been completed."],
    ["Disagreement", "Preserve both original annotations. Calculate agreement first; a third adjudicator resolves disagreements afterward."],
  ];
  protocol.getRange("A3:B8").values = protocolRows;
  protocol.getRange("A3:A8").format = {
    fill: blue, font: { bold: true, color: navy }, verticalAlignment: "top",
    borders: { preset: "all", style: "thin", color: border },
  };
  protocol.getRange("B3:B8").format = {
    wrapText: true, verticalAlignment: "top",
    borders: { preset: "all", style: "thin", color: border },
  };
  protocol.getRange("A:A").format.columnWidth = 22;
  protocol.getRange("B:B").format.columnWidth = 92;
  protocol.getRange("3:8").format.rowHeight = 45;

  annotations.showGridLines = false;
  annotations.getRange(`A1:P${rows.length + 1}`).values = [headers, ...rows];
  annotations.getRange("A1:P1").format = {
    fill: navy, font: { bold: true, color: "#FFFFFF" }, wrapText: true,
    rowHeight: 34, verticalAlignment: "center",
    borders: { preset: "all", style: "thin", color: border },
  };
  annotations.getRange(`A2:F${rows.length + 1}`).format = {
    fill: pale, wrapText: true, verticalAlignment: "top",
    borders: { preset: "all", style: "thin", color: border },
  };
  annotations.getRange(`G2:P${rows.length + 1}`).format = {
    fill: gold, wrapText: true, verticalAlignment: "top",
    borders: { preset: "all", style: "thin", color: border },
  };
  annotations.freezePanes.freezeRows(1);
  annotations.freezePanes.freezeColumns(2);
  annotations.getRange(`G2:G${rows.length + 1}`).dataValidation = { rule: { type: "list", values: ["Valid", "Partially valid", "Invalid"] } };
  annotations.getRange(`H2:H${rows.length + 1}`).dataValidation = { rule: { type: "list", values: ["Correct", "Partially correct", "Incorrect"] } };
  annotations.getRange(`I2:I${rows.length + 1}`).dataValidation = { rule: { type: "list", values: ["Correct", "Missing dependencies", "Incorrect dependencies"] } };
  annotations.getRange(`J2:J${rows.length + 1}`).dataValidation = { rule: { type: "list", values: ["Executable", "Uncertain", "Not executable"] } };
  annotations.getRange(`K2:K${rows.length + 1}`).dataValidation = { rule: { type: "list", values: ["Complete", "Partial", "Not complete"] } };
  annotations.getRange(`L2:L${rows.length + 1}`).dataValidation = { rule: { type: "list", values: ["Yes", "No", "Uncertain"] } };
  annotations.getRange(`M2:M${rows.length + 1}`).dataValidation = { rule: { type: "list", values: ["None", "Missing node", "Extra node", "Wrong tool", "Missing edge", "Wrong edge", "Wrong order", "Hallucination", "Other"] } };
  const widths = [14, 27, 15, 16, 58, 58, 18, 19, 22, 18, 18, 22, 20, 42, 16, 20];
  const letters = "ABCDEFGHIJKLMNOP";
  for (let col = 0; col < widths.length; col += 1) {
    annotations.getRange(`${letters[col]}:${letters[col]}`).format.columnWidth = widths[col];
  }
  annotations.getRange(`2:${rows.length + 1}`).format.rowHeight = 96;
  annotations.tables.add(`A1:P${rows.length + 1}`, true, `BlindAnnotations${annotatorId}`);

  codebook.showGridLines = false;
  codebook.getRange("A1:D1").merge();
  codebook.getRange("A1").values = [["Annotation Fields and Decision Rules"]];
  codebook.getRange("A1:D1").format = { fill: navy, font: { bold: true, color: "#FFFFFF", size: 15 }, rowHeight: 28 };
  const codeRows = [
    ["Field", "Options", "Decision rule", "Core metric"],
    ["overall_validity", "Valid / Partially valid / Invalid", "Overall judgment. Select Valid only when essential actions, tools, and dependencies are sound.", "Yes"],
    ["tool_selection", "Correct / Partially correct / Incorrect", "Whether the selected tools or actions are appropriate for the task.", "Yes"],
    ["dependency_validity", "Correct / Missing dependencies / Incorrect dependencies", "Check whether each edge is warranted and whether necessary prerequisite relations are missing.", "Yes"],
    ["executability", "Executable / Uncertain / Not executable", "Whether required inputs are available and actions are sufficiently specified when followed in order.", "Yes"],
    ["goal_completion", "Complete / Partial / Not complete", "Whether executing every node would satisfy the user's complete goal.", "Yes"],
    ["alternative_valid_plan", "Yes / No / Uncertain", "Whether the plan is a legitimate alternative decomposition even if it differs from a common reference.", "No"],
    ["primary_error_type", "Dropdown list", "Select the single most important error. Select None when the overall plan is valid.", "No"],
    ["rationale", "Free text", "Give 1–3 sentences citing the decisive evidence; do not write only 'correct' or 'incorrect'.", "No"],
  ];
  codebook.getRange("A3:D11").values = codeRows;
  codebook.getRange("A3:D3").format = {
    fill: navy, font: { bold: true, color: "#FFFFFF" },
    borders: { preset: "all", style: "thin", color: border },
  };
  codebook.getRange("A4:D11").format = {
    wrapText: true, verticalAlignment: "top",
    borders: { preset: "all", style: "thin", color: border },
  };
  codebook.getRange("A:A").format.columnWidth = 25;
  codebook.getRange("B:B").format.columnWidth = 43;
  codebook.getRange("C:C").format.columnWidth = 78;
  codebook.getRange("D:D").format.columnWidth = 15;
  codebook.freezePanes.freezeRows(3);
  return workbook;
}

const outDir = path.join(root, "outputs", "english_annotation_tables_20260827");
await fs.mkdir(outDir, { recursive: true });

for (const annotatorId of ["A", "B"]) {
  const workbook = buildWorkbook(annotatorId);
  const outputPath = path.join(outDir, `English_Annotation_Table_${annotatorId}.xlsx`);
  const output = await SpreadsheetFile.exportXlsx(workbook);
  await output.save(outputPath);

  for (const [sheetName, range] of [["Protocol", "A1:B8"], ["Annotations", "A1:P12"], ["Codebook", "A1:D11"]]) {
    const preview = await workbook.render({ sheetName, range, scale: 1, format: "png" });
    await fs.writeFile(path.join(outDir, `${annotatorId}_${sheetName}.png`), new Uint8Array(await preview.arrayBuffer()));
  }

  const check = await workbook.inspect({
    kind: "table", range: "Annotations!A1:P6", include: "values,formulas",
    tableMaxRows: 6, tableMaxCols: 16, maxChars: 5000,
  });
  console.log(`ANNOTATOR ${annotatorId}\n${check.ndjson}`);
  const errors = await workbook.inspect({
    kind: "match", searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
    options: { useRegex: true, maxResults: 100 }, summary: `formula errors ${annotatorId}`,
  });
  console.log(errors.ndjson);
}
