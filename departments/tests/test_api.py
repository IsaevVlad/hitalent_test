from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from departments.models import Department, Employee


class DepartmentAPITestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.root = Department.objects.create(name="Company")
        self.backend = Department.objects.create(name="Backend", parent=self.root)
        self.frontend = Department.objects.create(name="Frontend", parent=self.root)

    def test_create_department(self):
        response = self.client.post(
            "/departments/",
            {"name": "  DevOps  ", "parent_id": self.root.id},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["name"], "DevOps")
        self.assertEqual(response.data["parent_id"], self.root.id)

    def test_create_root_department_without_parent_id(self):
        response = self.client.post(
            "/departments/",
            {"name": "HQ"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIsNone(response.data["parent_id"])

    def test_create_department_duplicate_name_same_parent(self):
        response = self.client.post(
            "/departments/",
            {"name": "Backend", "parent_id": self.root.id},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_employee(self):
        response = self.client.post(
            f"/departments/{self.backend.id}/employees/",
            {"full_name": "John Doe", "position": "Developer"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["full_name"], "John Doe")
        self.assertEqual(response.data["department_id"], self.backend.id)

    def test_create_employee_department_not_found(self):
        response = self.client.post(
            "/departments/9999/employees/",
            {"full_name": "Jane", "position": "QA"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_department_with_tree(self):
        team = Department.objects.create(name="API Team", parent=self.backend)
        Employee.objects.create(
            department=self.backend,
            full_name="Alice",
            position="Lead",
        )

        response = self.client.get(f"/departments/{self.root.id}/?depth=2")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["department"]["name"], "Company")
        self.assertEqual(len(response.data["children"]), 2)

        backend_node = next(
            c for c in response.data["children"] if c["department"]["name"] == "Backend"
        )
        self.assertEqual(len(backend_node["employees"]), 1)
        self.assertEqual(len(backend_node["children"]), 1)
        self.assertEqual(backend_node["children"][0]["department"]["name"], "API Team")

    def test_move_department_cycle_conflict(self):
        response = self.client.patch(
            f"/departments/{self.root.id}/",
            {"parent_id": self.backend.id},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_cascade_delete(self):
        team = Department.objects.create(name="Team", parent=self.backend)
        employee = Employee.objects.create(
            department=team,
            full_name="Bob",
            position="Intern",
        )

        response = self.client.delete(f"/departments/{self.backend.id}/?mode=cascade")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Department.objects.filter(id=self.backend.id).exists())
        self.assertFalse(Department.objects.filter(id=team.id).exists())
        self.assertFalse(Employee.objects.filter(id=employee.id).exists())

    def test_reassign_delete(self):
        employee = Employee.objects.create(
            department=self.backend,
            full_name="Carol",
            position="Dev",
        )
        child = Department.objects.create(name="Sub Team", parent=self.backend)

        response = self.client.delete(
            f"/departments/{self.backend.id}/"
            f"?mode=reassign&reassign_to_department_id={self.frontend.id}"
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        employee.refresh_from_db()
        self.assertEqual(employee.department_id, self.frontend.id)

        child.refresh_from_db()
        self.assertEqual(child.parent_id, self.root.id)
        self.assertFalse(Department.objects.filter(id=self.backend.id).exists())
