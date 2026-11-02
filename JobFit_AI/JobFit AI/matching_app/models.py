"""
Database models for the matching_app application.

Models defined:
    1. Company          - Stores employer profile details, website, and company logo.
    2. Resume           - Stores candidate details, extracted text, skills, and uploaded PDF/DOCX resume file.
    3. Job              - Stores job description (JD), required skills, location, salary, category, and deadline.
    4. MatchResult      - Stores calculated AI match scores, missing skills, and recommendations.
    5. UserProfile      - Extended user metadata (roles: JOB_SEEKER or RECRUITER, phone, company_name, is_approved).
    6. JobApplication    - ATS application status workflow (Applied, Under Review, Shortlisted, Rejected).
    7. Message          - Internal messaging system between Job Seekers and Recruiters.
    8. InterviewSession - AI Screening Interview session with proctoring violations, re-attempt requests & evaluation score.
    9. InterviewQA      - Individual interview question, candidate answer, score, and AI feedback.
"""

from django.db import models
from django.contrib.auth.models import User


class UserProfile(models.Model):
    """
    Extends the default Django User model with Role-based authentication
    (Job Seeker vs Recruiter), contact metadata, and Admin Approval state.
    """
    ROLE_CHOICES = [
        ('JOB_SEEKER', 'Job Seeker'),
        ('RECRUITER', 'Recruiter / Employer'),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile",
        verbose_name="User Account",
    )
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='JOB_SEEKER',
        verbose_name="User Role",
    )
    phone = models.CharField(
        max_length=30,
        blank=True,
        verbose_name="Phone Number",
    )
    company_name = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Company Name (Recruiters)",
    )
    is_approved = models.BooleanField(
        default=True,
        verbose_name="Admin Approved",
        help_text="Set to False for pending recruiter registrations until verified by Admin.",
    )
    profile_picture = models.ImageField(
        upload_to="profile_pics/",
        blank=True,
        null=True,
        verbose_name="Profile Picture",
        help_text="Upload a professional profile photo (JPG, PNG, WEBP).",
    )
    deactivation_reason = models.TextField(
        blank=True,
        default='',
        verbose_name="Deactivation / Removal Reason",
        help_text="Explanatory reason displayed to user on login attempt if account/company was deleted by Admin."
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        null=True,
        blank=True,
        verbose_name="Created At",
    )

    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"

    def __str__(self):
        status = "Approved" if self.is_approved else "Pending Approval"
        return f"{self.user.username} ({self.get_role_display()}) [{status}]"


class Company(models.Model):
    """
    Represents a hiring organization/employer.
    Includes company name, logo, contact email, website, and description.
    """
    name = models.CharField(
        max_length=200,
        unique=True,
        verbose_name="Company Name",
        help_text="Official name of the hiring organization.",
    )
    logo = models.ImageField(
        upload_to="company_logos/",
        blank=True,
        null=True,
        verbose_name="Company Logo",
        help_text="Upload company brand logo image.",
    )
    description = models.TextField(
        blank=True,
        verbose_name="Description",
        help_text="Brief summary of company culture, products, and vision.",
    )
    website = models.URLField(
        blank=True,
        verbose_name="Website URL",
        help_text="Official corporate website (e.g., https://company.com).",
    )
    location = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Headquarters / Location",
        help_text="City, State/Country where company is based.",
    )
    email = models.EmailField(
        blank=True,
        verbose_name="Contact Email",
        help_text="Recruitment or HR contact email address.",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Created At",
    )

    class Meta:
        verbose_name = "Company"
        verbose_name_plural = "Companies"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Resume(models.Model):
    """
    Represents a candidate's uploaded resume file and extracted NLP metadata.
    Contains parsed skills, education, work experience, and reference to raw file.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="resumes",
        verbose_name="User Account",
        help_text="User account that uploaded this resume.",
    )
    candidate_name = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Candidate Name",
        help_text="Full name of the candidate extracted from the resume.",
    )
    email = models.EmailField(
        blank=True,
        verbose_name="Email Address",
        help_text="Email address extracted from the resume.",
    )
    phone = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Phone Number",
        help_text="Phone number extracted from the resume.",
    )
    uploaded_resume = models.FileField(
        upload_to="resumes/",
        verbose_name="Uploaded File",
        help_text="Original PDF or DOCX resume document file.",
    )
    extracted_text = models.TextField(
        blank=True,
        verbose_name="Extracted Raw Text",
        help_text="Full unparsed text content extracted from document parser.",
    )
    extracted_skills = models.TextField(
        blank=True,
        verbose_name="Extracted Skills",
        help_text="Comma-separated list of skills identified by NLP PhraseMatcher.",
    )
    education = models.TextField(
        blank=True,
        verbose_name="Education Details",
        help_text="Educational qualifications extracted from the resume.",
    )
    experience = models.TextField(
        blank=True,
        verbose_name="Experience Details",
        help_text="Work experience details extracted from the resume.",
    )
    uploaded_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Uploaded At",
        help_text="Date and time the resume was uploaded.",
    )

    class Meta:
        verbose_name = "Resume"
        verbose_name_plural = "Resumes"
        ordering = ["-uploaded_at"]

    def __str__(self):
        return self.candidate_name if self.candidate_name else f"Resume #{self.pk}"


class Job(models.Model):
    """
    Represents a job description (JD) linked to a Company.
    Includes job title, description, category, job type, location, salary, deadline, and required skills.
    """
    JOB_TYPE_CHOICES = [
        ("Full Time", "Full Time"),
        ("Part Time", "Part Time"),
        ("Internship", "Internship"),
        ("Contract", "Contract"),
        ("Remote", "Remote"),
    ]

    JOB_CATEGORY_CHOICES = [
        ("IT & Software", "IT & Software"),
        ("Data Science & AI", "Data Science & AI"),
        ("DevOps & Cloud", "DevOps & Cloud"),
        ("Product Management", "Product Management"),
        ("Design & UI/UX", "Design & UI/UX"),
        ("Marketing & Sales", "Marketing & Sales"),
        ("Other", "Other"),
    ]

    job_title = models.CharField(
        max_length=200,
        verbose_name="Job Title",
        help_text="The title of the job position (e.g., Backend Developer).",
    )
    posted_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="posted_jobs",
        verbose_name="Recruiter Account",
        help_text="Recruiter who posted this job.",
    )
    company = models.ForeignKey(
        Company,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="jobs",
        verbose_name="Company",
        help_text="The company offering this job.",
    )
    company_name_legacy = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Legacy Company Name",
        help_text="Fallback company name if unlinked to a Company model.",
    )
    category = models.CharField(
        max_length=100,
        choices=JOB_CATEGORY_CHOICES,
        default="IT & Software",
        verbose_name="Job Category",
    )
    job_type = models.CharField(
        max_length=50,
        choices=JOB_TYPE_CHOICES,
        default="Full Time",
        verbose_name="Job Type",
    )
    location = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Location",
        help_text="City, State or Remote (e.g., San Francisco, CA or Remote).",
    )
    salary = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Salary / Compensation",
        help_text="Salary range or text (e.g., $90,000 - $120,000 / year).",
    )
    vacancies = models.PositiveIntegerField(
        default=1,
        verbose_name="Vacancies",
        help_text="Number of open positions.",
    )
    deadline = models.DateField(
        null=True,
        blank=True,
        verbose_name="Application Deadline",
        help_text="Last date to apply for this position.",
    )
    job_description = models.TextField(
        verbose_name="Job Description",
        help_text="Full text of the job description used for semantic vector matching.",
    )
    required_skills = models.TextField(
        blank=True,
        verbose_name="Required Skills",
        help_text="Comma-separated list of required technical skills.",
    )
    required_experience = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Required Experience",
        help_text="Minimum experience required (e.g., 2-4 years).",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Posted At",
    )

    class Meta:
        verbose_name = "Job"
        verbose_name_plural = "Jobs"
        ordering = ["-created_at"]

    def __str__(self):
        comp = self.company.name if self.company else self.company_name_legacy
        return f"{self.job_title} at {comp}" if comp else self.job_title

    @property
    def company_name(self):
        """Helper property returning linked company name or legacy name fallback."""
        if self.company:
            return self.company.name
        return self.company_name_legacy or "Independent Hiring"

    @property
    def posted_at(self):
        """Alias property for created_at timestamp."""
        return self.created_at


class MatchResult(models.Model):
    """
    Stores calculated AI match evaluation scores between a Candidate Resume and a Job.
    Calculated via: (0.6 * Skill Overlap) + (0.4 * Sentence-BERT Cosine Similarity).
    """
    resume = models.ForeignKey(
        Resume,
        on_delete=models.CASCADE,
        related_name="match_results",
        verbose_name="Resume",
    )
    job = models.ForeignKey(
        Job,
        on_delete=models.CASCADE,
        related_name="match_results",
        verbose_name="Job",
    )
    match_percentage = models.FloatField(
        default=0.0,
        verbose_name="Match Percentage",
        help_text="Overall hybrid score (0-100%).",
    )
    missing_skills = models.TextField(
        blank=True,
        verbose_name="Missing Skills",
        help_text="Comma-separated skills present in Job requirements but missing in Resume.",
    )
    recommended_skills = models.TextField(
        blank=True,
        verbose_name="Recommended Skills / Certifications",
        help_text="Recommended learning roadmap and certifications.",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Created At",
    )

    class Meta:
        verbose_name = "Match Result"
        verbose_name_plural = "Match Results"
        ordering = ["-match_percentage"]

    def __str__(self):
        return f"{self.resume} <-> {self.job} ({self.match_percentage}%)"


class JobApplication(models.Model):
    """
    Tracks candidate job application submissions and ATS status workflow.
    Statuses: Applied -> Under Review -> Shortlisted -> Rejected.
    """
    STATUS_CHOICES = [
        ('Applied', 'Applied'),
        ('Under Review', 'Under Review'),
        ('Shortlisted', 'Shortlisted'),
        ('Rejected', 'Rejected'),
    ]

    resume = models.ForeignKey(
        Resume,
        on_delete=models.CASCADE,
        related_name="applications",
        verbose_name="Candidate Resume",
    )
    job = models.ForeignKey(
        Job,
        on_delete=models.CASCADE,
        related_name="applications",
        verbose_name="Applied Job",
    )
    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default='Applied',
        verbose_name="Application Status",
    )
    applied_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        verbose_name = "Job Application"
        verbose_name_plural = "Job Applications"
        unique_together = ('resume', 'job')
        ordering = ['-applied_at']

    def __str__(self):
        return f"{self.resume.candidate_name} -> {self.job.job_title} [{self.status}]"


class Message(models.Model):
    """
    Internal messaging system between Recruiters and Job Seekers.
    """
    sender = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="sent_messages",
        verbose_name="Sender",
    )
    recipient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="received_messages",
        verbose_name="Recipient",
    )
    subject = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Subject",
    )
    body = models.TextField(
        verbose_name="Message Body",
    )
    related_job = models.ForeignKey(
        Job,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="job_messages",
        verbose_name="Related Job Opening",
    )
    is_read = models.BooleanField(
        default=False,
        verbose_name="Is Read",
    )
    deleted_by_sender = models.BooleanField(
        default=False,
        verbose_name="Deleted by Sender",
        help_text="Flag if sender deleted message from their chat view.",
    )
    deleted_by_recipient = models.BooleanField(
        default=False,
        verbose_name="Deleted by Recipient",
        help_text="Flag if recipient deleted message from their chat view.",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Created At",
    )

    class Meta:
        verbose_name = "Message"
        verbose_name_plural = "Messages"
        ordering = ["-created_at"]

    def __str__(self):
        return f"From {self.sender.username} to {self.recipient.username}: {self.subject[:30]}"


class InterviewSession(models.Model):
    """
    Represents an AI Mock Screening Interview session.
    Tracks proctoring violations (tab switches), completion status, re-attempt requests, and AI score evaluation.
    """
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('In Progress', 'In Progress'),
        ('Completed', 'Completed'),
        ('Terminated (Tab Switch Violation)', 'Terminated (Tab Switch Violation)'),
    ]

    REATTEMPT_STATUS_CHOICES = [
        ('None', 'None'),
        ('Requested', 'Requested'),
        ('Approved', 'Approved'),
        ('Declined', 'Declined'),
    ]

    application = models.ForeignKey(
        JobApplication,
        on_delete=models.CASCADE,
        related_name="interview_sessions",
        verbose_name="Job Application",
    )
    candidate = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="interview_sessions",
        verbose_name="Candidate",
    )
    job = models.ForeignKey(
        Job,
        on_delete=models.CASCADE,
        related_name="interview_sessions",
        verbose_name="Target Job Opening",
    )
    status = models.CharField(
        max_length=50,
        choices=STATUS_CHOICES,
        default='Pending',
        verbose_name="Session Status",
    )
    tab_switch_count = models.PositiveIntegerField(
        default=0,
        verbose_name="Tab Switch Warnings Count",
        help_text="Number of times browser tab switching or window blur was detected.",
    )
    ai_evaluation_score = models.FloatField(
        default=0.0,
        verbose_name="AI Evaluation Score (%)",
        help_text="Overall candidate response score (0-100%).",
    )
    ai_summary = models.TextField(
        blank=True,
        verbose_name="AI Summary Feedback",
        help_text="Overall strengths, key answers evaluation, and shortlisting recommendation.",
    )
    is_reattempt_requested = models.BooleanField(
        default=False,
        verbose_name="Re-Attempt Requested",
    )
    reattempt_reason = models.TextField(
        blank=True,
        verbose_name="Candidate Re-Attempt Reason Note",
    )
    reattempt_status = models.CharField(
        max_length=30,
        choices=REATTEMPT_STATUS_CHOICES,
        default='None',
        verbose_name="Re-Attempt Request Status",
    )
    slot_1 = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Proposed Slot 1",
    )
    slot_2 = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Proposed Slot 2",
    )
    slot_3 = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Proposed Slot 3",
    )
    chosen_slot = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Chosen Scheduled Slot",
    )
    scheduled_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Slot Selection Timestamp",
    )
    reattempt_requested_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Re-Attempt Requested At",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Created At",
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Completed At",
    )
    duration_minutes = models.PositiveIntegerField(
        default=10,
        verbose_name="Interview Duration Limit (Minutes)",
        help_text="Time limit allocated for completing the screening interview.",
    )
    started_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Session Started Timestamp",
        help_text="Timestamp when candidate entered the active interview room.",
    )

    class Meta:
        verbose_name = "Interview Session"
        verbose_name_plural = "Interview Sessions"
        ordering = ['-created_at']

    def __str__(self):
        return f"Interview: {self.candidate.username} for {self.job.job_title} [{self.status}]"

    @property
    def remaining_seconds(self):
        """Returns remaining seconds for active interview session, or 0 if expired."""
        if not self.started_at:
            return self.duration_minutes * 60
        from django.utils import timezone
        elapsed = (timezone.now() - self.started_at).total_seconds()
        total_allowed = self.duration_minutes * 60
        return max(0, int(total_allowed - elapsed))

    @property
    def is_expired(self):
        """Check if active session duration has elapsed."""
        if self.status in ['Completed', 'Terminated (Tab Switch Violation)']:
            return True
        if self.started_at:
            return self.remaining_seconds <= 0
        return False

    @property
    def is_room_open(self):
        """
        Check if candidate can enter the interview room based on scheduled slot.
        - Open if session is already 'In Progress'.
        - If candidate selected a chosen_slot, room opens 15 minutes prior to chosen_slot and remains open for a 3-hour grace window.
        - If session has no slot_1 (legacy/direct invite without 3-slot proposal), room is open.
        """
        from django.utils import timezone
        from datetime import timedelta

        if self.status in ['Completed', 'Terminated (Tab Switch Violation)']:
            return False

        if self.status == 'In Progress':
            return True

        if self.chosen_slot:
            # Open 15 minutes prior to scheduled slot up to 3 hours after scheduled time
            earliest_open = self.chosen_slot - timedelta(minutes=15)
            latest_open = self.chosen_slot + timedelta(hours=3)
            return earliest_open <= timezone.now() <= latest_open

        if not self.slot_1:
            return True

        return False

    @property
    def is_missed(self):
        """
        Check if candidate missed their scheduled interview window (> 3 hours past chosen_slot).
        """
        if self.status in ['Completed', 'Terminated (Tab Switch Violation)']:
            return False
        if self.status == 'In Progress':
            return False
        if self.chosen_slot:
            from django.utils import timezone
            from datetime import timedelta
            return timezone.now() > (self.chosen_slot + timedelta(hours=3))
        return False


class InterviewQA(models.Model):
    """
    Stores individual question, candidate answer, score, and AI feedback within an InterviewSession.
    """
    session = models.ForeignKey(
        InterviewSession,
        on_delete=models.CASCADE,
        related_name="questions",
        verbose_name="Interview Session",
    )
    question_number = models.PositiveIntegerField(
        verbose_name="Question Number",
    )
    question_text = models.TextField(
        verbose_name="Question Text",
    )
    candidate_answer = models.TextField(
        blank=True,
        verbose_name="Candidate Answer",
    )
    score = models.FloatField(
        default=0.0,
        verbose_name="Question Score (%)",
    )
    ai_feedback = models.TextField(
        blank=True,
        verbose_name="AI Feedback",
    )

    class Meta:
        verbose_name = "Interview Question & Answer"
        verbose_name_plural = "Interview Questions & Answers"
        ordering = ['question_number']

    def __str__(self):
        return f"Q{self.question_number} ({self.session.candidate.username}): {self.question_text[:40]}"


class UserReport(models.Model):
    """
    Model for candidate/recruiter safety reporting.
    Allows reporting suspicious accounts, scams, harassment, or fake job postings.
    """
    REPORT_REASONS = [
        ('SCAM', 'Scam / Fraud / Requesting Money'),
        ('FAKE_JOB', 'Fake Job Offer / Impersonation'),
        ('HARASSMENT', 'Inappropriate Behavior / Harassment'),
        ('SPAM', 'Spam / Unsolicited Messages'),
        ('OTHER', 'Other Safety Violation'),
    ]

    reporter = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="submitted_reports",
        verbose_name="Reporter User",
    )
    reported_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="received_reports",
        verbose_name="Reported User",
    )
    related_job = models.ForeignKey(
        Job,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Related Job Opening",
    )
    reason = models.CharField(
        max_length=50,
        choices=REPORT_REASONS,
        default='OTHER',
        verbose_name="Violation Reason",
    )
    description = models.TextField(
        verbose_name="Report Description",
        help_text="Detailed explanation of the safety report.",
    )
    status = models.CharField(
        max_length=20,
        default='Pending',
        choices=[('Pending', 'Pending Review'), ('Resolved', 'Resolved / Action Taken'), ('Dismissed', 'Dismissed')],
        verbose_name="Review Status",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Reported At",
    )

    class Meta:
        verbose_name = "User Safety Report"
        verbose_name_plural = "User Safety Reports"
        ordering = ['-created_at']

    def __str__(self):
        return f"Report by {self.reporter.username} against {self.reported_user.username} [{self.get_reason_display()}]"
