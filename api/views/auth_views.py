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
