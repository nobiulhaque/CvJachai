from django.contrib.auth.models import User
from api.models import Profile
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import serializers

# --- Serializers ---

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ('email', 'password', 'first_name', 'last_name')

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate_password(self, value):
        from django.contrib.auth.password_validation import validate_password
        validate_password(value)
        return value

    def create(self, validated_data):
        # We use email as the username for Django's built-in User model
        # since the user requested email-based login.
        user = User.objects.create_user(
            username=validated_data['email'],
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', '')
        )
        # Create empty profile for the user
        Profile.objects.create(user=user)
        return user

class EmailTokenObtainSerializer(TokenObtainPairSerializer):
    """Custom JWT Serializer that treats the 'email' field as the 'username'."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'] = serializers.EmailField()
        # Remove username if it exists to clean up the UI
        if 'username' in self.fields:
            del self.fields['username']

    def validate(self, attrs):
        # Map 'email' to 'username' so SimpleJWT can authenticate normally
        attrs['username'] = attrs.get('email')
        data = super().validate(attrs)

        # Add custom user info and full profile to the response
        try:
            profile = self.user.profile
            data['user'] = {
                'email': self.user.email,
                'full_name': f"{self.user.first_name} {self.user.last_name}".strip(),
                'is_staff': self.user.is_staff,
                'location': profile.location,
                'profession': profile.profession,
                'skills': profile.skills,
                'company_name': profile.company_name,
                'bio': profile.bio
            }
        except Exception:
            data['user'] = {
                'email': self.user.email,
                'full_name': f"{self.user.first_name} {self.user.last_name}".strip(),
                'is_staff': self.user.is_staff
            }
        return data

class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()

class ResetPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp_code = serializers.CharField(max_length=6)
    new_password = serializers.CharField(write_only=True, min_length=8)

    def validate_new_password(self, value):
        from django.contrib.auth.password_validation import validate_password
        validate_password(value)
        return value

# --- Views ---

class RegisterView(generics.CreateAPIView):
    """Endpoint for user registration (Sign Up)."""
    queryset = User.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = RegisterSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response({
                "message": "User registered successfully",
                "user": {
                    "email": user.email,
                    "name": f"{user.first_name} {user.last_name}".strip()
                }
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LoginView(TokenObtainPairView):
    """Endpoint for user login (Sign In) using Email and Password."""
    serializer_class = EmailTokenObtainSerializer
    permission_classes = (AllowAny,)

class ForgotPasswordView(generics.GenericAPIView):
    """Endpoint to request a password reset OTP."""
    permission_classes = (AllowAny,)
    serializer_class = ForgotPasswordSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            user = User.objects.filter(email=email).first()
            
            if user:
                import random
                from django.core.mail import send_mail
                from django.conf import settings
                from api.models import PasswordResetOTP

                # Generate 6-digit OTP
                otp = str(random.randint(100000, 999999))
                
                # Save OTP to database
                PasswordResetOTP.objects.create(email=email, otp_code=otp)
                
                try:
                    import resend
                    resend.api_key = os.getenv("RESEND_API_KEY", "re_EKJus3Zv_9v1xeqKcjMivio94vJU25Dp2")
                    
                    resend.Emails.send({
                        "from": os.getenv("DEFAULT_FROM_EMAIL", "onboarding@resend.dev"),
                        "to": email,
                        "subject": "Your Password Reset OTP",
                        "html": f"""
                            <div style="font-family: sans-serif; padding: 20px; border: 1px solid #eee; border-radius: 10px;">
                                <h2 style="color: #333;">Password Reset Request</h2>
                                <p>Your OTP for password reset is:</p>
                                <div style="font-size: 24px; font-weight: bold; color: #007bff; padding: 10px; background: #f8f9fa; display: inline-block; border-radius: 5px;">
                                    {otp}
                                </div>
                                <p style="color: #666; margin-top: 20px;">This code will expire in 10 minutes.</p>
                                <hr style="border: 0; border-top: 1px solid #eee; margin: 20px 0;">
                                <p style="font-size: 12px; color: #999;">If you didn't request this, please ignore this email.</p>
                            </div>
                        """
                    })
                except Exception as e:
                    return Response({"error": f"Failed to send email via Resend: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
            # Always return success to prevent email enumeration
            return Response({"message": "If an account with this email exists, an OTP has been sent."}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ResetPasswordView(generics.GenericAPIView):
    """Endpoint to reset password using the OTP and Email."""
    permission_classes = (AllowAny,)
    serializer_class = ResetPasswordSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            from django.utils import timezone
            from datetime import timedelta
            from api.models import PasswordResetOTP

            email = serializer.validated_data['email']
            otp_code = serializer.validated_data['otp_code']
            new_password = serializer.validated_data['new_password']

            # Find the most recent unused OTP for this email
            expiry_time = timezone.now() - timedelta(minutes=10)
            otp_record = PasswordResetOTP.objects.filter(
                email=email, 
                otp_code=otp_code, 
                is_used=False,
                created_at__gte=expiry_time
            ).last()

            if otp_record:
                user = User.objects.filter(email=email).first()
                if user:
                    user.set_password(new_password)
                    user.save()
                    
                    # Mark OTP as used
                    otp_record.is_used = True
                    otp_record.save()
                    
                    return Response({"message": "Password has been reset successfully."}, status=status.HTTP_200_OK)
                else:
                    return Response({"error": "User with this email no longer exists."}, status=status.HTTP_404_NOT_FOUND)
            else:
                return Response({"error": "Invalid or expired OTP."}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
