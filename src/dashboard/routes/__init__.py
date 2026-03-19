"""Dashboard route modules.

Importing this package triggers registration of all route handlers
via their module-level @get/@post/@put/@delete decorators.

New route files should be added to the import list below.
"""

# Route modules — importing triggers decorator-based route registration.
from . import (
    config,  # noqa: F401
    cookie,  # noqa: F401
    dashboard_data,  # noqa: F401
    messages,  # noqa: F401
    orders,  # noqa: F401
    products,  # noqa: F401
    quote,  # noqa: F401
    rule_suggestions,  # noqa: F401
    slider,  # noqa: F401
    system,  # noqa: F401
)
# from . import cookie
# from . import quote
# from . import messages
# from . import products
# from . import orders
# from . import dashboard_data
