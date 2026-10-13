import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const root = process.cwd();
const resultDir = path.join(root, "external_validation", "results", "human_annotations");
const readJsonl = async (name) => (await fs.readFile(path.join(resultDir, name), "utf8"))
  .trim().split(/\r?\n/).map(JSON.parse);
const rowsA = await readJsonl("annotator_a.jsonl");
const rowsB = await readJsonl("annotator_b.jsonl");
const byB = new Map(rowsB.map((row) => [row.annotation_id, row]));
const fields = ["overall_validity", "tool_selection", "dependency_validity", "executability", "goal_completion", "alternative_valid_plan", "primary_error_type"];

const disagreements = rowsA.filter((rowA) => fields.some((field) => rowA[field] !== byB.get(rowA.annotation_id)[field]));
if (disagreements.length !== 29) throw new Error(`Expected 29 disagreements, found ${disagreements.length}`);

const formatLabels = (row) => fields.map((field) => `${field}: ${row[field]}`).join("\n");
const headers = [
  "annotation_id", "task_id", "benchmark", "subset", "instruction", "candidate_plan", "differing_fields",
  "A_labels", "A_rationale", "B_labels", "B_rationale",
  ...fields.map((field) => `final_${field}`), "adjudication_rationale", "adjudicator_id", "completed_at",
];
const data = disagreements.map((rowA) => {
  const rowB = byB.get(rowA.annotation_id);
  return [
    rowA.annotation_id, rowA.task_id, rowA.benchmark, rowA.subset, rowA.instruction, rowA.candidate_plan,
    fields.filter((field) => rowA[field] !== rowB[field]).join(", "),
    formatLabels(rowA), rowA.rationale, formatLabels(rowB), rowB.rationale,
    "", "", "", "", "", "", "", "", "", "",
  ];
});

const workbook = Workbook.create();
const protocol = workbook.worksheets.add("Protocol");
const sheet = workbook.worksheets.add("Adjudication");
const navy = "#17365D";
const pale = "#F4F7FA";
const gold = "#FFF2CC";
const border = "#B8C4CE";

protocol.showGridLines = false;
protocol.getRange("A1:B1").merge();
protocol.getRange("A1").values = [["Third-Person Adjudication Protocol"]];
protocol.getRange("A1:B1").format = { fill: navy, font: { bold: true, color: "#FFFFFF", size: 16 }, rowHeight: 30 };
protocol.getRange("A3:B8").values = [
  ["Scope", "Only the 29 records with at least one disagreement between passes A and B are included."],
  ["Independence", "Review the task and candidate plan before reading either rationale. Do not consult the original annotators while deciding."],
  ["Decision", "Fill every yellow final_* field. The final label may match A, match B, or differ from both when justified by the codebook."],
  ["Rationale", "Write 1–3 sentences identifying the decisive tool, dependency, executability, or goal-coverage evidence."],
  ["Preservation", "Do not edit A_labels, B_labels, or either original rationale."],
  ["Completion", "Enter a non-identifying adjudicator code and completion date after all seven final fields are filled."],
  ];
protocol.getRange("A3:A8").format = { fill: "#D9EAF7", font: { bold: true, color: navy }, borders: { preset: "all", style: "thin", color: border } };
protocol.getRange("B3:B8").format = { wrapText: true, verticalAlignment: "top", borders: { preset: "all", style: "thin", color: border } };
protocol.getRange("A:A").format.columnWidth = 20;
protocol.getRange("B:B").format.columnWidth = 95;
protocol.getRange("3:8").format.rowHeight = 44;

sheet.showGridLines = false;
sheet.getRange(`A1:U${data.length + 1}`).values = [headers, ...data];
sheet.getRange("A1:U1").format = { fill: navy, font: { bold: true, color: "#FFFFFF" }, wrapText: true, rowHeight: 36, borders: { preset: "all", style: "thin", color: border } };
sheet.getRange(`A2:K${data.length + 1}`).format = { fill: pale, wrapText: true, verticalAlignment: "top", borders: { preset: "all", style: "thin", color: border } };
sheet.getRange(`L2:U${data.length + 1}`).format = { fill: gold, wrapText: true, verticalAlignment: "top", borders: { preset: "all", style: "thin", color: border } };
sheet.freezePanes.freezeRows(1);
sheet.freezePanes.freezeColumns(2);
const end = data.length + 1;
sheet.getRange(`L2:L${end}`).dataValidation = { rule: { type: "list", values: ["Valid", "Partially valid", "Invalid"] } };
sheet.getRange(`M2:M${end}`).dataValidation = { rule: { type: "list", values: ["Correct", "Partially correct", "Incorrect"] } };
sheet.getRange(`N2:N${end}`).dataValidation = { rule: { type: "list", values: ["Correct", "Missing dependencies", "Incorrect dependencies"] } };
sheet.getRange(`O2:O${end}`).dataValidation = { rule: { type: "list", values: ["Executable", "Uncertain", "Not executable"] } };
sheet.getRange(`P2:P${end}`).dataValidation = { rule: { type: "list", values: ["Complete", "Partial", "Not complete"] } };
sheet.getRange(`Q2:Q${end}`).dataValidation = { rule: { type: "list", values: ["Yes", "No", "Uncertain"] } };
sheet.getRange(`R2:R${end}`).dataValidation = { rule: { type: "list", values: ["None", "Missing node", "Extra node", "Wrong tool", "Missing edge", "Wrong edge", "Wrong order", "Hallucination", "Other"] } };
const widths = [14, 27, 15, 16, 55, 55, 30, 35, 42, 35, 42, 18, 19, 23, 18, 18, 22, 20, 42, 17, 20];
const letters = "ABCDEFGHIJKLMNOPQRSTU";
for (let i = 0; i < widths.length; i += 1) sheet.getRange(`${letters[i]}:${letters[i]}`).format.columnWidth = widths[i];
sheet.getRange(`2:${end}`).format.rowHeight = 126;
sheet.tables.add(`A1:U${end}`, true, "AdjudicationCases");

const outputPath = path.join(resultDir, "human_annotation_adjudication.xlsx");
const previewPath = path.join(resultDir, "human_annotation_adjudication_preview.png");
const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);
const preview = await workbook.render({ sheetName: "Adjudication", range: "A1:U7", scale: 1, format: "png" });
await fs.writeFile(previewPath, new Uint8Array(await preview.arrayBuffer()));
const check = await workbook.inspect({ kind: "table", range: "Adjudication!A1:U5", include: "values,formulas", tableMaxRows: 5, tableMaxCols: 21, maxChars: 6000 });
console.log(check.ndjson);
const errors = await workbook.inspect({ kind: "match", searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A", options: { useRegex: true, maxResults: 100 }, summary: "formula error scan" });
console.log(errors.ndjson);
