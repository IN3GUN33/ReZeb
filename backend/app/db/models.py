# Import all models so Alembic autogenerate can find them
from app.modules.audit.models import AuditEvent  # noqa: F401
from app.modules.auth.models import RefreshToken, User  # noqa: F401
from app.modules.control.models import ConstructionSession, Defect, Photo  # noqa: F401
from app.modules.ntd.models import NTDClause, NTDDocument  # noqa: F401
from app.modules.pto.models import PTOQuery, RegistryItem, RegistrySynonym  # noqa: F401
