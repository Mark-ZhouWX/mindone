"""Adapted from https://github.com/huggingface/diffusers/tree/main/src/diffusers/pipelines/dit/__init__.py."""

from typing import TYPE_CHECKING

from ...utils import _LazyModule

_import_structure = {"pipeline_dit": ["DiTPipeline"]}

if TYPE_CHECKING:
    from .pipeline_dit import DiTPipeline

else:
    import sys

    sys.modules[__name__] = _LazyModule(
        __name__,
        globals()["__file__"],
        _import_structure,
        module_spec=__spec__,
    )
