"""
prompt_renderer.py -- iios.ai.prompt_context.composer
========================================================
:class:`PromptRenderer` -- safe variable substitution for prompt
templates.  Uses a restricted ``{{variable_name}}`` regex substitution
(no ``eval``/``exec``/format-string injection surface) so template
rendering can never execute arbitrary code, per OWASP guidance on
template injection.

A3 Prompt & Context Platform -- Phase 3, Module 3
"""
from __future__ import annotations

import re
from typing import List

from ..core.prompt_variables import PromptVariables
from ..core.prompt_version   import PromptVersion
from ..exceptions            import AIMissingVariableError

_VARIABLE_PATTERN = re.compile(r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}")


class PromptRenderer:
    """Renders a :class:`PromptVersion`'s template text against :class:`PromptVariables`."""

    def render(self, version: PromptVersion, variables: PromptVariables) -> str:
        """
        Raises
        ------
        AIMissingVariableError
            If a variable declared by the template (or referenced in the
            template text) is not present in ``variables``.
        """
        missing_declared: List[str] = [v for v in version.variables if v not in variables]
        if missing_declared:
            raise AIMissingVariableError(
                f"Missing declared variables for prompt {version.prompt_id!r}: {missing_declared}"
            )

        def _substitute(match: "re.Match[str]") -> str:
            key = match.group(1)
            if key not in variables:
                raise AIMissingVariableError(
                    f"Unresolved variable '{{{{{key}}}}}' in template for prompt "
                    f"{version.prompt_id!r}."
                )
            return str(variables.get(key))

        return _VARIABLE_PATTERN.sub(_substitute, version.template_text)
