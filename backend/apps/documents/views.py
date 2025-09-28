from django.http import HttpResponse


def index(request):
    """Страница со списком документов."""
    return HttpResponse("Documents index page")
