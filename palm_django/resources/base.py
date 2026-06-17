"""
Optional base model for class-level ``palm_resource`` configuration.
"""

from __future__ import annotations

from django.db import models

from palm_django.resources.config import PalmResourceConfig
from palm_django.resources.decorator import PALM_RESOURCE_ATTR


class PalmResourceModel(models.Model):
    """
    Optional abstract base for models that declare ``palm_resource = {...}``.

    Prefer :func:`~palm_django.resources.decorator.as_palm_resource` when a
    decorator reads more naturally.
    """

    class Meta:
        abstract = True

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        palm_cfg = getattr(cls, "palm_resource", None)
        if palm_cfg is not None and not hasattr(cls, PALM_RESOURCE_ATTR):
            setattr(cls, PALM_RESOURCE_ATTR, PalmResourceConfig.from_options(palm_cfg))