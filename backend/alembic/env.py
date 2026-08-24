from logging.config import fileConfig
from alembic import context
from sqlalchemy import engine_from_config,pool
from app.database.session import Base
from app.models import models
from app.core.config import get_settings
config=context.config; config.set_main_option("sqlalchemy.url",get_settings().database_url)
if config.config_file_name: fileConfig(config.config_file_name)
target_metadata=Base.metadata
def run_migrations_offline(): context.configure(url=config.get_main_option("sqlalchemy.url"),target_metadata=target_metadata,literal_binds=True); context.run_migrations()
def run_migrations_online():
 with engine_from_config(config.get_section(config.config_ini_section),prefix="sqlalchemy.",poolclass=pool.NullPool).connect() as connection: context.configure(connection=connection,target_metadata=target_metadata); context.run_migrations()
run_migrations_offline() if context.is_offline_mode() else run_migrations_online()

