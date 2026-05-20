import logging

from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Department, Employee
from .serializers import (
    DepartmentCreateSerializer,
    DepartmentSerializer,
    DepartmentUpdateSerializer,
    EmployeeCreateSerializer,
    EmployeeSerializer,
)

logger = logging.getLogger("departments")


def build_department_tree(
    department: Department,
    depth: int,
    include_employees: bool,
) -> dict:
    data = {
        "department": DepartmentSerializer(department).data,
        "employees": [],
        "children": [],
    }

    if include_employees:
        employees = department.employees.order_by("created_at", "full_name")
        data["employees"] = EmployeeSerializer(employees, many=True).data

    if depth > 0:
        children = department.children.all()
        data["children"] = [
            build_department_tree(child, depth - 1, include_employees)
            for child in children
        ]

    return data


class DepartmentListCreateView(APIView):
    def post(self, request: Request) -> Response:
        serializer = DepartmentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        department = serializer.save()
        logger.info("Created department id=%s name=%s", department.id, department.name)
        return Response(DepartmentSerializer(department).data, status=status.HTTP_201_CREATED)


class DepartmentDetailView(APIView):
    def get(self, request: Request, pk: int) -> Response:
        department = get_object_or_404(Department, pk=pk)

        try:
            depth = int(request.query_params.get("depth", 1))
        except (TypeError, ValueError):
            return Response(
                {"depth": "Must be an integer."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if depth < 0 or depth > 5:
            return Response(
                {"depth": "Must be between 0 and 5."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        include_employees = request.query_params.get("include_employees", "true").lower()
        if include_employees not in ("true", "false", "1", "0"):
            return Response(
                {"include_employees": "Must be a boolean."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        include_employees_bool = include_employees in ("true", "1")

        data = build_department_tree(department, depth, include_employees_bool)
        return Response(data)

    def patch(self, request: Request, pk: int) -> Response:
        department = get_object_or_404(Department, pk=pk)
        serializer = DepartmentUpdateSerializer(department, data=request.data, partial=True)
        if not serializer.is_valid():
            if "parent_id" in serializer.errors and any(
                "subtree" in str(err) or "own parent" in str(err)
                for err in serializer.errors["parent_id"]
            ):
                return Response(serializer.errors, status=status.HTTP_409_CONFLICT)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        department = serializer.save()
        logger.info("Updated department id=%s", department.id)
        return Response(DepartmentSerializer(department).data)

    @transaction.atomic
    def delete(self, request: Request, pk: int) -> Response:
        department = get_object_or_404(Department, pk=pk)
        mode = request.query_params.get("mode")

        if mode not in ("cascade", "reassign"):
            return Response(
                {"mode": "Required query parameter. Allowed values: cascade, reassign."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if mode == "cascade":
            logger.info("Cascade delete department id=%s", department.id)
            department.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        reassign_to_id = request.query_params.get("reassign_to_department_id")
        if not reassign_to_id:
            return Response(
                {"reassign_to_department_id": "Required when mode=reassign."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            reassign_to_id = int(reassign_to_id)
        except (TypeError, ValueError):
            return Response(
                {"reassign_to_department_id": "Must be an integer."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if reassign_to_id == department.pk:
            return Response(
                {"reassign_to_department_id": "Cannot reassign to the department being deleted."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        target = get_object_or_404(Department, pk=reassign_to_id)

        Employee.objects.filter(department=department).update(department=target)
        department.children.update(parent=department.parent)
        logger.info(
            "Reassign delete department id=%s, employees moved to id=%s",
            department.id,
            target.id,
        )
        department.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class DepartmentEmployeeCreateView(APIView):
    def post(self, request: Request, pk: int) -> Response:
        department = get_object_or_404(Department, pk=pk)
        serializer = EmployeeCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        employee = serializer.save(department=department)
        logger.info(
            "Created employee id=%s in department id=%s",
            employee.id,
            department.id,
        )
        return Response(EmployeeSerializer(employee).data, status=status.HTTP_201_CREATED)
