import os


def get_environment():
    _env = os.getenv("ENVIRONMENT")
    # default to internal-dev for pr and user workspaces
    return _env if _env in ["internal-dev", "int", "ref", "sandbox", "prod"] else "internal-dev"
