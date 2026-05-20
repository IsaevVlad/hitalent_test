from django.core.exceptions import ValidationError


def validate_non_empty_stripped(value: str, field_name: str) -> str:
    stripped = value.strip()
    if not stripped:
        raise ValidationError({field_name: f"{field_name} must not be empty."})
    if len(stripped) > 200:
        raise ValidationError({field_name: f"{field_name} must be at most 200 characters."})
    return stripped


def would_create_cycle(department_id: int, new_parent_id: int | None) -> bool:
    """Return True if assigning new_parent_id would create a cycle in the tree."""
    if new_parent_id is None:
        return False
    if new_parent_id == department_id:
        return True

    from .models import Department

    current_id = new_parent_id
    visited: set[int] = set()

    while current_id is not None:
        if current_id == department_id:
            return True
        if current_id in visited:
            return True
        visited.add(current_id)
        current_id = (
            Department.objects.filter(pk=current_id)
            .values_list("parent_id", flat=True)
            .first()
        )

    return False
