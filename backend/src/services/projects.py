import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Project, User
from src.services.workspace import get_user_workspace


class ProjectNotFoundError(Exception):
    pass


async def get_owned_project(session: AsyncSession, user: User, project_id: uuid.UUID) -> Project:
    """The caller's project, scoped to their workspace. Raises for foreign/missing ids."""
    workspace = await get_user_workspace(session, user)
    project = await session.scalar(
        select(Project).where(Project.id == project_id, Project.workspace_id == workspace.id)
    )
    if project is None:
        raise ProjectNotFoundError(project_id)
    return project
