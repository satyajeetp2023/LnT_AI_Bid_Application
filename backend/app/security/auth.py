from enum import StrEnum
from fastapi import Header, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models import ProjectMembership, RoleName, User

class Permission(StrEnum):
    CREATE_BID="create_bid"; EDIT_BID="edit_bid"; UPLOAD_DOCUMENT="upload_document"; VIEW_DOCUMENT="view_document"; DOWNLOAD_DOCUMENT="download_document"; CLASSIFY_DOCUMENT="classify_document"; ARCHIVE_DOCUMENT="archive_document"; MANAGE_MEMBERS="manage_project_members"; VIEW_AUDIT="view_audit_log"; REQUIREMENT_VIEW="requirement_view"; REQUIREMENT_MANAGE="requirement_manage"; MISSING_INPUT_VIEW="missing_input_view"; MISSING_INPUT_MANAGE="missing_input_manage"; PRE_BID_QUERY_VIEW="pre_bid_query_view"; PRE_BID_QUERY_MANAGE="pre_bid_query_manage"; PRE_BID_QUERY_APPROVE="pre_bid_query_approve"; PREPARED_ARTIFACT_VIEW="prepared_artifact_view"; PREPARED_ARTIFACT_MANAGE="prepared_artifact_manage"; PREPARED_ARTIFACT_APPROVE="prepared_artifact_approve"

VIEW={Permission.MISSING_INPUT_VIEW,Permission.PRE_BID_QUERY_VIEW,Permission.PREPARED_ARTIFACT_VIEW};MANAGE={Permission.MISSING_INPUT_VIEW,Permission.MISSING_INPUT_MANAGE,Permission.PRE_BID_QUERY_VIEW,Permission.PRE_BID_QUERY_MANAGE,Permission.PREPARED_ARTIFACT_VIEW,Permission.PREPARED_ARTIFACT_MANAGE}
ROLE_PERMISSIONS={
 RoleName.SYSTEM_ADMIN:set(Permission),
 RoleName.BID_MANAGER:{Permission.CREATE_BID,Permission.EDIT_BID,Permission.UPLOAD_DOCUMENT,Permission.VIEW_DOCUMENT,Permission.DOWNLOAD_DOCUMENT,Permission.CLASSIFY_DOCUMENT,Permission.ARCHIVE_DOCUMENT,Permission.MANAGE_MEMBERS,Permission.REQUIREMENT_VIEW,Permission.REQUIREMENT_MANAGE,Permission.PRE_BID_QUERY_APPROVE,Permission.PREPARED_ARTIFACT_APPROVE}|MANAGE,
 RoleName.PROPOSAL_ENGINEER:{Permission.UPLOAD_DOCUMENT,Permission.VIEW_DOCUMENT,Permission.DOWNLOAD_DOCUMENT,Permission.CLASSIFY_DOCUMENT,Permission.REQUIREMENT_VIEW,Permission.REQUIREMENT_MANAGE}|MANAGE,
 RoleName.PLANNING:{Permission.VIEW_DOCUMENT,Permission.DOWNLOAD_DOCUMENT,Permission.REQUIREMENT_VIEW}|VIEW, RoleName.ENGINEERING:{Permission.VIEW_DOCUMENT,Permission.DOWNLOAD_DOCUMENT,Permission.REQUIREMENT_VIEW}|VIEW, RoleName.CONTRACTS:{Permission.VIEW_DOCUMENT,Permission.DOWNLOAD_DOCUMENT,Permission.CLASSIFY_DOCUMENT,Permission.REQUIREMENT_VIEW,Permission.REQUIREMENT_MANAGE}|MANAGE, RoleName.COMMERCIAL:{Permission.VIEW_DOCUMENT,Permission.DOWNLOAD_DOCUMENT,Permission.REQUIREMENT_VIEW}|VIEW, RoleName.PROCUREMENT:{Permission.VIEW_DOCUMENT,Permission.DOWNLOAD_DOCUMENT,Permission.REQUIREMENT_VIEW}|VIEW, RoleName.FINANCE:{Permission.VIEW_DOCUMENT,Permission.DOWNLOAD_DOCUMENT,Permission.REQUIREMENT_VIEW}|VIEW, RoleName.MANAGEMENT_REVIEWER:{Permission.VIEW_DOCUMENT,Permission.DOWNLOAD_DOCUMENT,Permission.REQUIREMENT_VIEW,Permission.PRE_BID_QUERY_APPROVE,Permission.PREPARED_ARTIFACT_APPROVE}|VIEW, RoleName.READ_ONLY:{Permission.VIEW_DOCUMENT,Permission.DOWNLOAD_DOCUMENT,Permission.REQUIREMENT_VIEW}|VIEW,
}
def current_user(db:Session,x_user_id:int=Header(default=1,alias="X-User-ID"))->User:
 user=db.get(User,x_user_id)
 if not user or not user.is_active: raise HTTPException(401,"Invalid development identity")
 return user
def is_admin(user:User)->bool: return any(r.name==RoleName.SYSTEM_ADMIN for r in user.roles)
def require_permission(user:User,permission:Permission)->None:
 if not any(permission in ROLE_PERMISSIONS.get(r.name,set()) for r in user.roles): raise HTTPException(403,f"Permission denied: {permission.value}")
def require_project_access(db:Session,user:User,project_id:int,permission:Permission)->None:
 require_permission(user,permission)
 if is_admin(user): return
 member=db.scalar(select(ProjectMembership).where(ProjectMembership.bid_project_id==project_id,ProjectMembership.user_id==user.id))
 if not member: raise HTTPException(403,"You are not assigned to this bid project")
