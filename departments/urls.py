from django.urls import path

from .views import DepartmentDetailView, DepartmentEmployeeCreateView, DepartmentListCreateView

urlpatterns = [
    path("departments/", DepartmentListCreateView.as_view(), name="department-list-create"),
    path("departments/<int:pk>/", DepartmentDetailView.as_view(), name="department-detail"),
    path(
        "departments/<int:pk>/employees/",
        DepartmentEmployeeCreateView.as_view(),
        name="department-employee-create",
    ),
]
