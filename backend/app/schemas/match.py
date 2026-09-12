"""Structured output for Claude's stage-2 offer scoring.

This is the exact JSON shape requested from the LLM (Anthropic SDK tool-use /
structured output) — never parsed from free text.
"""
from pydantic import BaseModel, Field


class MatchResult(BaseModel):
    score: int = Field(ge=0, le=100, description="Overall fit score, 0-100.")
    reasoning: str = Field(description="Short explanation grounded in the profile and offer text.")
    missing_skills: list[str] = Field(
        default_factory=list, description="Skills the offer requires that are absent from the stored profile."
    )
    dealbreakers: list[str] = Field(
        default_factory=list, description="Hard mismatches (e.g. required work authorization, seniority, location)."
    )
