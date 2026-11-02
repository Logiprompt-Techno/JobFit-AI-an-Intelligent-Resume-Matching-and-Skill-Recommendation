"""
Root URL configuration for the config project.

Delegates all application URLs to matching_app.urls, and serves
media files (uploaded resumes) during development.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('matching_app.urls')),
]

# Serve user-uploaded media files (e.g. resumes) during development.
# In production this should be handled by the web server (e.g. Nginx),
# not by Django itself.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
