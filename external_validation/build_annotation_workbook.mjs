import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const root = process.cwd();
const taskLines = (await fs.readFile(path.join(root, "external_validation/data/external_tasks.jsonl"), "utf8")).trim().split(/\r?\n/).map(JSON.parse);
const planLines = (await fs.readFile(path.join(root, "external_validation/results/natural_plans.jsonl"), "utf8")).trim().split(/\r?\n/).map(JSON.parse);
const taskById = new Map(taskLines.map((task) => [task.task_id, task]));

function stableHash(text) {
  let value = 2166136261;
  for (const char of text) value = Math.imul(value ^ char.charCodeAt(0), 16777619) >>> 0;
  return value;
}

const annotationPlans = planLines
  .filter((record) => Number(record.run) === 1)
  .sort((left, right) => stableHash(left.task_id) - stableHash(right.task_id));

const rows = annotationPlans.map((record, index) => {
  const task = taskById.get(record.task_id);
  const plan = record.plan || { nodes: [], edges: [] };
  const nodeText = (plan.nodes || []).map((node) => `${node.id}. ${node.label}`).join("\n");
  const edgeText = (plan.edges || []).map((edge) => `${edge.source} → ${edge.target}`).join("; ") || "无依赖边";
  return [
    `P${String(index + 1).padStart(4, "0")}`,
    task.task_id,
    task.benchmark,
    task.subset,
    task.instruction,
    `${nodeText}\n依赖边: ${edgeText}`,
    "", "", "", "", "", "", "", "", "", "",
  ];
});

const workbook = Workbook.create();
const protocol = workbook.worksheets.add("Protocol");
const annotations = workbook.worksheets.add("Annotations");
const codebook = workbook.worksheets.add("Codebook");

const navy = "#17365D";
const blue = "#D9EAF7";
const pale = "#F4F7FA";
const gold = "#FFF2CC";
const border = "#B8C4CE";

protocol.showGridLines = false;
protocol.getRange("A1:H1").merge();
protocol.getRange("A1").values = [["外部计划质量独立盲审协议"]];
protocol.getRange("A1:H1").format = { fill: navy, font: { bold: true, color: "#FFFFFF", size: 16 }, rowHeight: 30, verticalAlignment: "center" };
const protocolRows = [
  ["目的", "独立判断候选计划是否正确、可执行并能完成目标。不得查看模型名称、自动分数或官方参考计划。"],
  ["独立性", "标注员 A 与 B 分别填写各自副本；在首次标注结束前不得讨论个案。"],
  ["操作", "只编辑 Annotations 工作表中黄色列。每行必须填写 annotator_id、五个核心判断、替代计划判断及简短理由。"],
  ["边含义", "source → target 表示 target 必须在 source 完成后执行。"],
  ["冲突处理", "先计算 Cohen's κ；分歧项由第三位仲裁员查看双方理由后裁决，原始标注不得覆盖。"],
  ["隐私", "工作簿不包含模型身份和参考答案。task_id 仅用于之后与自动指标连接。"],
];
protocol.getRange(`A3:B${2 + protocolRows.length}`).values = protocolRows;
protocol.getRange("A3:A8").format = { fill: blue, font: { bold: true, color: navy }, verticalAlignment: "top", borders: { preset: "all", style: "thin", color: border } };
protocol.getRange("B3:B8").format = { wrapText: true, verticalAlignment: "top", borders: { preset: "all", style: "thin", color: border } };
protocol.getRange("A:A").format.columnWidth = 18;
protocol.getRange("B:B").format.columnWidth = 90;
protocol.getRange("3:8").format.rowHeight = 42;

const headers = ["annotation_id", "task_id", "benchmark", "subset", "instruction", "candidate_plan", "overall_validity", "tool_selection", "dependency_validity", "executability", "goal_completion", "alternative_valid_plan", "primary_error_type", "rationale", "annotator_id", "completed_at"];
annotations.showGridLines = false;
annotations.getRange(`A1:P${rows.length + 1}`).values = [headers, ...rows];
annotations.getRange("A1:P1").format = { fill: navy, font: { bold: true, color: "#FFFFFF" }, wrapText: true, rowHeight: 34, verticalAlignment: "center", borders: { preset: "all", style: "thin", color: border } };
annotations.getRange(`A2:F${rows.length + 1}`).format = { fill: pale, wrapText: true, verticalAlignment: "top", borders: { preset: "all", style: "thin", color: border } };
annotations.getRange(`G2:P${rows.length + 1}`).format = { fill: gold, wrapText: true, verticalAlignment: "top", borders: { preset: "all", style: "thin", color: border } };
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
for (let col = 0; col < widths.length; col += 1) annotations.getRange(`${letters[col]}:${letters[col]}`).format.columnWidth = widths[col];
annotations.getRange(`2:${rows.length + 1}`).format.rowHeight = 96;
annotations.tables.add(`A1:P${rows.length + 1}`, true, "BlindAnnotations");

codebook.showGridLines = false;
codebook.getRange("A1:D1").merge();
codebook.getRange("A1").values = [["标注字段定义与判定口径"]];
codebook.getRange("A1:D1").format = { fill: navy, font: { bold: true, color: "#FFFFFF", size: 15 }, rowHeight: 28 };
const codeRows = [
  ["字段", "选项", "判定口径", "核心指标"],
  ["overall_validity", "Valid / Partially valid / Invalid", "综合判断；只有关键动作、工具和依赖均成立时选 Valid。", "是"],
  ["tool_selection", "Correct / Partially correct / Incorrect", "所选工具或动作是否适合任务；WorFBench 无显式工具表时按动作语义判断。", "是"],
  ["dependency_validity", "Correct / Missing dependencies / Incorrect dependencies", "检查每条边是否必要，以及是否遗漏会影响执行的前置关系。", "是"],
  ["executability", "Executable / Uncertain / Not executable", "按计划顺序执行时，输入是否可获得、动作是否明确。", "是"],
  ["goal_completion", "Complete / Partial / Not complete", "执行全部节点后是否满足用户完整目标。", "是"],
  ["alternative_valid_plan", "Yes / No / Uncertain", "即使不同于常见方案，该计划是否仍构成合理替代分解。", "否"],
  ["primary_error_type", "下拉菜单", "只选最主要错误；若总体有效则选 None。", "否"],
  ["rationale", "自由文本", "用 1–3 句指出关键证据；避免只写“正确/错误”。", "否"],
];
codebook.getRange(`A3:D${2 + codeRows.length}`).values = codeRows;
codebook.getRange("A3:D3").format = { fill: navy, font: { bold: true, color: "#FFFFFF" }, borders: { preset: "all", style: "thin", color: border } };
codebook.getRange(`A4:D${2 + codeRows.length}`).format = { wrapText: true, verticalAlignment: "top", borders: { preset: "all", style: "thin", color: border } };
codebook.getRange("A:A").format.columnWidth = 24;
codebook.getRange("B:B").format.columnWidth = 40;
codebook.getRange("C:C").format.columnWidth = 75;
codebook.getRange("D:D").format.columnWidth = 14;
codebook.freezePanes.freezeRows(3);

const outDir = path.join(root, "outputs", "execplaneval_external_validation");
await fs.mkdir(outDir, { recursive: true });
const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(path.join(outDir, "blind_annotation_template.xlsx"));
for (const sheetName of ["Protocol", "Annotations", "Codebook"]) {
  const preview = await workbook.render({ sheetName, autoCrop: "all", scale: 1, format: "png" });
  await fs.writeFile(path.join(outDir, `${sheetName}.png`), new Uint8Array(await preview.arrayBuffer()));
}
const inspection = await workbook.inspect({ kind: "sheet,region", maxChars: 5000, tableMaxRows: 8, tableMaxCols: 16 });
console.log(inspection.ndjson);
