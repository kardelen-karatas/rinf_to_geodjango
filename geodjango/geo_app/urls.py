from django.urls import path
from .views import HomeView, model_form_upload
from .models import OperationalPoint
from djgeojson.views import GeoJSONLayerView
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path('', model_form_upload, name='home'),
    path('data/', GeoJSONLayerView.as_view(model=OperationalPoint, properties=('opp_name','oty_id','mem_id','opp_uniqueid')), name='data'),
    #path('uploads/form/', model_form_upload, name='model_form_upload'),
]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
