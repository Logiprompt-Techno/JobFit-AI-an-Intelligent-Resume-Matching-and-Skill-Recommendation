"""
Django admin registration for matching_app models.

Models registered:
    - UserProfile
    - Company
    - Resume
    - Job
    - MatchResult
    - JobApplication
    - Message
    - InterviewSession
    - InterviewQA
"""

from django.contrib import admin
from .models import UserProfile, Company, Resume, Job, MatchResult, JobApplication, Message, InterviewSession, InterviewQA


@admin.action(description="Approve selected recruiter accounts")
def approve_recruiters(modeladmin, request, queryset):
    """Admin action to bulk approve selected pending recruiter accounts."""
    updated = queryset.update(is_approved=True)
    modeladmin.message_user(request, f"Successfully approved {updated} recruiter account(s).")


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """Admin configuration for UserProfile model."""
    list_display = ("id", "user", "role", "company_name", "phone", "is_approved", "created_at")
    search_fields = ("user__username", "user__email", "phone", "company_name")
    list_filter = ("role", "is_approved", "created_at")
    actions = [approve_recruiters]


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    """Admin configuration for the Company model."""
    list_display = ("id", "name", "email", "location", "website", "created_at")
    search_fields = ("name", "location", "email")
    list_filter = ("created_at",)
    ordering = ("name",)


@admin.register(Resume)
class ResumeAdmin(admin.ModelAdmin):
    """Admin configuration for the Resume model."""
    list_display = ("id", "user", "candidate_name", "email", "phone", "uploaded_at")
    search_fields = ("candidate_name", "email", "phone", "extracted_skills")
    list_filter = ("uploaded_at",)
    readonly_fields = ("uploaded_at",)
    ordering = ("-uploaded_at",)


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    """Admin configuration for the Job model."""
    list_display = ("id", "job_title", "posted_by", "company", "category", "job_type", "location", "created_at")
    search_fields = ("job_title", "company__name", "company_name_legacy", "required_skills", "location")
    list_filter = ("category", "job_type", "created_at")
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)


@admin.register(MatchResult)
class MatchResultAdmin(admin.ModelAdmin):
    """Admin configuration for the MatchResult model."""
    list_display = ("id", "resume", "job", "match_percentage", "created_at")
    search_fields = ("resume__candidate_name", "job__job_title", "job__company__name")
    list_filter = ("created_at", "match_percentage")
    readonly_fields = ("created_at",)
    ordering = ("-match_percentage",)


@admin.register(JobApplication)
class JobApplicationAdmin(admin.ModelAdmin):
    """Admin configuration for JobApplication model."""
    list_display = ("id", "resume", "job", "status", "applied_at")
    search_fields = ("resume__candidate_name", "job__job_title", "status")
    list_filter = ("status", "applied_at")
    ordering = ("-applied_at",)


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    """Admin configuration for Message model."""
    list_display = ("id", "sender", "recipient", "subject", "is_read", "created_at")
    search_fields = ("sender__username", "recipient__username", "subject", "body")
    list_filter = ("is_read", "created_at")
    ordering = ("-created_at",)


class InterviewQAInline(admin.TabularInline):
    model = InterviewQA
    extra = 0
    readonly_fields = ('question_number', 'question_text', 'candidate_answer', 'score', 'ai_feedback')


@admin.register(InterviewSession)
class InterviewSessionAdmin(admin.ModelAdmin):
    """Admin configuration for InterviewSession model."""
    list_display = ("id", "candidate", "job", "status", "tab_switch_count", "ai_evaluation_score", "created_at")
    search_fields = ("candidate__username", "job__job_title", "status")
    list_filter = ("status", "tab_switch_count", "created_at")
    inlines = [InterviewQAInline]


@admin.register(InterviewQA)
class InterviewQAAdmin(admin.ModelAdmin):
    """Admin configuration for InterviewQA model."""
    list_display = ("id", "session", "question_number", "score")
    search_fields = ("question_text", "candidate_answer")
