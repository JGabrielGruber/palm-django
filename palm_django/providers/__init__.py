"""
Palm provider integrations for Django.
"""

from palm_django.providers.registry import ensure_registered, register_django_model_provider

__all__ = ["ensure_registered", "register_django_model_provider"]