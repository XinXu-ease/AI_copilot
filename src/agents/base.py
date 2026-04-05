from pydantic import BaseModel


class BaseAgent:
    """Base class for all agents. Each agent implements its own run() method with agent-specific signature."""
    name: str