"""Adaptador de compatibilidad para utilidades de notebooks.

Permite que imports como `from utils_shared import ...` funcionen desde la raíz.
"""

from notebooks.utils_shared import *  # noqa: F401,F403
