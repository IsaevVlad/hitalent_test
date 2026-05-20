from rest_framework import serializers

from .models import Department, Employee
from .services import validate_non_empty_stripped, would_create_cycle


class DepartmentSerializer(serializers.ModelSerializer):
    parent_id = serializers.PrimaryKeyRelatedField(
        source="parent",
        queryset=Department.objects.all(),
        allow_null=True,
        required=False,
        default=None,
    )

    class Meta:
        model = Department
        fields = ["id", "name", "parent_id", "created_at"]
        read_only_fields = ["id", "created_at"]

    def validate_name(self, value: str) -> str:
        return validate_non_empty_stripped(value, "name")

    def validate(self, attrs: dict) -> dict:
        parent = attrs.get("parent", getattr(self.instance, "parent", None))
        name = attrs.get("name", getattr(self.instance, "name", None))

        if name is not None:
            qs = Department.objects.filter(parent=parent, name=name.strip())
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    {"name": "Department with this name already exists under the same parent."}
                )

        instance_id = self.instance.pk if self.instance else None
        if parent is not None:
            if instance_id and parent.pk == instance_id:
                raise serializers.ValidationError(
                    {"parent_id": "Department cannot be its own parent."}
                )
            if instance_id and would_create_cycle(instance_id, parent.pk):
                raise serializers.ValidationError(
                    {"parent_id": "Cannot move department into its own subtree."}
                )

        return attrs


class DepartmentCreateSerializer(DepartmentSerializer):
    pass


class DepartmentUpdateSerializer(serializers.ModelSerializer):
    parent_id = serializers.PrimaryKeyRelatedField(
        source="parent",
        queryset=Department.objects.all(),
        allow_null=True,
        required=False,
    )

    class Meta:
        model = Department
        fields = ["name", "parent_id"]

    def validate_name(self, value: str) -> str:
        return validate_non_empty_stripped(value, "name")

    def validate(self, attrs: dict) -> dict:
        parent = attrs.get("parent")
        name = attrs.get("name")

        if name is not None or "parent" in attrs:
            effective_parent = parent if "parent" in attrs else self.instance.parent
            effective_name = name if name is not None else self.instance.name
            qs = Department.objects.filter(parent=effective_parent, name=effective_name.strip())
            qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    {"name": "Department with this name already exists under the same parent."}
                )

        if "parent" in attrs:
            new_parent = attrs["parent"]
            if new_parent is not None:
                if new_parent.pk == self.instance.pk:
                    raise serializers.ValidationError(
                        {"parent_id": "Department cannot be its own parent."}
                    )
                if would_create_cycle(self.instance.pk, new_parent.pk):
                    raise serializers.ValidationError(
                        {"parent_id": "Cannot move department into its own subtree."}
                    )

        return attrs


class EmployeeSerializer(serializers.ModelSerializer):
    department_id = serializers.IntegerField(source="department.id", read_only=True)

    class Meta:
        model = Employee
        fields = [
            "id",
            "department_id",
            "full_name",
            "position",
            "hired_at",
            "created_at",
        ]
        read_only_fields = ["id", "department_id", "created_at"]

    def validate_full_name(self, value: str) -> str:
        return validate_non_empty_stripped(value, "full_name")

    def validate_position(self, value: str) -> str:
        return validate_non_empty_stripped(value, "position")


class EmployeeCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Employee
        fields = ["full_name", "position", "hired_at"]

    def validate_full_name(self, value: str) -> str:
        return validate_non_empty_stripped(value, "full_name")

    def validate_position(self, value: str) -> str:
        return validate_non_empty_stripped(value, "position")
