"""
Serializers for Resume Classifier API.
"""

from rest_framework import serializers


class ResumeUploadSerializer(serializers.Serializer):
    """Serializer for resume file uploads."""
    job_circular = serializers.CharField(
        help_text="Job description text"
    )
    resume_files = serializers.ListField(
        child=serializers.FileField(),
        help_text="Resume files (PDF, DOCX, TXT, or ZIP containing multiple resumes)"
    )
    top_k = serializers.IntegerField(
        default=5,
        min_value=1,
        help_text="Number of top candidates to return"
    )
    skills = serializers.CharField(
        required=False,
        default="",
        help_text="Comma-separated list of required skills"
    )
    min_experience = serializers.IntegerField(
        required=False,
        default=0,
        min_value=0,
        help_text="Minimum years of experience"
    )

    def validate_resume_files(self, value):
        if not value:
            raise serializers.ValidationError("At least one resume file is required.")
        return value
