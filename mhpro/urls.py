"""
URL configuration for mhpro project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path,  include
# Swagger imports
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework import permissions

from rest_framework_simplejwt.views import TokenRefreshView


schema_view = get_schema_view(
    openapi.Info(
        title="MHPro API",
        default_version='v1',
        description="MHPro Mental Health Platform API",
        terms_of_service="https://www.mhpro.com/terms/",
        contact=openapi.Contact(email="support@mhpro.com"),
        license=openapi.License(name="MIT License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)



urlpatterns = [
    path('admin/', admin.site.urls),
    
        # Swagger URLs
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    path('swagger.json/', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    path('api/v1/', include('referrals.urls')),
    path('api/v1/users/', include('accounts.urls')),
    path('api/v1/', include('appointments.urls')), #appointments/
    path('api/v1/', include('consultations.urls')),#consultations/
    path('api/v1/prescriptions/', include('prescriptions.urls')),
    path('api/v1/labs/', include('labs.urls')),
    path('api/v1/chat/', include('chat.urls')),
    # path('api/v1/queue/', include('queue.urls')),
    path('api/v1/payments/', include('payments.urls')),
    path('api/v1/notifications/', include('notifications.urls')),
    path('api/v1/analytics/', include('analytics.urls')),
    
    # WebSocket
    # path('ws/', include('chat.routing')),    
]

