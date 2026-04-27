from django.urls import path
from xp import views


urlpatterns = [
    path("add/", views.XPAddView.as_view(), name="xp-add"),
    path("total/", views.XPTotalView.as_view(), name="xp-total"),
    path("history/", views.XPHistoryView.as_view(), name="xp-history"),
]
