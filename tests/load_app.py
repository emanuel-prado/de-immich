import importlib.util
import sys
from pathlib import Path


def load_app():
    script = Path(__file__).parents[1] / "de-immich.py"
    spec = importlib.util.spec_from_file_location("de_immich", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module

