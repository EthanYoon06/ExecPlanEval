from __future__ import annotations

import json
import os
from pathlib import Path


DB_PATH = "/root/doccano/db.sqlite3"
HERE = Path(__file__).resolve().parent
DATA_DIR = HERE / "doccano"

PROJECTS = {
    "A": {
        "name": "ExecPlanEval-人工标注-A",
        "username": "annotator_a",
        "password": "ExecAnnotatorA2026!",
    },
    "B": {
        "name": "ExecPlanEval-人工标注-B",
        "username": "annotator_b",
        "password": "ExecAnnotatorB2026!",
    },
}


def configure_django() -> None:
    os.environ.setdefault("DATABASE_URL", f"sqlite:///{DB_PATH}")
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")
    import django

    django.setup()


def main() -> None:
    configure_django()

    from django.conf import settings
    from django.contrib.auth.models import User
    from django.db import transaction
    from examples.models import Example
    from label_types.models import CategoryType
    from projects.models import Member, Project, TextClassificationProject
    from roles.models import Role

    labels = [
        line.strip()
        for line in (DATA_DIR / "标签列表.txt").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    guideline = (DATA_DIR / "使用说明.md").read_text(encoding="utf-8")
    admin = User.objects.get(username="admin")
    annotator_role = Role.objects.get(name=settings.ROLE_ANNOTATOR)

    with transaction.atomic():
        for key, spec in PROJECTS.items():
            # Idempotent setup: replace only the projects owned by this script.
            Project.objects.filter(name=spec["name"]).delete()

            user, _ = User.objects.get_or_create(username=spec["username"])
            user.set_password(spec["password"])
            user.is_staff = False
            user.is_superuser = False
            user.save()

            project = TextClassificationProject.objects.create(
                name=spec["name"],
                description=f"标注者{key}独立评估120条任务分解计划；每个维度必须选择一个标签。",
                guideline=guideline,
                created_by=admin,
                project_type="DocumentClassification",
                random_order=False,
                collaborative_annotation=False,
                single_class_classification=False,
                allow_member_to_create_label_type=False,
            )
            project.add_admin()
            Member.objects.create(project=project, user=user, role=annotator_role)
            CategoryType.objects.bulk_create(
                [CategoryType(project=project, text=label) for label in labels]
            )

            source = DATA_DIR / f"人工标注_{key}_doccano.jsonl"
            records = [
                json.loads(line)
                for line in source.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            Example.objects.bulk_create(
                [
                    Example(
                        project=project,
                        text=record["text"],
                        upload_name=source.name,
                    )
                    for record in records
                ]
            )
            print(
                f'{project.id}\t{project.name}\t{spec["username"]}\t'
                f'{len(records)} records\t{len(labels)} labels'
            )


if __name__ == "__main__":
    main()
