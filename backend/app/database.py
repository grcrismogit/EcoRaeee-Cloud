"""Conexión a PostgreSQL con SQLAlchemy 2.0."""
from sqlalchemy import MetaData, create_engine, event, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import settings

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    # Todas las consultas trabajan sobre el esquema ecoraee
    connect_args={"options": "-csearch_path=ecoraee,public"},
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=True)


class Base(DeclarativeBase):
    metadata = MetaData(schema="ecoraee")


@event.listens_for(Session, "after_begin")
def _fijar_usuario_auditoria(session: Session, transaction, connection) -> None:
    """En cada transacción se informa a PostgreSQL quién opera, para la auditoría
    y el historial de estados (lo leen los triggers con fn_usuario_actual())."""
    id_usuario = session.info.get("id_usuario")
    connection.execute(
        text("SELECT set_config('ecoraee.id_usuario', :u, true)"),
        {"u": str(id_usuario) if id_usuario else ""},
    )


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()  # cierra y descarta cualquier transacción sin confirmar
