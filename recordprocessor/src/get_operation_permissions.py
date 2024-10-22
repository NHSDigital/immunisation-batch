""""Functions for obtaining a dictionary of allowed action flags"""

from mappings import Vaccine


def get_operation_permissions(vaccine: Vaccine, permission: str) -> set:
    """Returns the set of allowed action flags."""
    return (
        {"CREATE", "UPDATE", "DELETE"}
        if f"{vaccine.value}_FULL" in permission
        else {perm.split("_")[1] for perm in permission if perm.startswith(vaccine.value)}
    )
