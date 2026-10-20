from django.contrib import admin

from .models import CampusLocation, Student


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
	list_display = ('student_number', 'full_name', 'course', 'year_level', 'date_enrolled')
	search_fields = ('student_number', 'course', 'user__first_name', 'user__last_name', 'user__username')
	list_filter = ('course', 'year_level')


@admin.register(CampusLocation)
class CampusLocationAdmin(admin.ModelAdmin):
	list_display = ('location_name', 'category', 'building_floor', 'office_hours', 'contact_person', 'view_count', 'date_added')
	list_filter = ('category', 'date_added')
	search_fields = ('location_name', 'description', 'building_floor', 'contact_person')
	readonly_fields = ('view_count',)
	fieldsets = (
		('Location details', {
			'fields': ('location_name', 'category', 'description', 'building_floor', 'image'),
		}),
		('Map position', {
			'description': 'Use percentages from 0 to 100. X controls left-to-right position; Y controls top-to-bottom position.',
			'fields': ('x_coordinate', 'y_coordinate'),
		}),
		('Contact information', {
			'fields': ('office_hours', 'contact_person'),
		}),
	)
