"""MultiLanguage - composed from mixins."""

"""
MultiLanguage — Generate code in TypeScript, Go, and Kotlin from YAML entities.

Problem: All generated code is Python-only. Many users need APIs in
TypeScript (Express/NestJS), Go (Gin), or Kotlin (Spring/Ktor).

Solution: MultiLanguage takes entity definitions from niche YAML files
and generates complete API projects in multiple languages:
  - TypeScript: Express + TypeORM + Swagger
  - Go: Gin + GORM + Swagger
  - Kotlin: Spring Boot + JPA + Swagger

M10 Implementation: Uses entity field types from YAML, maps them to
target language types, and generates complete CRUD services.
No external APIs needed — pure code generation.
"""

import logging
from typing import Any, Optional

logger = logging.getLogger("zenic_agents.multi_language")

from ._core_mixin import MultiLanguageCoreMixin
from ._extra_mixin import MultiLanguageExtraMixin
from ._types import TYPE_MAP

__all__ = ["TYPE_MAP", "Any", "MultiLanguage", "Optional"]


class MultiLanguage(MultiLanguageCoreMixin, MultiLanguageExtraMixin):
    pass
