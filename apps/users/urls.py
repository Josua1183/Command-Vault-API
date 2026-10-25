from django.urls import path

from .views import (
    UserCreateView,
    UserVerifyView,
    UserLoginView,
    UserRefreshView,
    UserLogoutView,
    UserMeView,
    UserResendCodeView,
)

urlpatterns = [
    path('register/', UserCreateView.as_view(), name='user-register'),
    path('verify/', UserVerifyView.as_view(), name='user-verify'),
    path('login/', UserLoginView.as_view(), name='user-login'),
    path('refresh/', UserRefreshView.as_view(), name='user-refresh'),
    path('logout/', UserLogoutView.as_view(), name='user-logout'),
    path('me/', UserMeView.as_view(), name='user-me'),
    path('resend-code/', UserResendCodeView.as_view(), name='user-resend-code'),
]
