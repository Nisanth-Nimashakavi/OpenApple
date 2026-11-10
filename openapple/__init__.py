"""OpenApple: Human-verified reinforcement protocol for LLMs — the benevolent opposite of OpenWhip."""

__version__ = "0.2.0"
__author__ = "OpenApple Contributors"

from openapple.engine import OpenAppleEngine
from openapple.varieties import get_variety, list_varieties

__all__ = ["OpenAppleEngine", "get_variety", "list_varieties"]
