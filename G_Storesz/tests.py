import json

from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import CampusLocation, Student

User = get_user_model()


def sample_payload(**overrides):
	payload = {
		'location_name': 'Library',
		'category': CampusLocation.CATEGORY_FACILITY,
		'description': 'A quiet place to study.',
		'building_floor': 'Ground floor',
		'x_coordinate': '25',
		'y_coordinate': '40',
		'office_hours': '8 AM - 6 PM',
		'contact_person': 'Library desk',
	}
	payload.update(overrides)
	return payload


def make_location(**overrides):
	fields = {
		'location_name': 'Registrar\'s Office',
		'category': CampusLocation.CATEGORY_ADMIN_OFFICE,
		'description': 'Handles enrolment and records.',
		'building_floor': 'Main Building, 1st Floor',
		'x_coordinate': 20,
		'y_coordinate': 30,
	}
	fields.update(overrides)
	return CampusLocation.objects.create(**fields)


def student_payload(**overrides):
	payload = {
		'first_name': 'Maria',
		'last_name': 'Santos',
		'student_number': '2026-00123',
		'course': 'BS Information Technology',
		'year_level': '2',
		'email': 'maria@cctc.edu.ph',
		'password1': 'campus-student-123',
		'password2': 'campus-student-123',
	}
	payload.update(overrides)
	return payload


class AuthenticationTests(TestCase):
	def setUp(self):
		self.user = User.objects.create_user(username='registrar', password='campus-pass-123')

	def test_login_page_renders(self):
		response = self.client.get('/accounts/login/')

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Staff sign in')
		self.assertContains(response, 'name="username"')

	def test_manage_views_redirect_anonymous_users_to_login(self):
		location = make_location()
		urls = (
			'/locations/add/',
			f'/locations/{location.pk}/edit/',
			f'/locations/{location.pk}/delete/',
		)

		for url in urls:
			with self.subTest(url=url):
				response = self.client.get(url)
				self.assertRedirects(response, f'/accounts/login/?next={url}')

	def test_index_shows_sign_in_link_for_anonymous_and_sign_out_for_staff(self):
		anonymous = self.client.get('/')
		self.assertContains(anonymous, 'Staff sign in')
		self.assertNotContains(anonymous, 'Sign out')

		self.client.login(username='registrar', password='campus-pass-123')
		signed_in = self.client.get('/')
		self.assertContains(signed_in, 'Sign out')
		self.assertContains(signed_in, 'Add a location')

	def test_sign_in_add_location_then_sign_out(self):
		response = self.client.post('/accounts/login/', {
			'username': 'registrar',
			'password': 'campus-pass-123',
			'next': '/',
		})
		self.assertRedirects(response, '/')
		self.assertEqual(int(self.client.session['_auth_user_id']), self.user.pk)

		page = self.client.get('/locations/add/')
		self.assertEqual(page.status_code, 200)

		created = self.client.post('/locations/add/', sample_payload())
		self.assertRedirects(created, '/')
		self.assertTrue(CampusLocation.objects.filter(location_name='Library').exists())

		logout = self.client.post('/accounts/logout/')
		self.assertRedirects(logout, '/')

		blocked = self.client.get('/locations/add/')
		self.assertRedirects(blocked, '/accounts/login/?next=/locations/add/')

	def test_login_rejects_bad_password(self):
		response = self.client.post('/accounts/login/', {
			'username': 'registrar',
			'password': 'wrong-password',
		})

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Please enter a correct username and password')
		self.assertNotEqual(int(self.client.session.get('_auth_user_id', 0)), self.user.pk)


class CampusLocationViewsTests(TestCase):
	def setUp(self):
		User.objects.create_user(username='registrar', password='campus-pass-123')
		self.client.login(username='registrar', password='campus-pass-123')

	def test_add_location_saves_and_renders_location(self):
		response = self.client.post('/locations/add/', sample_payload())

		self.assertRedirects(response, '/')
		self.assertTrue(CampusLocation.objects.filter(location_name='Library').exists())
		rendered = self.client.get('/')
		self.assertContains(rendered, 'Library')
		self.assertContains(rendered, 'A quiet place to study.')

	def test_add_location_requires_required_fields(self):
		response = self.client.post('/locations/add/', {})

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'This field is required.')
		self.assertEqual(CampusLocation.objects.count(), 0)

	def test_edit_location_updates_details_and_pin(self):
		location = make_location()

		page = self.client.get(f'/locations/{location.pk}/edit/')
		self.assertContains(page, 'Edit Registrar')

		response = self.client.post(f'/locations/{location.pk}/edit/', sample_payload(
			location_name='Records and Registrar Office',
			description='Handles enrolment, records, and transfers.',
			building_floor='Main Building, 2nd Floor',
			x_coordinate='55',
			y_coordinate='70',
		))

		self.assertRedirects(response, '/')
		location.refresh_from_db()
		self.assertEqual(location.location_name, 'Records and Registrar Office')
		self.assertEqual(location.building_floor, 'Main Building, 2nd Floor')
		self.assertEqual(location.x_coordinate, 55)
		self.assertEqual(location.y_coordinate, 70)
		self.assertEqual(CampusLocation.objects.count(), 1)

	def test_delete_location_removes_record(self):
		location = make_location(location_name='Old Canteen', category=CampusLocation.CATEGORY_CANTEEN)

		confirm = self.client.get(f'/locations/{location.pk}/delete/')
		self.assertContains(confirm, 'Old Canteen')
		self.assertTrue(CampusLocation.objects.filter(pk=location.pk).exists())

		response = self.client.post(f'/locations/{location.pk}/delete/')

		self.assertRedirects(response, '/')
		self.assertFalse(CampusLocation.objects.filter(pk=location.pk).exists())
		rendered = self.client.get('/')
		self.assertNotContains(rendered, 'Old Canteen')


class LocationApiTests(TestCase):
	def setUp(self):
		User.objects.create_user(username='registrar', password='campus-pass-123')

	def test_list_is_public(self):
		make_location(location_name='Canteen Annex', category=CampusLocation.CATEGORY_CANTEEN)

		response = self.client.get('/api/locations/')

		self.assertEqual(response.status_code, 200)
		results = response.json()['results']
		self.assertEqual(len(results), 1)
		self.assertEqual(results[0]['location_name'], 'Canteen Annex')

	def test_create_requires_sign_in(self):
		response = self.client.post(
			'/api/locations/',
			data=json.dumps(sample_payload()),
			content_type='application/json',
		)

		self.assertEqual(response.status_code, 401)
		self.assertEqual(CampusLocation.objects.count(), 0)

	def test_create_when_signed_in(self):
		self.client.login(username='registrar', password='campus-pass-123')

		response = self.client.post(
			'/api/locations/',
			data=json.dumps(sample_payload()),
			content_type='application/json',
		)

		self.assertEqual(response.status_code, 201)
		self.assertEqual(response.json()['location_name'], 'Library')
		self.assertTrue(CampusLocation.objects.filter(location_name='Library').exists())

	def test_update_and_delete_require_sign_in(self):
		location = make_location()

		update = self.client.put(
			f'/api/locations/{location.pk}/',
			data=json.dumps(sample_payload()),
			content_type='application/json',
		)
		self.assertEqual(update.status_code, 401)

		removed = self.client.delete(f'/api/locations/{location.pk}/')
		self.assertEqual(removed.status_code, 401)
		self.assertTrue(CampusLocation.objects.filter(pk=location.pk).exists())


class StudentAuthTests(TestCase):
	def test_index_offers_student_sign_in_and_sign_up(self):
		anonymous = self.client.get('/')

		self.assertContains(anonymous, 'Student sign in')
		self.assertContains(anonymous, 'Student sign up')
		self.assertContains(anonymous, 'Staff sign in')
		self.assertNotContains(anonymous, 'Sign out')

	def test_signup_page_renders(self):
		response = self.client.get('/students/signup/')

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Create your student account')
		self.assertContains(response, 'name="student_number"')
		self.assertContains(response, 'name="year_level"')

	def test_student_can_sign_up_then_sign_out(self):
		created = self.client.post('/students/signup/', student_payload())

		self.assertRedirects(created, '/')
		self.assertEqual(Student.objects.count(), 1)
		self.assertTrue(User.objects.filter(username='2026-00123').exists())

		signed_in = self.client.get('/')
		self.assertContains(signed_in, 'Sign out')
		self.assertContains(signed_in, '2026-00123')
		self.assertNotContains(signed_in, 'Add a location')

		logout = self.client.post('/students/signout/')
		self.assertRedirects(logout, '/')

		signed_out = self.client.get('/')
		self.assertContains(signed_out, 'Student sign in')
		self.assertNotContains(signed_out, 'Sign out')

	def test_signup_rejects_a_duplicate_student_number(self):
		self.client.post('/students/signup/', student_payload())
		self.client.post('/students/signout/')

		response = self.client.post('/students/signup/', student_payload(first_name='Juan'))

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'A student account already exists for this student number.')
		self.assertEqual(Student.objects.count(), 1)

	def test_signup_requires_matching_passwords(self):
		response = self.client.post(
			'/students/signup/',
			student_payload(password2='different-password-1'),
		)

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'The two passwords do not match.')
		self.assertEqual(Student.objects.count(), 0)

	def test_signin_page_renders_student_fields(self):
		response = self.client.get('/students/signin/')

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Student sign in')
		self.assertContains(response, 'name="username"')
		self.assertContains(response, 'Student number')

	def test_student_can_sign_in_and_out(self):
		self.client.post('/students/signup/', student_payload())
		self.client.post('/students/signout/')

		response = self.client.post('/students/signin/', {
			'username': '2026-00123',
			'password': 'campus-student-123',
			'next': '/',
		})

		self.assertRedirects(response, '/')
		self.assertEqual(int(self.client.session['_auth_user_id']), User.objects.get(username='2026-00123').pk)
		self.assertContains(self.client.get('/'), 'Sign out')

		logout = self.client.post('/students/signout/')
		self.assertRedirects(logout, '/')
		self.assertNotIn('_auth_user_id', self.client.session)

	def test_signin_rejects_a_bad_password(self):
		self.client.post('/students/signup/', student_payload())
		self.client.post('/students/signout/')

		response = self.client.post('/students/signin/', {
			'username': '2026-00123',
			'password': 'wrong-password',
		})

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Please enter a correct username and password')
		self.assertNotIn('_auth_user_id', self.client.session)

	def test_staff_account_cannot_use_the_student_sign_in(self):
		User.objects.create_user(username='registrar', password='campus-pass-123')

		response = self.client.post('/students/signin/', {
			'username': 'registrar',
			'password': 'campus-pass-123',
		})

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'No student account matches those details')
		self.assertNotIn('_auth_user_id', self.client.session)

	def test_student_account_cannot_use_the_staff_sign_in(self):
		self.client.post('/students/signup/', student_payload())
		self.client.post('/students/signout/')

		response = self.client.post('/accounts/login/', {
			'username': '2026-00123',
			'password': 'campus-student-123',
		})

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Use the student sign in page instead')
		self.assertNotIn('_auth_user_id', self.client.session)

	def test_student_can_view_the_map_but_not_manage_locations(self):
		self.client.post('/students/signup/', student_payload())

		self.assertEqual(self.client.get('/').status_code, 200)
		self.assertRedirects(self.client.get('/locations/add/'), '/')

		response = self.client.post(
			'/api/locations/',
			data=json.dumps(sample_payload()),
			content_type='application/json',
		)

		self.assertEqual(response.status_code, 403)
		self.assertEqual(CampusLocation.objects.count(), 0)

	def test_signin_respects_a_safe_next_target(self):
		self.client.post('/students/signup/', student_payload())
		self.client.post('/students/signout/')

		blocked = self.client.post('/students/signin/', {
			'username': '2026-00123',
			'password': 'campus-student-123',
			'next': 'https://evil.example.com/',
		})
		self.assertRedirects(blocked, '/')
