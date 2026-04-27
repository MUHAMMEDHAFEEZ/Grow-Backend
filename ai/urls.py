from django.urls import path
from ai.views import chat

urlpatterns = [
    path('chat/', chat, name='chat'),
]