from django.test import TestCase

from departments.models import Department
from departments.services import would_create_cycle


class CycleDetectionTestCase(TestCase):
    def test_would_create_cycle_direct_self(self):
        dept = Department.objects.create(name="A")
        self.assertTrue(would_create_cycle(dept.pk, dept.pk))

    def test_would_create_cycle_in_subtree(self):
        root = Department.objects.create(name="Root")
        child = Department.objects.create(name="Child", parent=root)
        grandchild = Department.objects.create(name="Grandchild", parent=child)

        self.assertTrue(would_create_cycle(root.pk, grandchild.pk))
        self.assertFalse(would_create_cycle(child.pk, root.pk))
