from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

_CONFIG_PATH = Path(__file__).resolve().parents[1] / "config.py"
_SPEC = spec_from_file_location("_wcstats_config", _CONFIG_PATH)

if _SPEC is None or _SPEC.loader is None:
    raise ImportError(f"Could not load config from {_CONFIG_PATH}")

_CONFIG = module_from_spec(_SPEC)
_SPEC.loader.exec_module(_CONFIG)

__all__ = [name for name in dir(_CONFIG) if not name.startswith("_")]
globals().update({name: getattr(_CONFIG, name) for name in __all__})
