import os
os.environ["DATABASE_URL"]="sqlite+pysqlite:///:memory:";os.environ["STORAGE_ROOT"]="/tmp/railbid-test-storage"
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.database.session import Base,get_db
from app.main import app
from app.models import Role,RoleName,User
engine=create_engine("sqlite+pysqlite://",connect_args={"check_same_thread":False},poolclass=StaticPool);TestingSession=sessionmaker(engine,expire_on_commit=False)
@pytest.fixture(autouse=True)
def database(tmp_path):
 Base.metadata.create_all(engine)
 with TestingSession() as db:
  roles={n:Role(name=n) for n in [RoleName.SYSTEM_ADMIN,RoleName.BID_MANAGER,RoleName.PROPOSAL_ENGINEER,RoleName.READ_ONLY]};db.add_all(roles.values());db.flush();db.add_all([User(id=1,email="admin@test",full_name="Admin",roles=[roles[RoleName.SYSTEM_ADMIN]]),User(id=2,email="reader@test",full_name="Reader",roles=[roles[RoleName.READ_ONLY]]),User(id=3,email="manager@test",full_name="Manager",roles=[roles[RoleName.BID_MANAGER]])]);db.commit()
 yield;Base.metadata.drop_all(engine)
def override_db():
 with TestingSession() as db: yield db
app.dependency_overrides[get_db]=override_db
@pytest.fixture
def client(): return TestClient(app)
@pytest.fixture
def bid_payload(): return {"bid_id":"BID-001","tender_reference_no":"T-100","client":"Railways","tender_name":"OHE Package","contract_type":"EPC","project_type":"OHE","tender_due_date":"2026-12-20","bid_manager":"Admin","currency":"INR","current_stage":"Opportunity","bid_status":"Draft"}

@pytest.fixture
def testing_session(): return TestingSession
