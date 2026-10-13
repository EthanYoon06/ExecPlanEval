# Annotation provenance packet

This directory is an audit aid, not evidence that the declarations have been completed.
Each contributor must personally complete the corresponding declaration. The study author
must not sign on another contributor's behalf.

A Chinese, signature-ready packet is available at
`output/docx/人工标注来源与独立性证明材料包.docx`. It combines the three personal
declarations, a custodian verification page, artifact hashes, privacy guidance, and a final
submission checklist. Blank identity, experience, assistance, timing, and signature fields are
intentional and must be completed by the relevant people.

## Immutable source hashes

| Artifact | SHA-256 |
|---|---|
| `English_Annotation_Table_A_annotated.xlsx` | `0100EC7CD2FFBC4DB415EEE1694359A22F6F367BCEA7ECE1CA16B12363C7E78A` |
| `English_Annotation_Table_B_annotated.xlsx` | `FBAFB8E73FE0905E241D87EC1559D46FB41C05E671408B2728B662E97D83AA8C` |
| `adjudication_completed.csv` | `950BE1499EB98F2F3FCC592CEC377BA2CB44DA0FE2D57F6A9674C78213DF49C5` |

The two XLSX files report `openpyxl` as creator and share the same package creation time.
Those metadata identify the export process, not a person, and cannot establish independent
human work.

## Required completion procedure

1. Contributor A, Contributor B, and the adjudicator each complete their own declaration.
2. Each person supplies a stable pseudonymous ID, relevant experience, start/end dates,
   assistance used, and conflict/consultation disclosures.
3. Each person signs and dates the declaration. A cryptographic or institutional signature
   may be stored privately if public release would reveal identity.
4. The corresponding source-file hash must be copied into the signed declaration.
5. A study custodian records how identity was verified and releases only the de-identified
   statement where required by ethics or privacy rules.

Until these steps are complete, the manuscript must use “paired annotation passes” and
“adjudicated label layer,” not “independent human ground truth.”
