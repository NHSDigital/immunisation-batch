""""Functions for obtaining a dictionary of allowed action flags"""

from permissions_checker import get_permissions_config_json_from_s3


def get_supplier_permissions(supplier: str) -> list:
    """
    Returns the permissions for the given supplier.
    Returns an empty list if the permissions config json could not be downloaded, or the supplier has no permissions.
    """
    return get_permissions_config_json_from_s3().get("all_permissions", {}).get(supplier, [])


def get_operation_permissions(supplier: str, vaccine_type: str) -> set:
    """Returns the set of allowed CRUD operations."""
    allowed_permissions = get_supplier_permissions(supplier)
    return (
        {"CREATE", "UPDATE", "DELETE"}
        if f"{vaccine_type}_FULL" in allowed_permissions
        else {perm.split("_")[1] for perm in allowed_permissions if perm.startswith(vaccine_type)}
    )
