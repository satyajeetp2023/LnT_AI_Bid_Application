from sqlalchemy import select
from app.database.session import SessionLocal
from app.models import Role,RoleName,User
def run():
 with SessionLocal() as db:
  roles={r.name:r for r in db.scalars(select(Role)).all()}
  for name in RoleName:
   if name not in roles: roles[name]=Role(name=name); db.add(roles[name])
  db.flush()
  if not db.scalar(select(User).where(User.email=="admin@railbid.local")): db.add(User(email="admin@railbid.local",full_name="Aarav Sharma",roles=[roles[RoleName.SYSTEM_ADMIN]])); db.add(User(email="viewer@railbid.local",full_name="Demo Reviewer",roles=[roles[RoleName.READ_ONLY]]))
  db.commit()
if __name__=="__main__": run()

