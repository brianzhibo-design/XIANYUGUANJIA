"""Dashboard route modules.

Importing this package triggers registration of all route handlers
via their module-level @get/@post/@put/@delete decorators.

New route files should be added to the import list below.
"""

# Route modules — importing triggers decorator-based route registration.
from . import system  # noqa: F401
from . import dashboard_data  # noqa: F401
from . import config  # noqa: F401
from . import messages  # noqa: F401
from . import quote  # noqa: F401
from . import cookie  # noqa: F401
from . import orders  # noqa: F401
from . import products  # noqa: F401
from . import slider  # noqa: F401
from . import rule_suggestions  # noqa: F401
# from . import cookie  # noqa: F401
# from . import quote  # noqa: F401
# from . import messages  # noqa: F401
# from . import products  # noqa: F401
# from . import orders  # noqa: F401
# from . import dashboard_data  # noqa: F401
