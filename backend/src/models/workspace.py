import enum
import uuid

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, CreatedAt, UuidPk


class WorkspaceKind(enum.StrEnum):
    personal = "personal"
    team = "team"


class WorkspaceRole(enum.StrEnum):
    owner = "owner"


class Workspace(UuidPk, CreatedAt, Base):
    __tablename__ = "workspaces"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    kind: Mapped[WorkspaceKind] = mapped_column(
        Enum(WorkspaceKind, native_enum=False, length=20),
        default=WorkspaceKind.personal,
        nullable=False,
    )


class WorkspaceMember(CreatedAt, Base):
    __tablename__ = "workspace_members"

    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id"), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), primary_key=True, index=True)
    role: Mapped[WorkspaceRole] = mapped_column(
        Enum(WorkspaceRole, native_enum=False, length=20),
        default=WorkspaceRole.owner,
        nullable=False,
    )
