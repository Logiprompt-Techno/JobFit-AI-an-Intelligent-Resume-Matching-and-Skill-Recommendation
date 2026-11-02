"""
Views for the matching_app application.

Features:
    - Home page & Navigation
    - Authentication (Login, Logout, Job Seeker Signup, Recruiter Signup with Admin Approval, Forgot Password, Change Password)
    - User Profile & Contact Info Editing
    - Role-Based Dashboards & Master Admin Recruiter Approval
    - Resume Quality Score calculation (0-100) & Improvement Tips
    - Resume Upload & NLP Information Extraction
    - Job Posting Management & Search/Filter Bar
    - Job Application Workflow ('Apply for Job' CTA & ATS Status Updates)
    - Hybrid AI Resume-Job Matching (60% Skill Overlap + 40% Sentence-BERT Semantic Similarity)
    - Skill Gap Certification Recommendations
    - Printable PDF Report Download
    - User & Recruiter Internal Messaging System (Inbox, Threads, Send Message)
    - AI Screening Interview Chatbot & Tab-Switch Proctoring
    - Interview Re-Attempt Request & Recruiter Approval Workflow (request_interview_reattempt, decide_interview_reattempt)
"""

from datetime import timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Q

from .models import (
    Resume, Job, MatchResult, Company, UserProfile, JobApplication, Message,
    InterviewSession, InterviewQA, UserReport
)
from .forms import (
    ResumeUploadForm, JobForm, CompanyForm, AdminLoginForm,
    JobSeekerSignUpForm, RecruiterSignUpForm, JobApplicationStatusForm,
    UserProfileEditForm, CustomPasswordChangeForm, ForgotPasswordForm, SendMessageForm,
    InterviewScheduleForm, COUNTRY_CODE_CHOICES
)
from .utils.text_cleaning import skills_string_to_list
from .utils.file_utils import human_readable_file_size

from .services.resume_parser import extract_text_from_resume
from .services.info_extractor import extract_candidate_info
from .services.skill_extractor import extract_skills
from .services.matcher import calculate_match
from .services.skill_recommender import recommend_skills_for_gap
from .services.resume_scorer import calculate_resume_score
from .services.interview_ai import generate_interview_questions, evaluate_interview_answers


def _is_recruiter_or_admin(user) -> bool:
    """Helper check if user is an approved recruiter or admin staff."""
    if not user.is_authenticated:
        return False
    if user.is_staff or user.is_superuser:
        return True
    return hasattr(user, 'profile') and user.profile.role == 'RECRUITER' and user.profile.is_approved


# ---------------------------------------------------------------------------
# HOME PAGE
# ---------------------------------------------------------------------------
def home(request):
    """Render home landing page for visitors and logged-in users."""
    context = {
        'project_title': 'JobFit AI - Intelligent Resume-Based Job Matching & Skill Recommendation Platform',
        'total_jobs': Job.objects.count(),
        'total_companies': Company.objects.count(),
        'total_resumes': Resume.objects.count(),
        'recent_jobs': Job.objects.select_related('company').all()[:6],
    }
    return render(request, 'matching_app/home.html', context)



# ---------------------------------------------------------------------------
# AUTHENTICATION & SIGNUP VIEWS
# ---------------------------------------------------------------------------
def jobseeker_signup(request):
    """Handle Job Seeker account registration."""
    if request.user.is_authenticated:
        return redirect('matching_app:jobseeker_dashboard')

    if request.method == 'POST':
        form = JobSeekerSignUpForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.save()

            country_code = form.cleaned_data.get('country_code', '+91')
            raw_phone = form.cleaned_data.get('phone', '').strip()
            full_phone = f"{country_code} {raw_phone}".strip() if raw_phone else ""

            UserProfile.objects.create(
                user=user,
                role='JOB_SEEKER',
                phone=full_phone,
                is_approved=True
            )

            login(request, user)
            messages.success(request, f"Welcome to JobFit AI, {user.username}! Your Job Seeker account was created.")
            return redirect('matching_app:jobseeker_dashboard')
        else:
            messages.error(request, "Registration failed. Please correct the errors below.")
    else:
        form = JobSeekerSignUpForm()

    return render(request, 'matching_app/jobseeker_signup.html', {'form': form})


def recruiter_signup(request):
    """Handle Recruiter / Employer registration with Admin Approval Workflow."""
    if request.user.is_authenticated:
        return redirect('matching_app:recruiter_dashboard')

    if request.method == 'POST':
        form = RecruiterSignUpForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.save()

            comp_name = form.cleaned_data.get('company_name', '').strip()
            country_code = form.cleaned_data.get('country_code', '+91')
            raw_phone = form.cleaned_data.get('phone', '').strip()
            full_phone = f"{country_code} {raw_phone}".strip() if raw_phone else ""

            UserProfile.objects.create(
                user=user,
                role='RECRUITER',
                phone=full_phone,
                company_name=comp_name,
                is_approved=False
            )

            if comp_name:
                Company.objects.get_or_create(name=comp_name)

            messages.warning(
                request,
                f"Your Recruiter registration for '{comp_name or user.username}' has been submitted! "
                "Your account is currently PENDING ADMIN APPROVAL. You will be able to log in once the administrator verifies your company registration."
            )
            return redirect('matching_app:login')
        else:
            messages.error(request, "Registration failed. Please correct the errors below.")
    else:
        form = RecruiterSignUpForm()

    return render(request, 'matching_app/recruiter_signup.html', {'form': form})


def user_login(request):
    """Unified user & recruiter login view with Admin Approval protection."""
    if request.user.is_authenticated:
        if hasattr(request.user, 'profile'):
            if request.user.profile.role == 'RECRUITER':
                return redirect('matching_app:recruiter_dashboard')
            return redirect('matching_app:jobseeker_dashboard')
        return redirect('matching_app:dashboard')

    if request.method == 'POST':
        username_input = request.POST.get('username', '').strip()
        if username_input:
            inactive_user = User.objects.filter(username__iexact=username_input, is_active=False).first()
            if inactive_user:
                reason = getattr(inactive_user.profile, 'deactivation_reason', '') if hasattr(inactive_user, 'profile') else ''
                reason_msg = reason if reason else "Your account or company registration was removed/deactivated by Administrator due to policy violation or safety report."
                messages.error(request, f"❌ Account Removed / Disabled: {reason_msg}")
                return redirect('matching_app:login')

        form = AdminLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()

            if hasattr(user, 'profile') and user.profile.role == 'RECRUITER' and not user.profile.is_approved and not user.is_staff and not user.is_superuser:
                messages.warning(
                    request,
                    "Your Recruiter account is currently PENDING ADMIN APPROVAL. "
                    "Please wait for an administrator to verify your company registration before signing in."
                )
                return redirect('matching_app:login')

            login(request, user)
            messages.success(request, f"Welcome back, {user.username}!")
            
            next_url = request.GET.get('next')
            if next_url:
                return redirect(next_url)

            if hasattr(user, 'profile'):
                if user.profile.role == 'RECRUITER':
                    return redirect('matching_app:recruiter_dashboard')
                return redirect('matching_app:jobseeker_dashboard')
            return redirect('matching_app:dashboard')
        else:
            messages.error(request, "Invalid username or password. Please try again.")
    else:
        form = AdminLoginForm()

    return render(request, 'matching_app/login.html', {'form': form})


def user_logout(request):
    """Logout view."""
    logout(request)
    messages.info(request, "You have been logged out successfully.")
    return redirect('matching_app:home')


def forgot_password(request):
    """View to reset password securely with username + registered email verification and superuser protection."""
    if request.method == 'POST':
        form = ForgotPasswordForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username'].strip()
            email = form.cleaned_data['email'].strip()
            new_password = form.cleaned_data['new_password']

            user = User.objects.filter(username__iexact=username).first()
            if not user:
                messages.error(request, f"No user account found with username '{username}'.")
            elif user.is_superuser or user.is_staff:
                messages.error(request, "⚠️ Master Admin and Staff accounts cannot be reset via the public web form for security reasons.")
            elif not user.email or user.email.lower() != email.lower():
                messages.error(request, f"Security verification failed: The email address provided does not match the registered email for account '{user.username}'.")
            else:
                user.set_password(new_password)
                user.save()
                messages.success(request, f"Password for user '{user.username}' updated successfully! You can now log in.")
                return redirect('matching_app:login')
        else:
            messages.error(request, "Please fix the errors below.")
    else:
        form = ForgotPasswordForm()

    return render(request, 'matching_app/forgot_password.html', {'form': form})


# ---------------------------------------------------------------------------
# USER PROFILE & PASSWORD CHANGE VIEWS
# ---------------------------------------------------------------------------
@login_required(login_url='matching_app:login')
def user_profile(request):
    """View and update User Profile details, username, and profile picture."""
    profile, created = UserProfile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        form = UserProfileEditForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            new_username = form.cleaned_data['username']
            request.user.username = new_username
            request.user.email = form.cleaned_data['email']
            request.user.save()

            country_code = form.cleaned_data.get('country_code', '+91')
            raw_phone = form.cleaned_data.get('phone', '').strip()
            profile.phone = f"{country_code} {raw_phone}".strip() if raw_phone else ""
            if profile.role == 'RECRUITER':
                profile.company_name = form.cleaned_data.get('company_name', '')
            
            if form.cleaned_data.get('profile_picture'):
                profile.profile_picture = form.cleaned_data['profile_picture']

            profile.save()

            messages.success(request, "Your profile details and username have been updated successfully!")
            return redirect('matching_app:user_profile')
        else:
            messages.error(request, "Failed to update profile. Please check inputs.")
    else:
        raw_phone = profile.phone
        country_code = '+91'
        if profile.phone:
            parts = profile.phone.split(' ', 1)
            if len(parts) == 2 and parts[0] in [c[0] for c in COUNTRY_CODE_CHOICES]:
                country_code = parts[0]
                raw_phone = parts[1]

        form = UserProfileEditForm(user=request.user, initial={
            'username': request.user.username,
            'email': request.user.email,
            'country_code': country_code,
            'phone': raw_phone,
            'company_name': profile.company_name,
        })

    user_resume = Resume.objects.filter(user=request.user).first()
    posted_jobs_count = Job.objects.filter(posted_by=request.user).count()

    context = {
        'profile': profile,
        'form': form,
        'user_resume': user_resume,
        'posted_jobs_count': posted_jobs_count,
    }
    return render(request, 'matching_app/profile.html', context)


@login_required(login_url='matching_app:login')
@require_POST
def delete_account(request):
    """Permanently delete user account and all associated profile, application, and resume data."""
    user = request.user
    username = user.username
    logout(request)
    user.delete()
    messages.success(request, f"Your account '{username}' and all associated profile data have been permanently deleted.")
    return redirect('matching_app:home')


@login_required(login_url='matching_app:login')
def change_password(request):
    """Allow logged-in users to change their password securely."""
    if request.method == 'POST':
        form = CustomPasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            form.save()
            update_session_auth_hash(request, form.user)
            messages.success(request, "Your password was changed successfully!")
            return redirect('matching_app:user_profile')
        else:
            messages.error(request, "Please fix the password errors below.")
    else:
        form = CustomPasswordChangeForm(user=request.user)

    return render(request, 'matching_app/password_change.html', {'form': form})


# ---------------------------------------------------------------------------
# ROLE-BASED DASHBOARDS & ADMIN RECRUITER APPROVAL
# ---------------------------------------------------------------------------
@login_required(login_url='matching_app:login')
def dashboard(request):
    """General Master Admin Overview Dashboard with Recruiter Approval panel."""
    if hasattr(request.user, 'profile'):
        if request.user.profile.role == 'RECRUITER' and not (request.user.is_staff or request.user.is_superuser):
            return redirect('matching_app:recruiter_dashboard')
        elif request.user.profile.role == 'JOB_SEEKER' and not (request.user.is_staff or request.user.is_superuser):
            return redirect('matching_app:jobseeker_dashboard')

    pending_recruiters = UserProfile.objects.filter(role='RECRUITER', is_approved=False).select_related('user')
    pending_reports = UserReport.objects.filter(status='Pending').select_related('reporter', 'reported_user', 'related_job')
    master_messages = Message.objects.select_related('sender', 'recipient', 'related_job').order_by('-created_at')[:25]

    context = {
        'total_jobs': Job.objects.count(),
        'total_companies': Company.objects.count(),
        'total_resumes': Resume.objects.count(),
        'total_matches': MatchResult.objects.count(),
        'recent_resumes': Resume.objects.all()[:5],
        'recent_jobs': Job.objects.select_related('company').all()[:5],
        'recent_matches': MatchResult.objects.select_related('resume', 'job').order_by('-created_at')[:5],
        'pending_recruiters': pending_recruiters,
        'pending_reports': pending_reports,
        'master_messages': master_messages,
    }
    return render(request, 'matching_app/dashboard.html', context)


@login_required(login_url='matching_app:login')
@require_POST
def submit_user_report(request, user_id):
    """Allow candidate or recruiter to report a suspicious user account or message."""
    reported_user = get_object_or_404(User, pk=user_id)
    reason = request.POST.get('reason', 'OTHER')
    description = request.POST.get('description', '').strip()
    job_id = request.POST.get('job_id')
    related_job = Job.objects.filter(pk=job_id).first() if job_id else None

    if reported_user == request.user:
        messages.error(request, "You cannot report your own account.")
        return redirect('matching_app:inbox')

    UserReport.objects.create(
        reporter=request.user,
        reported_user=reported_user,
        related_job=related_job,
        reason=reason,
        description=description or "Reported via Messaging System."
    )

    messages.success(request, f"Thank you. Your safety report regarding '{reported_user.username}' has been submitted to Administrator for review.")
    return redirect('matching_app:conversation_detail', user_id=user_id)


@login_required(login_url='matching_app:login')
@require_POST
def resolve_user_report(request, report_id):
    """Allow Master Admin to resolve, dismiss, or ban user based on safety report."""
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, "Only Master Administrators can resolve safety reports.")
        return redirect('matching_app:home')

    report = get_object_or_404(UserReport, pk=report_id)
    action = request.POST.get('action', '').strip().lower()

    if action == 'ban':
        reported_user = report.reported_user
        username = reported_user.username
        reported_user.is_active = False
        reported_user.save()

        if hasattr(reported_user, 'profile'):
            reported_user.profile.deactivation_reason = f"Your account was suspended/banned by Administrator following a safety report investigation ({report.get_reason_display()})."
            reported_user.profile.save()

        report.status = 'Resolved'
        report.save()
        messages.success(request, f"User account '{username}' has been BANNED and deactivated.")
    elif action == 'resolve':
        report.status = 'Resolved'
        report.save()
        messages.success(request, f"Safety report #{report.id} marked as RESOLVED.")
    elif action == 'dismiss':
        report.status = 'Dismissed'
        report.save()
        messages.info(request, f"Safety report #{report.id} DISMISSED.")

    return redirect('matching_app:dashboard')


@login_required(login_url='matching_app:login')
def approve_recruiter(request, pk):
    """Allow Master Admin to approve a pending recruiter registration."""
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, "Only Master Administrators can approve recruiter registrations.")
        return redirect('matching_app:home')

    profile = get_object_or_404(UserProfile, pk=pk, role='RECRUITER')
    profile.is_approved = True
    profile.save()
    messages.success(request, f"Recruiter account '{profile.user.username}' for '{profile.company_name or 'Company'}' was APPROVED successfully!")
    return redirect('matching_app:dashboard')


@login_required(login_url='matching_app:login')
def decline_recruiter(request, pk):
    """Allow Master Admin to decline/reject a pending recruiter registration."""
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, "Only Master Administrators can manage recruiter registrations.")
        return redirect('matching_app:home')

    profile = get_object_or_404(UserProfile, pk=pk, role='RECRUITER')
    username = profile.user.username
    profile.user.delete()
    messages.success(request, f"Recruiter registration request for '{username}' was DECLINED and removed.")
    return redirect('matching_app:dashboard')


@login_required(login_url='matching_app:login')
def jobseeker_dashboard(request):
    """Candidate / Job Seeker personal dashboard with interview sessions list."""
    user_resume = Resume.objects.filter(user=request.user).first()
    if not user_resume:
        user_resume = Resume.objects.filter(email=request.user.email).first()

    resume_score_data = None
    match_history = []
    recommended_jobs = []

    if user_resume:
        resume_score_data = calculate_resume_score(user_resume)
        match_history = MatchResult.objects.filter(resume=user_resume).select_related('job', 'job__company').order_by('-match_percentage')[:5]
        
        matched_job_ids = match_history.values_list('job_id', flat=True)
        recommended_jobs = Job.objects.exclude(id__in=matched_job_ids).select_related('company')[:4]
    else:
        recommended_jobs = Job.objects.select_related('company').all()[:4]

    interview_sessions = InterviewSession.objects.filter(candidate=request.user).select_related('job')

    context = {
        'user_resume': user_resume,
        'resume_score_data': resume_score_data,
        'match_history': match_history,
        'recommended_jobs': recommended_jobs,
        'applications': JobApplication.objects.filter(resume=user_resume) if user_resume else [],
        'interview_sessions': interview_sessions,
    }
    return render(request, 'matching_app/jobseeker_dashboard.html', context)


@login_required(login_url='matching_app:login')
def recruiter_dashboard(request):
    """Employer / Recruiter dashboard displaying only their own posted jobs and applicants."""
    if not _is_recruiter_or_admin(request.user):
        messages.error(request, "Access restricted to approved recruiters and administrators.")
        return redirect('matching_app:jobseeker_dashboard')

    if request.user.is_superuser and not Job.objects.filter(posted_by=request.user).exists():
        posted_jobs = Job.objects.select_related('company').all()
    else:
        posted_jobs = Job.objects.filter(posted_by=request.user).select_related('company')

    applications = JobApplication.objects.filter(job__in=posted_jobs).select_related('resume', 'resume__user', 'job').order_by('-applied_at')[:15]
    top_matches = MatchResult.objects.filter(job__in=posted_jobs).select_related('resume', 'resume__user', 'job').order_by('-match_percentage')[:10]

    # Map interview sessions for applicants
    app_ids = [app.pk for app in applications]
    interview_sessions_map = {
        session.application_id: session
        for session in InterviewSession.objects.filter(application_id__in=app_ids)
    }

    context = {
        'posted_jobs': posted_jobs,
        'applications': applications,
        'top_matches': top_matches,
        'total_posted_jobs': posted_jobs.count(),
        'total_applicants': applications.count(),
        'interview_sessions_map': interview_sessions_map,
    }
    return render(request, 'matching_app/recruiter_dashboard.html', context)


# ---------------------------------------------------------------------------
# COMPANY MANAGEMENT
# ---------------------------------------------------------------------------
def company_list(request):
    """List all featured companies."""
    companies = Company.objects.all()
    context = {
        'companies': companies,
        'is_recruiter': _is_recruiter_or_admin(request.user),
    }
    return render(request, 'matching_app/company_list.html', context)



@login_required(login_url='matching_app:login')
def company_create(request):
    """Create new company profile."""
    if not _is_recruiter_or_admin(request.user):
        messages.error(request, "Only recruiters or administrators can create company profiles.")
        return redirect('matching_app:company_list')

    if request.method == 'POST':
        form = CompanyForm(request.POST, request.FILES)
        if form.is_valid():
            company = form.save()
            messages.success(request, f"Company '{company.name}' created successfully.")
            return redirect('matching_app:company_detail', pk=company.pk)
        else:
            messages.error(request, "Please fix the errors below.")
    else:
        form = CompanyForm()

    return render(request, 'matching_app/company_form.html', {'form': form, 'is_edit': False})


def company_detail(request, pk):
    """Show details of a company and its jobs."""
    company = get_object_or_404(Company, pk=pk)
    jobs = company.jobs.all()
    return render(request, 'matching_app/company_detail.html', {'company': company, 'jobs': jobs})


@login_required(login_url='matching_app:login')
def company_edit(request, pk):
    """Edit company profile (Recruiters only; Admin can delete fraudulent company profiles)."""
    if not _is_recruiter_or_admin(request.user):
        messages.error(request, "Only approved recruiters can edit company profiles.")
        return redirect('matching_app:company_list')

    company = get_object_or_404(Company, pk=pk)

    if (request.user.is_staff or request.user.is_superuser) and not Job.objects.filter(posted_by=request.user).exists():
        messages.warning(request, "Company profile editing is managed by hiring recruiters. Administrators can inspect or delete fraudulent company profiles.")
        return redirect('matching_app:company_detail', pk=company.pk)

    if request.method == 'POST':
        form = CompanyForm(request.POST, request.FILES, instance=company)
        if form.is_valid():
            form.save()
            messages.success(request, f"Company '{company.name}' updated successfully.")
            return redirect('matching_app:company_detail', pk=company.pk)
        else:
            messages.error(request, "Please fix the errors below.")
    else:
        form = CompanyForm(instance=company)

    return render(request, 'matching_app/company_form.html', {'form': form, 'is_edit': True, 'company': company})


@login_required(login_url='matching_app:login')
@require_POST
def company_delete(request, pk):
    """Delete company profile and notify associated recruiter accounts on login."""
    if not _is_recruiter_or_admin(request.user):
        messages.error(request, "Only recruiters or administrators can delete company profiles.")
        return redirect('matching_app:company_list')

    company = get_object_or_404(Company, pk=pk)
    company_name = company.name

    # Deactivate associated recruiter user accounts and log deactivation reason
    recruiter_profiles = UserProfile.objects.filter(company_name__iexact=company_name)
    for prof in recruiter_profiles:
        prof.deactivation_reason = f"Your company registration '{company_name}' was removed by Administrator due to policy, terms, or safety violation."
        prof.save()
        prof.user.is_active = False
        prof.user.save()

    company.delete()
    messages.success(request, f"Company '{company_name}' was deleted.")
    return redirect('matching_app:company_list')


# ---------------------------------------------------------------------------
# RESUME UPLOAD & MANAGEMENT
# ---------------------------------------------------------------------------
@login_required(login_url='matching_app:login')
def upload_resume(request):
    """Upload PDF/DOCX resume and extract candidate skills via spaCy NLP."""
    if request.method == 'POST':
        form = ResumeUploadForm(request.POST, request.FILES)
        if form.is_valid():
            resume = form.save(commit=False)
            if request.user.is_authenticated:
                resume.user = request.user
            resume.save()

            try:
                extracted_text = extract_text_from_resume(resume.uploaded_resume.path)
                candidate_info = extract_candidate_info(extracted_text)
                skills_found = extract_skills(extracted_text)

                resume.extracted_text = extracted_text
                resume.extracted_skills = ", ".join(skills_found)
                resume.candidate_name = candidate_info.get('name', '') or (request.user.username if request.user.is_authenticated else '')
                resume.email = candidate_info.get('email', '') or (request.user.email if request.user.is_authenticated else '')
                resume.phone = candidate_info.get('phone', '')
                resume.education = candidate_info.get('education', '')
                resume.experience = candidate_info.get('experience', '')
                resume.save()

                messages.success(request, "Resume uploaded and processed successfully!")
                return redirect('matching_app:resume_detail', pk=resume.pk)

            except Exception as exc:
                resume.delete()
                messages.error(request, f"We couldn't process this resume: {exc}. Please upload a valid PDF or DOCX file.")
                return redirect('matching_app:upload_resume')
        else:
            messages.error(request, "Please fix the errors below and try again.")
    else:
        form = ResumeUploadForm()

    return render(request, 'matching_app/upload_resume.html', {'form': form})


@login_required(login_url='matching_app:login')
def resume_list(request):
    """Show list of candidate resumes."""
    if request.user.is_authenticated and hasattr(request.user, 'profile') and request.user.profile.role == 'JOB_SEEKER':
        resumes = Resume.objects.filter(user=request.user)
    else:
        resumes = Resume.objects.all()
    return render(request, 'matching_app/resume_list.html', {'resumes': resumes})


@login_required(login_url='matching_app:login')
def resume_detail(request, pk):
    """Show parsed candidate details and Resume Score."""
    resume = get_object_or_404(Resume, pk=pk)
    is_recruiter = _is_recruiter_or_admin(request.user)

    # Privacy check: Candidates can only view their own resume
    if not is_recruiter and resume.user and resume.user != request.user:
        messages.error(request, "Access denied: Candidates can only view their own resume profile.")
        return redirect('matching_app:jobseeker_dashboard')

    skills_list = skills_string_to_list(resume.extracted_skills)
    resume_score_data = calculate_resume_score(resume)

    file_size_display = ""
    try:
        file_size_display = human_readable_file_size(resume.uploaded_resume.size)
    except (FileNotFoundError, ValueError, OSError):
        file_size_display = "Unknown size"

    context = {
        'resume': resume,
        'skills_list': skills_list,
        'resume_score_data': resume_score_data,
        'is_recruiter': is_recruiter,
    }
    return render(request, 'matching_app/resume_detail.html', context)


@login_required(login_url='matching_app:login')
@require_POST
def resume_delete(request, pk):
    """Delete a resume."""
    resume = get_object_or_404(Resume, pk=pk)
    is_recruiter = _is_recruiter_or_admin(request.user)
    if not is_recruiter and resume.user and resume.user != request.user:
        messages.error(request, "Access denied: You can only delete your own resume.")
        return redirect('matching_app:jobseeker_dashboard')

    candidate_name = str(resume)
    resume.delete()
    messages.success(request, f"Resume for '{candidate_name}' was deleted.")
    return redirect('matching_app:resume_list')


# ---------------------------------------------------------------------------
# JOB MANAGEMENT WITH SEARCH & FILTERS
# ---------------------------------------------------------------------------
def job_list(request):
    """Explore jobs with search and category filters."""
    jobs = Job.objects.select_related('company').all()

    q = request.GET.get('q', '').strip()
    category = request.GET.get('category', '').strip()
    job_type = request.GET.get('job_type', '').strip()

    if q:
        jobs = jobs.filter(
            Q(job_title__icontains=q) |
            Q(company__name__icontains=q) |
            Q(company_name_legacy__icontains=q) |
            Q(required_skills__icontains=q) |
            Q(job_description__icontains=q)
        )

    if category:
        jobs = jobs.filter(category=category)

    if job_type:
        jobs = jobs.filter(job_type=job_type)

    context = {
        'jobs': jobs,
        'q': q,
        'selected_category': category,
        'selected_job_type': job_type,
        'category_choices': Job.JOB_CATEGORY_CHOICES,
        'job_type_choices': Job.JOB_TYPE_CHOICES,
        'is_recruiter': _is_recruiter_or_admin(request.user),
    }
    return render(request, 'matching_app/job_list.html', context)


@login_required(login_url='matching_app:login')
def job_create(request):
    """Post new job opening (Admin / Recruiter required)."""
    if not _is_recruiter_or_admin(request.user):
        messages.error(request, "Only recruiters or administrators can post new job openings.")
        return redirect('matching_app:job_list')

    user_company = None
    if hasattr(request.user, 'profile') and request.user.profile.company_name:
        comp_name = request.user.profile.company_name.strip()
        if comp_name:
            user_company, _ = Company.objects.get_or_create(name=comp_name)

    if request.method == 'POST':
        form = JobForm(request.POST)
        if form.is_valid():
            job = form.save(commit=False)
            job.posted_by = request.user
            # Automatically lock company to recruiter's registered company
            if user_company and not (request.user.is_staff or request.user.is_superuser):
                job.company = user_company
                job.company_name_legacy = user_company.name
            elif job.company:
                job.company_name_legacy = job.company.name

            job.save()
            messages.success(request, f"Job '{job.job_title}' was created successfully for {job.company_name}!")
            return redirect('matching_app:job_detail', pk=job.pk)
        else:
            messages.error(request, "Please fix the errors below and try again.")
    else:
        initial = {'company': user_company} if user_company else {}
        form = JobForm(initial=initial)

    context = {
        'form': form,
        'is_edit': False,
        'user_company': user_company,
    }
    return render(request, 'matching_app/job_form.html', context)


def job_detail(request, pk):
    """Show details of a single job opening and candidate's uploaded resumes."""
    job = get_object_or_404(Job, pk=pk)
    required_skills_list = skills_string_to_list(job.required_skills)
    
    existing_application = None
    user_resumes = []
    if request.user.is_authenticated:
        user_resumes = Resume.objects.filter(user=request.user)
        existing_application = JobApplication.objects.filter(resume__user=request.user, job=job).first()

    context = {
        'job': job,
        'required_skills_list': required_skills_list,
        'existing_application': existing_application,
        'user_resumes': user_resumes,
        'is_recruiter': _is_recruiter_or_admin(request.user),
    }
    return render(request, 'matching_app/job_detail.html', context)


@login_required(login_url='matching_app:login')
def job_edit(request, pk):
    """Edit existing job posting (Recruiter owner/company only)."""
    if not _is_recruiter_or_admin(request.user):
        messages.error(request, "Only approved recruiters can edit job postings.")
        return redirect('matching_app:job_list')

    job = get_object_or_404(Job, pk=pk)

    # Admin staff review safeguard
    if (request.user.is_staff or request.user.is_superuser) and job.posted_by and job.posted_by != request.user:
        messages.warning(request, "Job editing is reserved for hiring recruiters. Administrators can review or delete fraudulent job postings.")
        return redirect('matching_app:job_detail', pk=job.pk)

    # Recruiter permission check: must be job creator or belong to the same company
    if not (request.user.is_staff or request.user.is_superuser):
        user_company_name = request.user.profile.company_name.strip() if hasattr(request.user, 'profile') and request.user.profile.company_name else ""
        job_company_name = job.company.name.strip() if job.company else job.company_name_legacy.strip()

        is_owner = (job.posted_by == request.user)
        is_same_company = bool(user_company_name and job_company_name and user_company_name.lower() == job_company_name.lower())

        if not (is_owner or is_same_company):
            messages.error(request, "Access denied: You can only edit job postings created by your company.")
            return redirect('matching_app:job_list')

    user_company = None
    if hasattr(request.user, 'profile') and request.user.profile.company_name:
        comp_name = request.user.profile.company_name.strip()
        if comp_name:
            user_company, _ = Company.objects.get_or_create(name=comp_name)

    if request.method == 'POST':
        form = JobForm(request.POST, instance=job)
        if form.is_valid():
            updated_job = form.save(commit=False)
            if user_company and not (request.user.is_staff or request.user.is_superuser):
                updated_job.company = user_company
                updated_job.company_name_legacy = user_company.name
            elif updated_job.company:
                updated_job.company_name_legacy = updated_job.company.name

            updated_job.save()
            messages.success(request, f"Job '{job.job_title}' was updated successfully.")
            return redirect('matching_app:job_detail', pk=job.pk)
        else:
            messages.error(request, "Please fix the errors below and try again.")
    else:
        form = JobForm(instance=job)

    context = {
        'form': form,
        'is_edit': True,
        'job': job,
        'user_company': user_company,
    }
    return render(request, 'matching_app/job_form.html', context)


@login_required(login_url='matching_app:login')
@require_POST
def job_delete(request, pk):
    """Delete a job posting (Recruiter owner/company or Admin only)."""
    if not _is_recruiter_or_admin(request.user):
        messages.error(request, "Only recruiters or administrators can delete job postings.")
        return redirect('matching_app:job_list')

    job = get_object_or_404(Job, pk=pk)

    # Recruiter permission check: must be job creator, same company, or admin
    if not (request.user.is_staff or request.user.is_superuser):
        user_company_name = request.user.profile.company_name.strip() if hasattr(request.user, 'profile') and request.user.profile.company_name else ""
        job_company_name = job.company.name.strip() if job.company else job.company_name_legacy.strip()

        is_owner = (job.posted_by == request.user)
        is_same_company = bool(user_company_name and job_company_name and user_company_name.lower() == job_company_name.lower())

        if not (is_owner or is_same_company):
            messages.error(request, "Access denied: You can only delete job postings created by your company.")
            return redirect('matching_app:job_list')

    job_title = job.job_title
    job.delete()
    messages.success(request, f"Job '{job_title}' was deleted.")
    return redirect('matching_app:job_list')


# ---------------------------------------------------------------------------
# ATS JOB APPLICATION & STATUS WORKFLOW
# ---------------------------------------------------------------------------
@login_required(login_url='matching_app:login')
def apply_for_job(request, pk):
    """Allow job seeker to apply for a job with a selected resume."""
    job = get_object_or_404(Job, pk=pk)
    
    resume_id = request.POST.get('resume_id') or request.GET.get('resume_id')
    user_resume = None

    if resume_id:
        user_resume = Resume.objects.filter(pk=resume_id, user=request.user).first()

    if not user_resume:
        user_resume = Resume.objects.filter(user=request.user).first()

    if not user_resume:
        user_resume = Resume.objects.filter(email=request.user.email).first()

    if not user_resume:
        messages.error(request, "Please upload your resume before applying for jobs.")
        return redirect('matching_app:upload_resume')

    application, created = JobApplication.objects.get_or_create(
        resume=user_resume,
        job=job,
        defaults={'status': 'Applied'}
    )

    if created:
        messages.success(request, f"Successfully applied for '{job.job_title}' using resume '{user_resume.candidate_name or user_resume}'!")
    else:
        messages.info(request, f"You have already applied for '{job.job_title}'. Current Status: {application.status}")

    return redirect('matching_app:job_detail', pk=job.pk)



@login_required(login_url='matching_app:login')
@require_POST
def update_application_status(request, pk):
    """Allow recruiter to update candidate application status (Recruiter only; Admin views only)."""
    if (request.user.is_staff or request.user.is_superuser) and not Job.objects.filter(posted_by=request.user).exists():
        messages.warning(request, "Updating candidate status is reserved for hiring recruiters.")
        return redirect('matching_app:recruiter_dashboard')

    if not _is_recruiter_or_admin(request.user):
        messages.error(request, "Only recruiters can update candidate application statuses.")
        return redirect('matching_app:jobseeker_dashboard')

    application = get_object_or_404(JobApplication, pk=pk)
    form = JobApplicationStatusForm(request.POST, instance=application)
    if form.is_valid():
        form.save()
        messages.success(request, f"Updated application status for {application.resume.candidate_name} to '{application.status}'.")
    else:
        messages.error(request, "Failed to update application status.")

    return redirect('matching_app:recruiter_dashboard')


# ---------------------------------------------------------------------------
# RESUME-JOB MATCHING, RECOMMENDATIONS & PDF EXPORT
# ---------------------------------------------------------------------------
@login_required(login_url='matching_app:login')
def match_results(request, pk):
    """Compute AI match scores between resume and all jobs."""
    resume = get_object_or_404(Resume, pk=pk)

    if not resume.extracted_skills and not resume.extracted_text:
        messages.error(request, "This resume doesn't have extracted information yet. Please re-upload it.")
        return redirect('matching_app:resume_detail', pk=resume.pk)

    jobs = Job.objects.all()
    if not jobs.exists():
        messages.warning(request, "There are no jobs to match against yet.")
        return redirect('matching_app:job_list')

    try:
        for job in jobs:
            match_data = calculate_match(resume, job)
            missing_skills_list = match_data.get('missing_skills', [])
            recommended = recommend_skills_for_gap(missing_skills_list)

            MatchResult.objects.update_or_create(
                resume=resume,
                job=job,
                defaults={
                    'match_percentage': match_data.get('match_percentage', 0.0),
                    'missing_skills': ", ".join(missing_skills_list),
                    'recommended_skills': ", ".join(recommended),
                }
            )
    except Exception as exc:
        messages.error(request, f"Matching calculation failed: {exc}")
        return redirect('matching_app:resume_detail', pk=resume.pk)

    ranked_results = resume.match_results.select_related('job', 'job__company').order_by('-match_percentage')
    resume_skills_set = set(skills_string_to_list(resume.extracted_skills))

    context = {
        'resume': resume,
        'ranked_results': ranked_results,
        'resume_skills_set': resume_skills_set,
    }
    return render(request, 'matching_app/match_results.html', context)


@login_required(login_url='matching_app:login')
def recommendations(request, pk):
    """Show skill gap recommendations."""
    resume = get_object_or_404(Resume, pk=pk)
    ranked_results = resume.match_results.select_related('job', 'job__company').order_by('-match_percentage')

    if not ranked_results.exists():
        return redirect('matching_app:match_results', pk=resume.pk)

    context = {
        'resume': resume,
        'ranked_results': ranked_results,
    }
    return render(request, 'matching_app/recommendations.html', context)


@login_required(login_url='matching_app:login')
def download_match_pdf(request, pk):
    """Generate printable PDF report summary of match results."""
    resume = get_object_or_404(Resume, pk=pk)
    ranked_results = resume.match_results.select_related('job', 'job__company').order_by('-match_percentage')
    resume_score_data = calculate_resume_score(resume)

    context = {
        'resume': resume,
        'ranked_results': ranked_results,
        'resume_score_data': resume_score_data,
    }
    return render(request, 'matching_app/pdf_report.html', context)


# ---------------------------------------------------------------------------
# MESSAGING SYSTEM (RECRUITER <-> CANDIDATE)
# ---------------------------------------------------------------------------
@login_required(login_url='matching_app:login')
def inbox(request):
    """Display message conversations and allow Admin direct messaging/broadcast."""
    messages_list = Message.objects.filter(
        (Q(sender=request.user, deleted_by_sender=False) | Q(recipient=request.user, deleted_by_recipient=False))
    ).select_related('sender', 'recipient', 'related_job').order_by('-created_at')

    conversations = {}
    for msg in messages_list:
        other_user = msg.recipient if msg.sender == request.user else msg.sender
        if other_user.id not in conversations:
            conversations[other_user.id] = {
                'other_user': other_user,
                'last_message': msg,
                'unread_count': Message.objects.filter(sender=other_user, recipient=request.user, is_read=False, deleted_by_recipient=False).count()
            }

    # Fetch categorized users for Admin messaging
    jobseekers = User.objects.filter(profile__role='JOB_SEEKER').exclude(id=request.user.id).select_related('profile').order_by('username')
    recruiters = User.objects.filter(profile__role='RECRUITER').exclude(id=request.user.id).select_related('profile').order_by('username')

    if request.method == 'POST' and (request.user.is_staff or request.user.is_superuser):
        target_user_id = request.POST.get('recipient_user_id')
        target_username = request.POST.get('target_username', '').strip()
        subject = request.POST.get('subject', 'Notice from Administrator').strip()
        body = request.POST.get('body', '').strip()

        recipient = None
        if target_user_id:
            recipient = User.objects.filter(pk=target_user_id).first()
        elif target_username:
            recipient = User.objects.filter(username__iexact=target_username).first()

        if recipient and body:
            Message.objects.create(
                sender=request.user,
                recipient=recipient,
                subject=subject,
                body=body
            )
            messages.success(request, f"Message sent successfully to {recipient.username}!")
            return redirect('matching_app:conversation_detail', user_id=recipient.id)
        elif not recipient:
            messages.error(request, "Recipient user not found. Please select from the list or enter a valid username.")
        else:
            messages.error(request, "Message body cannot be empty.")

    context = {
        'conversations': conversations.values(),
        'unread_total': Message.objects.filter(recipient=request.user, is_read=False, deleted_by_recipient=False).count(),
        'jobseekers': jobseekers,
        'recruiters': recruiters,
    }
    return render(request, 'matching_app/inbox.html', context)


@login_required(login_url='matching_app:login')
def conversation_detail(request, user_id):
    """View conversation thread with another user (or inspect user-to-user thread for Admin audit)."""
    other_user = get_object_or_404(User, pk=user_id)
    sender_id = request.GET.get('sender_id')

    if (request.user.is_staff or request.user.is_superuser) and sender_id and str(sender_id) != str(request.user.id):
        sender_user = get_object_or_404(User, pk=sender_id)
        thread_messages = Message.objects.filter(
            (Q(sender=sender_user, recipient=other_user) | Q(sender=other_user, recipient=sender_user))
        ).select_related('sender', 'recipient', 'related_job').order_by('created_at')
        audit_mode = True
        header_title = f"Admin Audit: Thread between {sender_user.username} & {other_user.username}"
    else:
        Message.objects.filter(sender=other_user, recipient=request.user, is_read=False, deleted_by_recipient=False).update(is_read=True)
        thread_messages = Message.objects.filter(
            (Q(sender=request.user, recipient=other_user, deleted_by_sender=False) |
             Q(sender=other_user, recipient=request.user, deleted_by_recipient=False))
        ).select_related('sender', 'recipient', 'related_job').order_by('created_at')
        audit_mode = False
        header_title = f"Conversation with {other_user.username}"

    if request.method == 'POST':
        form = SendMessageForm(request.POST)
        if form.is_valid():
            msg = form.save(commit=False)
            msg.sender = request.user
            msg.recipient = other_user
            msg.save()
            messages.success(request, f"Message sent to {other_user.username}!")
            return redirect('matching_app:conversation_detail', user_id=other_user.id)
    else:
        form = SendMessageForm()

    context = {
        'other_user': other_user,
        'thread_messages': thread_messages,
        'form': form,
        'audit_mode': audit_mode,
        'header_title': header_title,
    }
    return render(request, 'matching_app/conversation.html', context)


@login_required(login_url='matching_app:login')
@require_POST
def delete_message(request, pk):
    """Delete an individual message for current user."""
    msg = get_object_or_404(Message, pk=pk)
    if msg.sender != request.user and msg.recipient != request.user and not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, "Permission denied.")
        return redirect('matching_app:inbox')

    if msg.sender == request.user:
        msg.deleted_by_sender = True
    if msg.recipient == request.user or request.user.is_staff or request.user.is_superuser:
        msg.deleted_by_recipient = True

    if msg.deleted_by_sender and msg.deleted_by_recipient:
        msg.delete()
    else:
        msg.save()

    messages.success(request, "Message deleted.")
    other_user_id = msg.recipient.id if msg.sender == request.user else msg.sender.id
    return redirect('matching_app:conversation_detail', user_id=other_user_id)


@login_required(login_url='matching_app:login')
@require_POST
def delete_conversation(request, user_id):
    """Delete an entire conversation thread with another user for current user."""
    other_user = get_object_or_404(User, pk=user_id)
    thread_messages = Message.objects.filter(
        (Q(sender=request.user, recipient=other_user) | Q(sender=other_user, recipient=request.user))
    )

    for msg in thread_messages:
        if msg.sender == request.user:
            msg.deleted_by_sender = True
        if msg.recipient == request.user:
            msg.deleted_by_recipient = True

        if msg.deleted_by_sender and msg.deleted_by_recipient:
            msg.delete()
        else:
            msg.save()

    messages.success(request, f"Conversation thread with {other_user.username} deleted.")
    return redirect('matching_app:inbox')


@login_required(login_url='matching_app:login')
def send_message(request, recipient_id):
    """Initiate a message to a specific recipient (candidate or recruiter)."""
    recipient = get_object_or_404(User, pk=recipient_id)
    job_id = request.GET.get('job_id')
    related_job = Job.objects.filter(pk=job_id).first() if job_id else None

    if request.method == 'POST':
        form = SendMessageForm(request.POST)
        if form.is_valid():
            msg = form.save(commit=False)
            msg.sender = request.user
            msg.recipient = recipient
            if related_job:
                msg.related_job = related_job
            msg.save()
            messages.success(request, f"Message sent to {recipient.username}!")
            return redirect('matching_app:conversation_detail', user_id=recipient.id)
    else:
        initial_subject = f"Regarding {related_job.job_title}" if related_job else ""
        form = SendMessageForm(initial={'subject': initial_subject})

    context = {
        'recipient': recipient,
        'related_job': related_job,
        'form': form,
    }
    return render(request, 'matching_app/send_message.html', context)


# ---------------------------------------------------------------------------
# AI SCREENING INTERVIEW & RE-ATTEMPT WORKFLOW
# ---------------------------------------------------------------------------
@login_required(login_url='matching_app:login')
@login_required(login_url='matching_app:login')
def invite_to_interview(request, app_id):
    """Allow recruiter to propose 3 interview time slots for an AI Mock Screening Interview."""
    if not _is_recruiter_or_admin(request.user):
        messages.error(request, "Only recruiters can send interview invitations.")
        return redirect('matching_app:recruiter_dashboard')

    application = get_object_or_404(JobApplication, pk=app_id)
    candidate_user = application.resume.user

    if not candidate_user:
        messages.error(request, "Cannot send interview invite: Candidate does not have an active user account.")
        return redirect('matching_app:recruiter_dashboard')

    session = InterviewSession.objects.filter(application=application, candidate=candidate_user, job=application.job).first()

    now = timezone.now()
    default_slot1 = (now + timedelta(hours=2)).strftime('%Y-%m-%dT%H:%M')
    default_slot2 = (now + timedelta(days=1)).replace(hour=10, minute=0, second=0).strftime('%Y-%m-%dT%H:%M')
    default_slot3 = (now + timedelta(days=1)).replace(hour=15, minute=0, second=0).strftime('%Y-%m-%dT%H:%M')

    if request.method == 'POST':
        form = InterviewScheduleForm(request.POST)
        if form.is_valid():
            if not session:
                session = InterviewSession.objects.create(
                    application=application,
                    candidate=candidate_user,
                    job=application.job,
                    status='Pending'
                )

            session.slot_1 = form.cleaned_data['slot_1']
            session.slot_2 = form.cleaned_data['slot_2']
            session.slot_3 = form.cleaned_data['slot_3']
            session.save()

            if not session.questions.exists():
                questions_text = generate_interview_questions(application.job)
                for idx, q_text in enumerate(questions_text, start=1):
                    InterviewQA.objects.create(
                        session=session,
                        question_number=idx,
                        question_text=q_text
                    )

            s1_str = session.slot_1.strftime('%b %d, %Y at %I:%M %p')
            s2_str = session.slot_2.strftime('%b %d, %Y at %I:%M %p')
            s3_str = session.slot_3.strftime('%b %d, %Y at %I:%M %p')

            s1_link = request.build_absolute_uri(f"/interview/{session.id}/select-slot/1/")
            s2_link = request.build_absolute_uri(f"/interview/{session.id}/select-slot/2/")
            s3_link = request.build_absolute_uri(f"/interview/{session.id}/select-slot/3/")

            msg_body = (
                f"Hi {candidate_user.username},\n\n"
                f"You are invited to attend an AI Mock Screening Interview for the '{application.job.job_title}' position.\n\n"
                f"Please choose your preferred interview time slot from the 3 proposed schedules below:\n\n"
                f"1️⃣ Option 1: {s1_str}\nSelect Option 1: {s1_link}\n\n"
                f"2️⃣ Option 2: {s2_str}\nSelect Option 2: {s2_link}\n\n"
                f"3️⃣ Option 3: {s3_str}\nSelect Option 3: {s3_link}\n\n"
                f"Note: Once you select your time slot, your proctored interview room will be confirmed for that schedule."
            )

            Message.objects.create(
                sender=request.user,
                recipient=candidate_user,
                subject=f"AI Interview Schedule Proposal: {application.job.job_title}",
                body=msg_body,
                related_job=application.job
            )

            application.status = 'Under Review'
            application.save()

            messages.success(request, f"Proposed 3 interview time slots and sent invitation to {candidate_user.username}!")
            return redirect('matching_app:recruiter_dashboard')
        else:
            messages.error(request, "Please specify valid future date and time slots.")
    else:
        form = InterviewScheduleForm(initial={
            'slot_1': default_slot1,
            'slot_2': default_slot2,
            'slot_3': default_slot3,
        })

    context = {
        'application': application,
        'candidate_user': candidate_user,
        'form': form,
    }
    return render(request, 'matching_app/invite_interview.html', context)


@login_required(login_url='matching_app:login')
def select_interview_slot(request, session_id, slot_num):
    """Allow candidate to select their preferred interview time slot from the 3 proposed options."""
    session = get_object_or_404(InterviewSession, pk=session_id)
    if request.user != session.candidate and not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, "Access restricted to the invited candidate.")
        return redirect('matching_app:home')

    chosen_dt = None
    if slot_num == 1:
        chosen_dt = session.slot_1
    elif slot_num == 2:
        chosen_dt = session.slot_2
    elif slot_num == 3:
        chosen_dt = session.slot_3

    if not chosen_dt:
        messages.error(request, "Invalid time slot selected.")
        return redirect('matching_app:jobseeker_dashboard')

    session.chosen_slot = chosen_dt
    session.scheduled_at = timezone.now()
    session.save()

    slot_str = chosen_dt.strftime('%b %d, %Y at %I:%M %p')

    # Send confirmation message to recruiter
    msg_recruiter = (
        f"Hello! Candidate {session.candidate.username} has confirmed their AI Screening Interview for "
        f"'{session.job.job_title}' on {slot_str}."
    )
    recruiter_user = session.job.posted_by or session.application.resume.user
    if recruiter_user:
        Message.objects.create(
            sender=session.candidate,
            recipient=recruiter_user,
            subject=f"Interview Confirmed: {session.candidate.username} - {session.job.job_title}",
            body=msg_recruiter,
            related_job=session.job
        )

    messages.success(request, f"🎉 Interview Confirmed! Your AI Screening Interview is scheduled for {slot_str}.")
    return redirect('matching_app:jobseeker_dashboard')


@login_required(login_url='matching_app:login')
def interview_room(request, session_id):
    """Proctored AI Chatbot Interview Room for candidates."""
    session = get_object_or_404(InterviewSession, pk=session_id)
    is_staff_or_recruiter = _is_recruiter_or_admin(request.user)

    if request.user != session.candidate and not is_staff_or_recruiter:
        messages.error(request, "Access restricted to the invited candidate.")
        return redirect('matching_app:home')

    # Enforce time schedule gate for candidates
    if not is_staff_or_recruiter:
        if not session.chosen_slot and session.slot_1:
            messages.warning(request, "Please select your preferred interview time slot before entering the room.")
            return redirect('matching_app:jobseeker_dashboard')

        if session.chosen_slot and not session.is_room_open:
            slot_str = session.chosen_slot.strftime('%b %d, %Y at %I:%M %p')
            messages.warning(
                request,
                f"⏰ The interview room is not open yet! Your interview for '{session.job.job_title}' is scheduled for {slot_str}. "
                "The room will open 15 minutes prior to your scheduled time."
            )
            return redirect('matching_app:jobseeker_dashboard')

    if session.status == 'Pending':
        session.status = 'In Progress'
        if not session.started_at:
            session.started_at = timezone.now()
        session.save()
    elif session.status == 'In Progress' and not session.started_at:
        session.started_at = timezone.now()
        session.save()

    # Enforce timer expiration check
    if session.status == 'In Progress' and session.is_expired:
        session.status = 'Completed'
        session.completed_at = timezone.now()
        session.save()
        evaluate_interview_answers(session)
        messages.info(request, "⏰ Your interview session time limit has expired. Your responses have been automatically submitted for evaluation.")

    questions = session.questions.all().order_by('question_number')

    context = {
        'session': session,
        'questions': questions,
        'total_questions': questions.count(),
        'remaining_seconds': session.remaining_seconds,
    }
    return render(request, 'matching_app/interview_room.html', context)


@login_required(login_url='matching_app:login')
@require_POST
def expire_interview_session(request, session_id):
    """AJAX endpoint triggered when client interview countdown timer reaches 00:00."""
    session = get_object_or_404(InterviewSession, pk=session_id, candidate=request.user)

    if session.status == 'In Progress':
        session.status = 'Completed'
        session.completed_at = timezone.now()
        session.save()
        evaluate_interview_answers(session)

    return JsonResponse({'success': True, 'status': session.status})


@login_required(login_url='matching_app:login')
@require_POST
def submit_interview_answer(request, session_id):
    """AJAX endpoint to record candidate's answer for a question."""
    session = get_object_or_404(InterviewSession, pk=session_id, candidate=request.user)

    if session.status in ['Completed', 'Terminated (Tab Switch Violation)']:
        return JsonResponse({'error': 'Interview session is already closed.'}, status=400)

    question_id = request.POST.get('question_id')
    answer_text = request.POST.get('answer_text', '').strip()

    qa = get_object_or_404(InterviewQA, pk=question_id, session=session)
    qa.candidate_answer = answer_text
    qa.save()

    # Check if all questions have candidate answers (or if finish=true)
    unanswered = session.questions.filter(candidate_answer='').exists()
    is_completed = False

    if not unanswered or request.POST.get('finish') == 'true':
        session.status = 'Completed'
        session.completed_at = timezone.now()
        session.save()
        evaluate_interview_answers(session)
        is_completed = True

    return JsonResponse({
        'success': True,
        'is_completed': is_completed,
        'ai_evaluation_score': session.ai_evaluation_score if is_completed else None
    })


@login_required(login_url='matching_app:login')
@require_POST
def record_tab_switch(request, session_id):
    """AJAX endpoint to increment tab switch warnings and auto-terminate if > 3 violations."""
    session = get_object_or_404(InterviewSession, pk=session_id, candidate=request.user)

    if session.status in ['Completed', 'Terminated (Tab Switch Violation)']:
        return JsonResponse({'status': session.status, 'terminated': True})

    session.tab_switch_count += 1
    terminated = False

    if session.tab_switch_count > 3:
        session.status = 'Terminated (Tab Switch Violation)'
        session.completed_at = timezone.now()
        session.save()
        evaluate_interview_answers(session)
        terminated = True
    else:
        session.save()

    return JsonResponse({
        'tab_switch_count': session.tab_switch_count,
        'warnings_remaining': max(0, 3 - session.tab_switch_count),
        'terminated': terminated
    })


@login_required(login_url='matching_app:login')
def interview_transcript(request, session_id):
    """Recruiter evaluation view to inspect candidate Q&A transcript and AI evaluation score."""
    session = get_object_or_404(InterviewSession, pk=session_id)

    if not _is_recruiter_or_admin(request.user) and request.user != session.candidate:
        messages.error(request, "Access restricted.")
        return redirect('matching_app:home')

    questions = session.questions.all().order_by('question_number')

    context = {
        'session': session,
        'questions': questions,
        'is_recruiter': _is_recruiter_or_admin(request.user),
    }
    return render(request, 'matching_app/interview_transcript.html', context)


@login_required(login_url='matching_app:login')
@require_POST
def request_interview_reattempt(request, session_id):
    """Allow candidate to submit a re-attempt request with an explanatory note."""
    session = get_object_or_404(InterviewSession, pk=session_id, candidate=request.user)
    reason = request.POST.get('reason', '').strip()

    if not reason:
        messages.error(request, "Please provide a reason for your re-attempt request.")
        return redirect('matching_app:interview_room', session_id=session.id)

    session.is_reattempt_requested = True
    session.reattempt_reason = reason
    session.reattempt_status = 'Requested'
    session.reattempt_requested_at = timezone.now()
    session.save()

    recruiter_user = session.job.posted_by
    if recruiter_user:
        msg_body = (
            f"Candidate {request.user.username} has submitted a Re-Attempt Request for the '{session.job.job_title}' screening interview.\n\n"
            f"Candidate Note / Reason:\n\"{reason}\"\n\n"
            f"Please visit your Recruiter Dashboard or Candidate Transcript view to Approve or Decline this retake request."
        )
        Message.objects.create(
            sender=request.user,
            recipient=recruiter_user,
            subject=f"Interview Re-Attempt Request: {request.user.username}",
            body=msg_body,
            related_job=session.job
        )

    messages.success(request, "Your interview re-attempt request was submitted to the recruiter for review!")
    return redirect('matching_app:interview_room', session_id=session.id)


@login_required(login_url='matching_app:login')
@require_POST
def decide_interview_reattempt(request, session_id):
    """Allow recruiter to Approve or Decline candidate's interview re-attempt request."""
    if not _is_recruiter_or_admin(request.user):
        messages.error(request, "Access restricted to recruiters.")
        return redirect('matching_app:recruiter_dashboard')

    session = get_object_or_404(InterviewSession, pk=session_id)
    decision = request.POST.get('decision', '').strip().lower()

    if decision == 'approve':
        session.status = 'Pending'
        session.tab_switch_count = 0
        session.ai_evaluation_score = 0.0
        session.ai_summary = ""
        session.completed_at = None
        session.started_at = None
        session.reattempt_status = 'Approved'
        session.save()

        # Reset questions
        session.questions.update(candidate_answer='', score=0.0, ai_feedback='')

        # Notify candidate via internal message
        msg_body = (
            f"Great news, {session.candidate.username}!\n\n"
            f"Your Re-Attempt Request for the '{session.job.job_title}' AI screening interview has been APPROVED by the employer.\n\n"
            f"Your previous session has been reset. You may re-enter your proctored interview room at any time to retake the interview:\n"
            f"{request.build_absolute_uri(f'/interview/{session.id}/')}"
        )
        Message.objects.create(
            sender=request.user,
            recipient=session.candidate,
            subject=f"Re-Attempt Request APPROVED: {session.job.job_title}",
            body=msg_body,
            related_job=session.job
        )

        messages.success(request, f"Re-attempt request APPROVED for {session.candidate.username}. Session has been reset.")

    elif decision == 'decline':
        session.reattempt_status = 'Declined'
        session.save()

        msg_body = (
            f"Hello {session.candidate.username},\n\n"
            f"Regarding your Re-Attempt Request for '{session.job.job_title}': "
            f"The recruiter has reviewed your request and decided to proceed with your original evaluation results."
        )
        Message.objects.create(
            sender=request.user,
            recipient=session.candidate,
            subject=f"Re-Attempt Request Update: {session.job.job_title}",
            body=msg_body,
            related_job=session.job
        )

        messages.info(request, f"Re-attempt request DECLINED for {session.candidate.username}.")

    return redirect('matching_app:interview_transcript', session_id=session.id)