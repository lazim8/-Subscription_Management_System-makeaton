from django.urls import path
from django.http import HttpResponse

app_name = 'catalog'

def placeholder_catalog(request):
    return HttpResponse("Catalog - Coming in Step 2")

urlpatterns = [
    path('products/', placeholder_catalog, name='product-list'),
]
