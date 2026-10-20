from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Student(models.Model):
    YEAR_CHOICES = [(year, f'Year {year}') for year in range(1, 5)]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='student_profile')
    student_number = models.CharField(max_length=30, unique=True)
    course = models.CharField(max_length=120, help_text='Program or course, e.g. BS Information Technology.')
    year_level = models.PositiveSmallIntegerField(choices=YEAR_CHOICES, default=1)
    date_enrolled = models.DateField(auto_now_add=True)

    class Meta:
        ordering = ['student_number']

    def __str__(self):
        return f'{self.student_number} - {self.full_name}'

    @property
    def full_name(self):
        name = self.user.get_full_name().strip()
        return name or self.user.get_username()

    @property
    def display_name(self):
        return self.user.first_name.strip() or self.user.get_username()


def student_for(user):
    """Return the Student profile for ``user``, or None when there is none."""
    if not user or not user.is_authenticated:
        return None
    try:
        return user.student_profile
    except Student.DoesNotExist:
        return None


class CampusLocation(models.Model):
    CATEGORY_CLASSROOM_BUILDING = 'Classroom Buildings'
    CATEGORY_ADMIN_OFFICE = 'Admin Office'
    CATEGORY_FACILITY = 'Facility'
    CATEGORY_CANTEEN = 'Canteen'
    CATEGORY_CLINIC = 'Clinic'
    CATEGORY_FIELD = 'Field'
    CATEGORY_OTHER = 'Other'

    CATEGORY_CHOICES = [
        (CATEGORY_CLASSROOM_BUILDING, 'Classroom Buildings'),
        (CATEGORY_ADMIN_OFFICE, 'Admin Office'),
        (CATEGORY_FACILITY, 'Facility'),
        (CATEGORY_CANTEEN, 'Canteen'),
        (CATEGORY_CLINIC, 'Clinic'),
        (CATEGORY_FIELD, 'Field'),
        (CATEGORY_OTHER, 'Other'),
    ]

    CATEGORY_COLORS = {
        CATEGORY_CLASSROOM_BUILDING: '#2f7ee0',
        CATEGORY_ADMIN_OFFICE: '#7c5ce0',
        CATEGORY_FACILITY: '#0ea5a5',
        CATEGORY_CANTEEN: '#ef7b55',
        CATEGORY_CLINIC: '#e5484d',
        CATEGORY_FIELD: '#2f9e63',
        CATEGORY_OTHER: '#64748b',
    }

    location_name = models.CharField(max_length=200)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default=CATEGORY_OTHER)
    description = models.TextField()
    building_floor = models.CharField(max_length=120)
    x_coordinate = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(100.0)],
        help_text='Horizontal position on the campus map, from 0 to 100.',
    )
    y_coordinate = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(100.0)],
        help_text='Vertical position on the campus map, from 0 to 100.',
    )
    office_hours = models.CharField(max_length=120, blank=True)
    contact_person = models.CharField(max_length=120, blank=True)
    image = models.ImageField(upload_to='campus_locations/', blank=True, null=True)
    view_count = models.PositiveIntegerField(default=0, editable=False)
    date_added = models.DateField(auto_now_add=True)

    class Meta:
        ordering = ['location_name']

    def __str__(self):
        return self.location_name

    @property
    def color(self):
        return self.CATEGORY_COLORS.get(self.category, self.CATEGORY_COLORS[self.CATEGORY_OTHER])

    def to_dict(self):
        return {
            'id': self.id,
            'location_name': self.location_name,
            'category': self.category,
            'color': self.color,
            'description': self.description,
            'building_floor': self.building_floor,
            'x_coordinate': self.x_coordinate,
            'y_coordinate': self.y_coordinate,
            'office_hours': self.office_hours,
            'contact_person': self.contact_person,
            'image_url': self.image.url if self.image else None,
            'view_count': self.view_count,
            'date_added': self.date_added.isoformat() if self.date_added else None,
        }
