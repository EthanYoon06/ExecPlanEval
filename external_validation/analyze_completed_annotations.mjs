import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const rawDir = path.join(process.cwd(), "external_validation", "results", "human_annotations", "raw");
const inputs = {
  A: path.join(rawDir, "English_Annotation_Table_A_annotated.xlsx"),
  B: path.join(rawDir, "English_Annotation_Table_B_annotated.xlsx"),
};

const fields = [
  "overall_validity",
  "tool_selection",
  "dependency_validity",
  "executability",
  "goal_completion",
  "alternative_valid_plan",
  "primary_error_type",
];

function normalize(value) {
  return String(value ?? "").trim();
}

function kappa(a, b) {
  const n = a.length;
  const agree = a.filter((value, i) => value === b[i]).length;
  const labels = [...new Set([...a, ...b])];
  const pe = labels.reduce((sum, label) => {
    const pa = a.filter((value) => value === label).length / n;
    const pb = b.filter((value) => value === label).length / n;
    return sum + pa * pb;
  }, 0);
  const po = agree / n;
  return { n, agree, observed_agreement: po, expected_agreement: pe, kappa: pe === 1 ? 1 : (po - pe) / (1 - pe) };
}

function mulberry32(seed) {
  return function random() {
    let t = seed += 0x6D2B79F5;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function bootstrapKappa(a, b, iterations = 2000, seed = 20260827) {
  const random = mulberry32(seed);
  const values = [];
  for (let iteration = 0; iteration < iterations; iteration += 1) {
    const left = [];
    const right = [];
    for (let i = 0; i < a.length; i += 1) {
      const index = Math.floor(random() * a.length);
      left.push(a[index]);
      right.push(b[index]);
    }
    values.push(kappa(left, right).kappa);
  }
  values.sort((x, y) => x - y);
  return {
    iterations,
    seed,
    lower_95: values[Math.floor(0.025 * iterations)],
    upper_95: values[Math.floor(0.975 * iterations)],
  };
}

async function readWorkbook(filePath) {
  const workbook = await SpreadsheetFile.importXlsx(await FileBlob.load(filePath));
  const overview = await workbook.inspect({ kind: "workbook,sheet,table", maxChars: 5000, tableMaxRows: 4, tableMaxCols: 16 });
  console.log(`${path.basename(filePath)}\n${overview.ndjson}`);
  const sheet = workbook.worksheets.getItem("Annotations");
  const values = sheet.getRange("A1:P121").values;
  const headers = values[0].map(normalize);
  return values.slice(1).map((row) => Object.fromEntries(headers.map((header, i) => [header, normalize(row[i])])));
}

const records = {};
for (const [key, filePath] of Object.entries(inputs)) records[key] = await readWorkbook(filePath);

const quality = {};
for (const key of ["A", "B"]) {
  const rows = records[key];
  quality[key] = {
    row_count: rows.length,
    unique_annotation_ids: new Set(rows.map((row) => row.annotation_id)).size,
    missing_by_field: Object.fromEntries([...fields, "rationale", "annotator_id"].map((field) => [field, rows.filter((row) => !row[field]).length])),
    annotator_ids: [...new Set(rows.map((row) => row.annotator_id))],
  };
}

const idsA = records.A.map((row) => row.annotation_id);
const idsB = records.B.map((row) => row.annotation_id);
const alignment = {
  same_order: idsA.every((id, i) => id === idsB[i]),
  task_ids_same_order: records.A.every((row, i) => row.task_id === records.B[i].task_id),
};

const agreement = {};
for (const field of fields) {
  const left = records.A.map((row) => row[field]);
  const right = records.B.map((row) => row[field]);
  agreement[field] = kappa(left, right);
  agreement[field].bootstrap_95_ci = bootstrapKappa(left, right);
  agreement[field].distribution_A = Object.fromEntries([...new Set(records.A.map((row) => row[field]))].sort().map((label) => [label, records.A.filter((row) => row[field] === label).length]));
  agreement[field].distribution_B = Object.fromEntries([...new Set(records.B.map((row) => row[field]))].sort().map((label) => [label, records.B.filter((row) => row[field] === label).length]));
}

const allCoreAgreement = records.A.filter((row, i) => fields.slice(0, 5).every((field) => row[field] === records.B[i][field])).length;
const disagreements = records.A.map((row, i) => ({
  annotation_id: row.annotation_id,
  task_id: row.task_id,
  differing_fields: fields.filter((field) => row[field] !== records.B[i][field]),
  A: Object.fromEntries(fields.map((field) => [field, row[field]])),
  B: Object.fromEntries(fields.map((field) => [field, records.B[i][field]])),
})).filter((row) => row.differing_fields.length > 0);

const provenanceDiagnostics = {
  exact_rationale_matches: records.A.filter((row, i) => row.rationale === records.B[i].rationale).length,
  unique_completion_timestamps_A: [...new Set(records.A.map((row) => row.completed_at))],
  unique_completion_timestamps_B: [...new Set(records.B.map((row) => row.completed_at))],
  note: "Workbook metadata alone cannot verify that A and B were completed by different people or independently.",
};

const result = {
  generated_at: new Date().toISOString(),
  input_files: inputs,
  quality,
  alignment,
  agreement,
  all_five_core_fields_agree: { count: allCoreAgreement, total: records.A.length, rate: allCoreAgreement / records.A.length },
  any_seven_field_disagreement: { count: disagreements.length, total: records.A.length, rate: disagreements.length / records.A.length },
  provenance_diagnostics: provenanceDiagnostics,
  disagreements,
};

const outDir = path.join(process.cwd(), "external_validation", "results", "human_annotations");
await fs.mkdir(outDir, { recursive: true });
await fs.writeFile(path.join(outDir, "human_annotation_analysis.json"), JSON.stringify(result, null, 2), "utf8");
await fs.writeFile(path.join(outDir, "annotator_a.jsonl"), records.A.map((row) => JSON.stringify(row)).join("\n") + "\n", "utf8");
await fs.writeFile(path.join(outDir, "annotator_b.jsonl"), records.B.map((row) => JSON.stringify(row)).join("\n") + "\n", "utf8");

console.log(JSON.stringify({ quality, alignment, agreement, all_five_core_fields_agree: result.all_five_core_fields_agree, any_seven_field_disagreement: result.any_seven_field_disagreement }, null, 2));
