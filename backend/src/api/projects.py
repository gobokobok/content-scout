import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependency import CurrentUser
from src.db import get_session
from src.models import Account, AccountList, AnalysisRun, Project
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


class ProjectStatsOut(BaseModel):
    lifetime_items_analyzed: int


class ProjectOut(BaseModel):
    id: uuid.UUID
    name: str
    created_at: datetime
    archived_at: datetime | None
    accounts_count: int

    @classmethod
    def from_model(cls, project: Project, accounts_count: int) -> "ProjectOut":
        return cls(
            id=project.id,
            name=project.name,
            created_at=project.created_at,
            archived_at=project.archived_at,
            accounts_count=accounts_count,
        )


def _accounts_count_subquery():
    return (
        select(func.count(Account.id))
        .select_from(Account)
        .join(AccountList, Account.account_list_id == AccountList.id)
        .where(AccountList.project_id == Project.id)
        .correlate(Project)
        .scalar_subquery()
    )


async def _count_accounts(session: AsyncSession, project_id: uuid.UUID) -> int:
    return int(
        await session.scalar(
            select(func.count(Account.id))
            .select_from(Account)
            .join(AccountList, Account.account_list_id == AccountList.id)
            .where(AccountList.project_id == project_id)
        )
        or 0
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
    return ProjectOut.from_model(project, accounts_count=0)


@router.get("", response_model=list[ProjectOut])
async def list_projects(
    user: CurrentUser, session: SessionDep, include_archived: bool = False
) -> list[ProjectOut]:
    workspace = await get_user_workspace(session, user)
    stmt = select(Project, _accounts_count_subquery()).where(Project.workspace_id == workspace.id)
    if not include_archived:
        stmt = stmt.where(Project.archived_at.is_(None))
    stmt = stmt.order_by(Project.created_at.desc())
    rows = (await session.execute(stmt)).all()
    return [ProjectOut.from_model(p, accounts_count=count) for p, count in rows]


@router.get("/{project_id}", response_model=ProjectOut)
async def get_project(project_id: uuid.UUID, user: CurrentUser, session: SessionDep) -> ProjectOut:
    project = await _get_owned_project(session, user, project_id)
    return ProjectOut.from_model(project, accounts_count=await _count_accounts(session, project.id))


@router.get("/{project_id}/stats", response_model=ProjectStatsOut)
async def get_project_stats(
    project_id: uuid.UUID, user: CurrentUser, session: SessionDep
) -> ProjectStatsOut:
    project = await _get_owned_project(session, user, project_id)
    total = await session.scalar(
        select(func.coalesce(func.sum(AnalysisRun.progress_items), 0)).where(
            AnalysisRun.project_id == project.id
        )
    )
    return ProjectStatsOut(lifetime_items_analyzed=int(total or 0))


@router.patch("/{project_id}", response_model=ProjectOut)
async def update_project(
    project_id: uuid.UUID, body: ProjectUpdateIn, user: CurrentUser, session: SessionDep
) -> ProjectOut:
    project = await _get_owned_project(session, user, project_id)
    project.name = body.name
    await session.commit()
    return ProjectOut.from_model(project, accounts_count=await _count_accounts(session, project.id))


@router.post("/{project_id}/archive", response_model=ProjectOut)
async def archive_project(
    project_id: uuid.UUID, user: CurrentUser, session: SessionDep
) -> ProjectOut:
    project = await _get_owned_project(session, user, project_id)
    if project.archived_at is None:
        project.archived_at = datetime.now(UTC)
    await session.commit()
    return ProjectOut.from_model(project, accounts_count=await _count_accounts(session, project.id))


@router.post("/{project_id}/unarchive", response_model=ProjectOut)
async def unarchive_project(
    project_id: uuid.UUID, user: CurrentUser, session: SessionDep
) -> ProjectOut:
    project = await _get_owned_project(session, user, project_id)
    project.archived_at = None
    await session.commit()
    return ProjectOut.from_model(project, accounts_count=await _count_accounts(session, project.id))
