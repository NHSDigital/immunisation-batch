""""Functions for obtaining a dictionary of allowed action flags"""


def get_operation_permissions(vaccine_type: str, permission: str) -> set:
    """Returns the set of allowed action flags."""
    return (
        {"NEW", "UPDATE", "DELETE"}
        if f"{vaccine_type}_FULL" in permission
        else {
            perm.split("_")[1].replace("CREATE", "NEW") for perm in permission if perm.startswith(vaccine_type)
        }
    )
