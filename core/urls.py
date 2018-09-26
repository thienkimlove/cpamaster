from django.contrib.auth.decorators import login_required
from django.urls import path

from core.classes import *
from core.views import *

app_name = 'core'

urlpatterns = [
    path('login/', LogInView.as_view(), name='login'),
    path('logout/', log_out, name='logout'),
    path('offers/', list_offer, name='offer_list'),

    path('offers/create/', create_offer, name='offer_create'),
    path('offers/data_table/', login_required(OfferListJson.as_view()), name='offer_data_table'),
    path('offers/edit/<item_id>/', edit_offer, name='offer_edit'),
    path('offers/clear/<item_id>/', clear_offer, name='offer_clear'),
    path('offers/accept/<item_id>/', accept_offer, name='offer_accept'),
    path('offers/reject/<item_id>/', reject_offer, name='offer_reject'),
    path('offers/inactive/<item_id>/', inactive_offer, name='offer_inactive'),
    path('offers/delete/<item_id>/', delete_offer, name='offer_delete'),
    path('offers/export/', export_offer, name='offer_export'),
    path('offers/api/', OfferAPIJson.as_view(), name='offer_api'),

    path('camp/', camp, name='offer_camp'),
    path('check/', check, name='offer_check'),
    path('postback/', postback, name='offer_postback'),

    path('networks/', list_network, name='network_list'),
    path('networks/data_table/', login_required(NetworkListJson.as_view()), name='network_data_table'),
    path('networks/edit/<item_id>/', edit_network, name='network_edit'),
    path('networks/cron/<item_id>/', cron_network, name='network_cron'),
    path('networks/ajax_cron/<item_id>/<routing>/', ajax_cron, name='network_ajax_cron'),
    path('networks/api/', NetworkAPIJson.as_view(), name='network_api'),


    path('leads/', list_lead, name='lead_list'),
    path('leads/data_table/', login_required(LeadListJson.as_view()), name='lead_data_table'),
    path('leads/recent_lead/', recent_lead, name='recent_lead'),
    path('leads/notify_lead/', notify_lead, name='notify_lead'),
    path('leads/export/', export_lead, name='lead_export'),
    path('api/offers/', api_offer, name='api_offer'),
    path('api/users/', api_user, name='api_user'),

]
