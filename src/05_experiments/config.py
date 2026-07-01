import importlib.util
from pathlib import Path

_CONFIG_PATH = Path(__file__).resolve().parents[1] / "config.py"
_SPEC = importlib.util.spec_from_file_location("_wcstats_config", _CONFIG_PATH)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)

for _name in dir(_MODULE):
    if not _name.startswith("_"):
        globals()[_name] = getattr(_MODULE, _name)
