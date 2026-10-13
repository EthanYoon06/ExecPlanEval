import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const file = await FileBlob.load("outputs/execplaneval_external_validation/blind_annotation_template.xlsx");
const workbook = await SpreadsheetFile.importXlsx(file);
const formulas = await workbook.inspect({ kind: "formula", maxChars: 3000, options: { maxResults: 100 } });
const errors = await workbook.inspect({ kind: "match", searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A", searchOptions: { useRegex: true }, maxChars: 3000, options: { maxResults: 100 } });
console.log("FORMULAS\n" + formulas.ndjson);
console.log("ERROR_SCAN\n" + errors.ndjson);
