import os
from pathlib import Path
import subprocess
import sys

REPOSITORY_ROOT = Path(__file__).parents[4]


def test_should_import_the_app_modules_without_a_configuration_file(tmp_path):
    # Arrange
    # A fresh interpreter: in the pytest process these modules are already imported, so importing them again would prove nothing.
    environment = {**os.environ, "CONFIG_FILE": str(tmp_path / "missing.yml")}

    # Act
    result = subprocess.run(
        [sys.executable, "-c", "import api.infrastructure.configuration, api.dependencies, api.app"],
        cwd=REPOSITORY_ROOT,
        env=environment,
        capture_output=True,
        text=True,
    )

    # Assert
    assert result.returncode == 0, result.stderr
