from django.contrib import admin
from .models import OperationalPoint
from leaflet.admin import LeafletGeoAdmin
# Register your models here.

admin.site.register(OperationalPoint, LeafletGeoAdmin)

