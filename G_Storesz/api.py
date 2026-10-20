import json

from django.db.models import F, Q
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from .forms import CampusLocationForm
from .models import CampusLocation, student_for

MERGE_FIELDS = (
    'location_name', 'category', 'description', 'building_floor',
    'x_coordinate', 'y_coordinate', 'office_hours', 'contact_person',
)


def _errors(form):
    return {field: [str(error) for error in errors] for field, errors in form.errors.items()}


def _unauthenticated():
    return JsonResponse({'error': 'You must be signed in to manage locations.'}, status=401)


def _student_forbidden():
    return JsonResponse({'error': 'Student accounts can view the map but cannot manage locations.'}, status=403)


def _manage_denied(request):
    if not request.user.is_authenticated:
        return _unauthenticated()
    if student_for(request.user) is not None:
        return _student_forbidden()
    return None


def _body(request):
    """Return (data, files) from either a multipart form or a JSON body."""
    if request.content_type and request.content_type.startswith('multipart/form-data'):
        return request.POST, request.FILES
    try:
        payload = json.loads(request.body or b'{}')
    except json.JSONDecodeError:
        return None, None
    if not isinstance(payload, dict):
        return None, None
    return payload, request.FILES


@require_http_methods(['GET', 'POST'])
def location_list(request):
    if request.method == 'GET':
        locations = CampusLocation.objects.all()

        search = request.GET.get('search', '').strip()
        if search:
            locations = locations.filter(
                Q(location_name__icontains=search)
                | Q(category__icontains=search)
                | Q(description__icontains=search)
                | Q(building_floor__icontains=search)
            )

        category = request.GET.get('category', '').strip()
        if category:
            locations = locations.filter(category=category)

        sort = request.GET.get('sort', 'name')
        if sort == 'newest':
            locations = locations.order_by('-date_added', 'location_name')
        elif sort == 'popular':
            locations = locations.order_by('-view_count', 'location_name')
        else:
            locations = locations.order_by('location_name')

        return JsonResponse({'results': [location.to_dict() for location in locations]})

    denied = _manage_denied(request)
    if denied:
        return denied

    data, files = _body(request)
    if data is None:
        return JsonResponse({'error': 'Invalid request body.'}, status=400)

    form = CampusLocationForm(data, files)
    if not form.is_valid():
        return JsonResponse({'errors': _errors(form)}, status=400)

    location = form.save()
    return JsonResponse(location.to_dict(), status=201)


@require_http_methods(['GET', 'POST', 'PUT', 'PATCH', 'DELETE'])
def location_detail(request, pk):
    try:
        location = CampusLocation.objects.get(pk=pk)
    except CampusLocation.DoesNotExist:
        return JsonResponse({'error': 'Location not found.'}, status=404)

    if request.method == 'GET':
        return JsonResponse(location.to_dict())

    denied = _manage_denied(request)
    if denied:
        return denied

    if request.method == 'DELETE':
        location.delete()
        return JsonResponse({'ok': True, 'id': pk})

    data, files = _body(request)
    if data is None:
        return JsonResponse({'error': 'Invalid request body.'}, status=400)

    if request.method == 'PATCH':
        merged = {field: getattr(location, field) for field in MERGE_FIELDS}
        merged.update(data)
        data = merged
    form = CampusLocationForm(data, files, instance=location)
    if not form.is_valid():
        return JsonResponse({'errors': _errors(form)}, status=400)

    updated = form.save()
    return JsonResponse(updated.to_dict())


@require_http_methods(['POST'])
def location_view_ping(request, pk):
    updated = CampusLocation.objects.filter(pk=pk).update(view_count=F('view_count') + 1)
    if not updated:
        return JsonResponse({'error': 'Location not found.'}, status=404)
    count = CampusLocation.objects.get(pk=pk).view_count
    return JsonResponse({'id': pk, 'view_count': count})
