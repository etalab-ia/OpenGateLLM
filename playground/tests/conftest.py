import os
from pathlib import Path

os.environ["CONFIG_FILE"] = str(Path(__file__).parents[2] / "config.example.yml")
