from django.db import models
from django.contrib.auth.models import User
import uuid
import secrets
import string

def generate_short_id():
    """Generates a compact 10-character unique ID."""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(10))

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    location = models.CharField(max_length=255, blank=True, null=True)
    profession = models.CharField(max_length=255, blank=True, null=True)
    skills = models.TextField(blank=True, null=True) # Stored as comma-separated or text
    company_name = models.CharField(max_length=255, blank=True, null=True)
    bio = models.TextField(blank=True, null=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    website = models.URLField(blank=True, null=True)

    def __str__(self):
        return f"Profile of {self.user.email}"

class Job(models.Model):
    id = models.CharField(primary_key=True, default=generate_short_id, max_length=12, editable=False)
    title = models.CharField(max_length=255)
    description = models.TextField()
    skills_required = models.TextField(help_text="Comma separated skills")
    min_experience = models.IntegerField(default=0)
    company_name = models.CharField(max_length=255)
    location = models.CharField(max_length=255)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='jobs_created')
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.title} at {self.company_name}"

class Application(models.Model):
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='applications')
    candidate_name = models.CharField(max_length=255)
    candidate_email = models.EmailField()
    resume_file = models.FileField(upload_to='resumes/applications/')
    applied_at = models.DateTimeField(auto_now_add=True)
    
    # Storage for analysis results (cached)
    match_score = models.FloatField(null=True, blank=True)
    analysis_data = models.JSONField(null=True, blank=True) # Strengths, verdict, etc.

    def __str__(self):
        return f"Application by {self.candidate_name} for {self.job.title}"

class PasswordResetOTP(models.Model):
    email = models.EmailField()
    otp_code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    def __str__(self):
        return f"OTP for {self.email} - {self.otp_code}"
