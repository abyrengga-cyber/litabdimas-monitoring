from django.urls import path
from . import views

urlpatterns = [
    # Auth
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # Dashboard
    path('', views.dashboard, name='dashboard'),

    # Activities
    path('activity/list/', views.activity_list, name='activity_list'),
    path('activity/new/', views.activity_create, name='activity_create'),
    path('activity/<int:pk>/', views.activity_detail, name='activity_detail'),
    path('activity/<int:pk>/edit/', views.activity_edit, name='activity_edit'),
    path('activity/<int:pk>/review/', views.activity_review, name='activity_review'),
    path('activity/<int:pk>/report/', views.activity_submit_report, name='activity_submit_report'),

    # Statistik & Profile
    path('statistik/', views.dosen_statistics, name='statistik'),
    path('statistik/dosen/<int:dosen_id>/', views.dosen_detail_statistics, name='dosen_detail_statistics'),
    path('profil/', views.profile_view, name='profile'),

    # Notifikasi
    path('notifikasi/', views.notification_list, name='notification_list'),
    path('notification/<int:pk>/read/', views.mark_notification_read, name='notification_read'),
    path('notification/read-all/', views.mark_all_notifications_read, name='notification_read_all'),

    # Fitur Admin Khusus
    path('activity/export/', views.export_activities_csv, name='export_activities_csv'),
    path('users/', views.user_list, name='user_list'),
    path('users/new/', views.user_create, name='user_create'),
    path('users/<int:pk>/edit/', views.user_edit, name='user_edit'),
]
