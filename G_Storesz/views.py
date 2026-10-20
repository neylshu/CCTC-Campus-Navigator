import json
from functools import wraps

from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST

from .forms import CampusLocationForm, StudentLoginForm, StudentSignUpForm
from .models import CampusLocation, student_for


def _safe_next(request):
    target = request.POST.get('next') or request.GET.get('next')
    if target and url_has_allowed_host_and_scheme(target, allowed_hosts={request.get_host()}):
        return target
    return None


def staff_required(view):
    """Allow only signed-in staff accounts; students are sent back to the map."""

    @wraps(view)
    @login_required
    def wrapper(request, *args, **kwargs):
        if student_for(request.user) is not None:
            return redirect('index')
        return view(request, *args, **kwargs)

    return wrapper


class StaffLoginView(LoginView):
    template_name = 'registration/login.html'

    def form_valid(self, form):
        if student_for(form.get_user()) is not None:
            form.add_error(None, 'This is a student account. Use the student sign in page instead.')
            return self.form_invalid(form)
        return super().form_valid(form)


def index(request):
    locations = list(CampusLocation.objects.all())
    categories = [
        {'value': value, 'label': label, 'color': CampusLocation.CATEGORY_COLORS.get(value, '#64748b')}
        for value, label in CampusLocation.CATEGORY_CHOICES
    ]
    top = max(locations, key=lambda location: location.view_count, default=None)
    stats = {
        'total': len(locations),
        'categories': len({location.category for location in locations}),
        'top_name': top.location_name if top else None,
        'top_views': top.view_count if top else 0,
    }
    student = student_for(request.user)
    context = {
        'locations': locations,
        'locations_json': json.dumps([location.to_dict() for location in locations]),
        'categories_json': json.dumps(categories),
        'stats': stats,
        'student': student,
        'is_student': student is not None,
        'can_edit': request.user.is_authenticated and student is None,
    }
    return render(request, 'G_Storesz/navigator.html', context)


@never_cache
def student_signup(request):
    if request.user.is_authenticated:
        return redirect('index')

    if request.method == 'POST':
        form = StudentSignUpForm(request.POST)
        if form.is_valid():
            student = form.save()
            auth_login(request, student.user)
            return redirect(_safe_next(request) or 'index')
    else:
        form = StudentSignUpForm()

    return render(request, 'registration/student_signup.html', {'form': form})


@never_cache
def student_login(request):
    if request.user.is_authenticated:
        return redirect('index')

    if request.method == 'POST':
        form = StudentLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            if student_for(user) is None:
                form.add_error(None, 'No student account matches those details. Staff should use the staff sign in page.')
            else:
                auth_login(request, user)
                return redirect(_safe_next(request) or 'index')
    else:
        form = StudentLoginForm()

    return render(request, 'registration/student_login.html', {'form': form})


@never_cache
@require_POST
def student_logout(request):
    auth_logout(request)
    return redirect('index')


@staff_required
def add_location(request):
    if request.method == 'POST':
        form = CampusLocationForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('index')
    else:
        form = CampusLocationForm()

    return render(request, 'G_Storesz/add_location.html', {'form': form})


@staff_required
def edit_location(request, pk):
    location = get_object_or_404(CampusLocation, pk=pk)

    if request.method == 'POST':
        form = CampusLocationForm(request.POST, request.FILES, instance=location)
        if form.is_valid():
            form.save()
            return redirect('index')
    else:
        form = CampusLocationForm(instance=location)

    return render(request, 'G_Storesz/edit_location.html', {'form': form, 'location': location})


@staff_required
def delete_location(request, pk):
    location = get_object_or_404(CampusLocation, pk=pk)

    if request.method == 'POST':
        location.delete()
        return redirect('index')

    return render(request, 'G_Storesz/delete_location.html', {'location': location})
