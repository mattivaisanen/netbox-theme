from django.urls import path

from . import views

urlpatterns = [
    path('', views.ThemeView.as_view(), name='theme'),
    path('reset/', views.ThemeResetView.as_view(), name='theme_reset'),
    path('export/', views.ThemeExportView.as_view(), name='theme_export'),
    path('import/', views.ThemeImportView.as_view(), name='theme_import'),
    path('logo/<str:slot>/', views.LogoView.as_view(), name='logo'),
]
