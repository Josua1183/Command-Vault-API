from django.contrib.auth import authenticate
from django.db import IntegrityError, transaction
from rest_framework import status
from rest_framework.generics import CreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

from .models import User
from .serializers import UserSerializer, LoginSerializer, UserProfileSerializer, ResendCodeSerializer
from .services import send_password_reset_for_user, send_user_verification_code, resend_verification_code


class UserCreateView(CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [AllowAny]

    GENERIC_SUCCESS_RESPONSE = {
        "detail": "Wenn die E-Mail-Adresse gültig ist, wurde eine E-Mail mit weiteren Anweisungen versendet."
    }

    def _handle_existing_user(self, user):
        """Hilfsmethode, um Duplikate zu vermeiden."""
        if user.is_verified:
            send_password_reset_for_user(user=user)
            return Response(self.GENERIC_SUCCESS_RESPONSE, status=status.HTTP_200_OK)
        else:
            send_user_verification_code(user=user)
            return Response(self.GENERIC_SUCCESS_RESPONSE, status=status.HTTP_200_OK)

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        # 1. Daten validieren (durch den Serializer)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data.get('email', '').strip()

        existing_user = User.objects.filter(email__iexact=email).first()
        if existing_user:
            return self._handle_existing_user(existing_user)

        try:
            user = self.perform_create(serializer)
        except IntegrityError:
            existing_user = User.objects.filter(email__iexact=email).first()
            if existing_user:
                return self._handle_existing_user(existing_user)
            raise

        send_user_verification_code(user=user)
        return Response(self.GENERIC_SUCCESS_RESPONSE, status=status.HTTP_201_CREATED)


class UserVerifyView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        code = request.data.get('code')
        email = request.data.get('email')
        user = User.objects.filter(verification_code__code=code, email__iexact=email).first()
        if not user:
            return Response(
                {"detail": "Ungültiger Verifizierungscode."},
                status=status.HTTP_400_BAD_REQUEST
            )

        verification_code = user.verification_code
        if not verification_code.is_valid():
            # Erhöhe Versuche, um auch abgelaufene Codes zu tracken
            verification_code.attempts += 1
            verification_code.save(update_fields=['attempts'])

            # Unterscheide zwischen Ablauf und zu vielen Versuchen
            from django.utils import timezone
            from datetime import timedelta
            is_expired = timezone.now() > verification_code.created_at + timedelta(minutes=15)
            if is_expired and verification_code.attempts >= 5:
                return Response(
                    {"detail": "Verifizierungscode ist abgelaufen und es wurden zu viele Versuche unternommen. Bitte fordere einen neuen Code an."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            elif is_expired:
                return Response(
                    {"detail": "Verifizierungscode ist abgelaufen. Bitte fordere einen neuen Code an."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            else:
                return Response(
                    {"detail": "Zu viele fehlgeschlagene Versuche. Bitte fordere einen neuen Code an."},
                    status=status.HTTP_400_BAD_REQUEST
                )

        user.is_verified = True
        user.save()
        user.verification_code.delete()
        return Response({"detail": "E-Mail-Adresse erfolgreich verifiziert."}, status=status.HTTP_200_OK)


class UserLoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = authenticate(
            request,
            email=serializer.validated_data['email'],
            password=serializer.validated_data['password']
        )
        if not user:
            return Response(
                {"detail": "Ungültige E-Mail-Adresse oder Passwort."},
                status=status.HTTP_401_UNAUTHORIZED
            )

        if not user.is_verified:
            return Response(
                {"detail": "E-Mail-Adresse ist noch nicht verifiziert."},
                status=status.HTTP_403_FORBIDDEN
            )

        # Tokens dynamisch mit SimpleJWT erzeugen
        refresh = RefreshToken.for_user(user)
        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        })


class UserRefreshView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        refresh_token = request.data.get('refresh')
        if not refresh_token:
            return Response(
                {"detail": "Refresh-Token fehlt."},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            refresh = RefreshToken(refresh_token)
            return Response({
                'access': str(refresh.access_token),
            })
        except TokenError:
            return Response(
                {"detail": "Ungültiger oder abgelaufener Refresh-Token."},
                status=status.HTTP_400_BAD_REQUEST
            )


class UserLogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()  # Setzt den Token auf die Blacklist (erfordert 'rest_framework_simplejwt.token_blacklist' in INSTALLED_APPS)
            return Response({"detail": "Logout erfolgreich."}, status=status.HTTP_200_OK)
        except Exception:
            return Response(
                {"detail": "Ungültiger Token oder bereits ausgeloggt."},
                status=status.HTTP_400_BAD_REQUEST
            )


class UserMeView(RetrieveUpdateDestroyAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save(update_fields=['is_active'])


class UserResendCodeView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ResendCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        resend_verification_code(**serializer.validated_data)

        return Response({
            "detail": "Falls ein unbestätigtes Konto mit dieser E-Mail existiert, haben wir einen neuen Code gesendet."
        })
