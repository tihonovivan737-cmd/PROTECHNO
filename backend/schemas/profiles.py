from __future__ import annotations

from pydantic import BaseModel

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.modules.profiles.registry import Profile


class ProfileResponse(BaseModel):
    name: str
    title: str
    system: str
    example_input: str
    example_output: str

    @classmethod
    def from_profile(cls, p: Profile) -> ProfileResponse:
        return cls(
            name=p.name,
            title=p.title,
            system=p.system,
            example_input=p.example_input,
            example_output=p.example_output,
        )
