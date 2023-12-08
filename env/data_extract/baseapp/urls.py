from django.urls import path
from . import views
from .views import *



urlpatterns = [
    path('', IndexView.as_view(), name='home'),
    path('city_selection/', SelectedCityView.as_view(), name='city_selection'),
    path('object_data/', ObjectView.as_view(), name='object_data'),
    path('object_data_radius/', ObjectDataRadiusView.as_view(), name='object_data_radius'),
    path('object_details/<int:url_index>/', ObjectDetailsView.as_view(), name='object_details'),
    path('object_radius_details/<str:selected_radius>/<str:zip_or_city>/<int:city_url_index>', ObjectRadiusDetailView.as_view(), name='object_radius_details'),
    path('object_city_details/<str:selected_city>/<int:city_url_index>/', ObjectCityDetailView.as_view(), name='object_city_details'),
    path('all_objects_details/', AllObjectsView.as_view(), name='all_objects_details'),
    path('detail_search/', DetailSearch.as_view(), name='detail_search'),

    path('amtsgerichte/', AmtsgerichteView.as_view(), name='amtsgerichte'),
    path('bdl_city/', StaedteView.as_view(), name='bdl_city'),
    path('objekt_daten_nach_stadt/', StaedteObjektlisteView.as_view(), name='objekt_daten_nach_stadt'),


    path('test/', TestView.as_view(), name='test'),
    path('test_liste/', TerminObjektlisteView.as_view(), name='test_liste'),
    path('test_objektdetails/<int:url_zvg_index>/', TestObjektdetails.as_view() , name='test_objektdetails')
]