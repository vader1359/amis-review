"""Run Terraform's native mock-provider policy tests without Google credentials.

Set PSI_TERRAFORM_BIN to the checksum-verified Terraform 1.13.5 executable.
No apply, cloud API access, or real readiness assertion is performed.
"""

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest


def _assert_resource_allowlist(changes: list[dict]) -> None:
    """Reject unexpected privileges/compute using the actual planned graph."""
    permitted = {
        "terraform_data.readiness",
        "google_cloud_tasks_queue.dispatch",
        "google_artifact_registry_repository.images",
        *(
            f'google_service_account.runtime["{role}"]'
            for role in ("api", "worker", "dispatcher")
        ),
        *(
            f'google_storage_bucket.preview["{bucket}"]'
            for bucket in ("staging", "artifacts")
        ),
        *(
            f'google_project_iam_custom_role.objects["{role}"]'
            for role in ("create", "read")
        ),
        *(
            f'google_storage_bucket_iam_member.objects["{grant}"]'
            for grant in (
                "api_staging_create",
                "worker_staging_read",
                "worker_artifacts_write",
                "api_artifacts_read",
            )
        ),
        *(
            f'google_project_service.required["{api}.googleapis.com"]'
            for api in ("artifactregistry", "cloudtasks", "cloudkms", "iam", "storage")
        ),
    }
    assert {change["address"] for change in changes} == permitted
    for change in changes:
        values = change["change"]["after"]
        if change["type"] == "google_storage_bucket_iam_member":
            assert values["member"].startswith("serviceAccount:")
            assert values["role"].startswith(
                "projects/amis-psi-preview-20260905/roles/psiPreviewObject"
            )


def test_cloud_bootstrap_native_policy(tmp_path: Path) -> None:
    executable = os.environ.get("PSI_TERRAFORM_BIN") or shutil.which("terraform")
    if not executable:
        pytest.skip("Terraform 1.13.5 unavailable; run the native policy gate")
    source = Path(__file__).resolve().parents[2] / "infra" / "terraform" / "preview"
    module = tmp_path / "preview"
    shutil.copytree(
        source,
        module,
        ignore=shutil.ignore_patterns(".terraform", "*.tfstate*", "*.tfvars*"),
    )
    # Ignore TF_VAR_* and provider credentials; native tests use a mock provider.
    environment = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("TF_", "GOOGLE_", "GCLOUD_", "CLOUDSDK_"))
    }
    environment.update(TF_IN_AUTOMATION="1", TF_INPUT="0")
    for arguments in (
        ["init", "-backend=false", "-lockfile=readonly", "-no-color"],
        ["validate", "-no-color"],
        ["test", "-no-color"],
        ["test", "-json", "-verbose", "-filter=tests/foundation.tftest.hcl"],
    ):
        result = subprocess.run(
            [executable, f"-chdir={module}", *arguments],
            env=environment,
            text=True,
            capture_output=True,
            timeout=180,
            check=False,
        )
        assert result.returncode == 0, (result.stdout + result.stderr)[-12000:]
    plans = [
        item["test_plan"]
        for line in result.stdout.splitlines()
        if (item := json.loads(line)).get("type") == "test_plan"
    ]
    assert len(plans) == 1
    _assert_resource_allowlist(plans[0]["resource_changes"])
