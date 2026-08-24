from fastapi import Header, HTTPException
from sqlalchemy.orm import Session
from app.models import User

WRITE_ROLES={"System Admin","Bid Manager","Proposal Engineer"}
def current_user(db: Session, x_user_id: int=Header(default=1)) -> User:
    user=db.get(User,x_user_id)
    if not user or not user.is_active: raise HTTPException(401,"Invalid development identity")
    return user
def require_write(user: User):
    if not ({r.name.value for r in user.roles} & WRITE_ROLES): raise HTTPException(403,"This role has read-only access")

