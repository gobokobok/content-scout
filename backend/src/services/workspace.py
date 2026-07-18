from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import User, Workspace, WorkspaceMember


class NoWorkspaceError(Exception):
    pass


async def get_user_workspace(session: AsyncSession, user: User) -> Workspace:
    """Every user has exactly one (personal) workspace as of D6; teams are post-MVP."""
    workspace = await session.scalar(
        select(Workspace)
        .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
        .where(WorkspaceMember.user_id == user.id)
    )
    if workspace is None:
        raise NoWorkspaceError(user.id)
    return workspace
