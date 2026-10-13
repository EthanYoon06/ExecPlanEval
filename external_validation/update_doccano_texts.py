from __future__ import annotations

import json

from setup_doccano_projects import DATA_DIR, PROJECTS, configure_django


def main() -> None:
    configure_django()

    from examples.models import Example
    from projects.models import Project

    for key, spec in PROJECTS.items():
        source = DATA_DIR / f"人工标注_{key}_doccano.jsonl"
        records = [
            json.loads(line)
            for line in source.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        project = Project.objects.get(name=spec["name"])
        examples = list(Example.objects.filter(project=project).order_by("created_at"))
        if len(examples) != len(records):
            raise ValueError(
                f"{project.name}: database has {len(examples)} records, "
                f"but source has {len(records)}"
            )
        for example, record in zip(examples, records):
            example.text = record["text"]
        Example.objects.bulk_update(examples, ["text"])
        print(f"{project.name}: updated {len(examples)} bilingual records")


if __name__ == "__main__":
    main()
