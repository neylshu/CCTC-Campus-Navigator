from django.urls import path
from . import api, views

urlpatterns = [
    path('', views.index, name='index'),
    path('students/signup/', views.student_signup, name='student_signup'),
    path('students/signin/', views.student_login, name='student_login'),
    path('students/signout/', views.student_logout, name='student_logout'),
    path('locations/add/', views.add_location, name='add_location'),
    path('locations/<int:pk>/edit/', views.edit_location, name='edit_location'),
    path('locations/<int:pk>/delete/', views.delete_location, name='delete_location'),
    path('api/locations/', api.location_list, name='api_location_list'),
    path('api/locations/<int:pk>/', api.location_detail, name='api_location_detail'),
    path('api/locations/<int:pk>/view/', api.location_view_ping, name='api_location_view'),
]
