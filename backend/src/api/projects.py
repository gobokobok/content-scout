import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependency import CurrentUser
from src.db import get_session
from src.models import Project
from src.services.projects import ProjectNotFoundError, get_owned_project
from src.services.workspace import get_user_workspace

router = APIRouter(prefix="/projects", tags=["projects"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]

PROJECT_NOT_FOUND = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail={"code": "project_not_found", "message_ru": "Проект не найден."},
)


class ProjectCreateIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)


class ProjectUpdateIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)


class ProjectOut(BaseModel):
    id: uuid.UUID
    name: str
    created_at: datetime
    archived_at: datetime | None

    @classmethod
    def from_model(cls, project: Project) -> "ProjectOut":
        return cls(
            id=project.id,
            name=project.name,
            created_at=project.created_at,
            archived_at=project.archived_at,
        )


async def _get_owned_project(
    session: AsyncSession, user: CurrentUser, project_id: uuid.UUID
) -> Project:
    try:
        return await get_owned_project(session, user, project_id)
    except ProjectNotFoundError:
        raise PROJECT_NOT_FOUND from None


@router.post("", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
async def create_project(
    body: ProjectCreateIn, user: CurrentUser, session: SessionDep
) -> ProjectOut:
    workspace = await get_user_workspace(session, user)
    project = Project(workspace_id=workspace.id, name=body.name)
    session.add(project)
    await session.commit()
    return ProjectOut.from_model(project)


@router.get("", response_model=list[ProjectOut])
async def list_projects(
    user: CurrentUser, session: SessionDep, include_archived: bool = False
) -> list[ProjectOut]:
    workspace = await get_user_workspace(session, user)
    stmt = select(Project).where(Project.workspace_id == workspace.id)
    if not include_archived:
        stmt = stmt.where(Project.archived_at.is_(None))
    stmt = stmt.order_by(Project.created_at.desc())
    projects = (await session.scalars(stmt)).all()
    return [ProjectOut.from_model(p) for p in projects]


@router.get("/{project_id}", response_model=ProjectOut)
async def get_project(project_id: uuid.UUID, user: CurrentUser, session: SessionDep) -> ProjectOut:
    project = await _get_owned_project(session, user, project_id)
    return ProjectOut.from_model(project)


@router.patch("/{project_id}", response_model=ProjectOut)
async def update_project(
    project_id: uuid.UUID, body: ProjectUpdateIn, user: CurrentUser, session: SessionDep
) -> ProjectOut:
    project = await _get_owned_project(session, user, project_id)
    project.name = body.name
    await session.commit()
    return ProjectOut.from_model(project)


@router.post("/{project_id}/archive", response_model=ProjectOut)
async def archive_project(
    project_id: uuid.UUID, user: CurrentUser, session: SessionDep
) -> ProjectOut:
    project = await _get_owned_project(session, user, project_id)
    if project.archived_at is None:
        project.archived_at = datetime.now(UTC)
    await session.commit()
    return ProjectOut.from_model(project)
