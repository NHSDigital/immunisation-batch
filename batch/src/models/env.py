import os

def get_environment():

    _env = os.getenv("ENVIRONMENT")
    non_prod = ["internal-dev", "int", "ref", "sandbox"]
    if _env in non_prod:
        imms_env = _env
    elif _env == "prod":
        imms_env = "prod"
    else:
        # for temporary envs like pr-xx or user workspaces
        imms_env = "internal-dev"
    return imms_env
