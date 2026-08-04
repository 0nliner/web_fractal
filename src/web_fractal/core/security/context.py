from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class UserPrincipal:
    id: Any = None
    roles: list[str] = field(default_factory=list)
    organization_id: Optional[Any] = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class EnvContext:
    ip: Optional[str] = None
    tenant: Optional[str] = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class SecurityContext:
    user: UserPrincipal
    environment: EnvContext = field(default_factory=EnvContext)

    @classmethod
    async def build(cls, user: UserPrincipal, session: Any = None) -> "SecurityContext":
        return cls(user=user)
