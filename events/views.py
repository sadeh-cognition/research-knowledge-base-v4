from django.shortcuts import render


def viz_view(request):
    return render(request, "events/viz.html")
