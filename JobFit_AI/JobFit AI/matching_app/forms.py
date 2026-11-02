"""
Forms for the matching_app application.

Forms defined:
    1. ResumeUploadForm         - candidate resume upload validation
    2. CompanyForm              - create/edit company profile & logo
    3. JobForm                  - create/edit job openings
    4. AdminLoginForm           - login authentication
    5. JobSeekerSignUpForm      - candidate registration
    6. RecruiterSignUpForm      - employer/recruiter registration
    7. JobApplicationStatusForm  - ATS application status updater
    8. UserProfileEditForm      - edit profile contact info
    9. CustomPasswordChangeForm - password change form
   10. ForgotPasswordForm       - password reset request form
   11. SendMessageForm          - recruiter <-> candidate messaging form
"""

import os
from django import forms
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm

from .models import Resume, Job, Company, UserProfile, JobApplication, Message, InterviewSession


COUNTRY_CODE_CHOICES = [
    ('+91', '🇮🇳 India (+91)'),
    ('+1', '🇺🇸/🇨🇦 USA/Canada (+1)'),
    ('+44', '🇬🇧 UK (+44)'),
    ('+61', '🇦🇺 Australia (+61)'),
    ('+971', '🇦🇪 UAE (+971)'),
    ('+65', '🇸🇬 Singapore (+65)'),
    ('+49', '🇩🇪 Germany (+49)'),
]


class JobSeekerSignUpForm(forms.ModelForm):
    """Registration form for Job Seekers."""
    username = forms.CharField(
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Choose a username"})
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={"class": "form-control", "placeholder": "name@example.com"})
    )
    country_code = forms.ChoiceField(
        choices=COUNTRY_CODE_CHOICES,
        initial='+91',
        required=False,
        widget=forms.Select(attrs={"class": "form-select"})
    )
    phone = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "10-digit mobile number", "maxlength": "10"})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "At least 6 letters/numbers/symbols", "id": "jobseeker_password"})
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Confirm password", "id": "jobseeker_confirm_password"})
    )

    class Meta:
        model = User
        fields = ["username", "email", "password"]

    def clean_username(self):
        raw_username = self.cleaned_data.get("username", "").strip()
        username = raw_username.replace(" ", "_")
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("This username is already taken. Please choose another.")
        return username

    def clean_phone(self):
        phone = self.cleaned_data.get("phone", "").strip()
        if phone:
            digits = ''.join(filter(str.isdigit, phone))
            if len(digits) != 10:
                raise forms.ValidationError("Phone number must contain exactly 10 digits (e.g. 9876543210).")
            return digits
        return phone

    def clean_password(self):
        password = self.cleaned_data.get("password")
        if password and len(password) < 6:
            raise forms.ValidationError("Password must be at least 6 characters long (letters, numbers, or symbols).")
        return password

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")
        if password and confirm_password and password != confirm_password:
            self.add_error("confirm_password", "Passwords do not match.")
        return cleaned_data


class RecruiterSignUpForm(forms.ModelForm):
    """Registration form for Recruiters/Employers."""
    username = forms.CharField(
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Choose a username (e.g. Rahul_Menon)"})
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={"class": "form-control", "placeholder": "recruiter@company.com"})
    )
    country_code = forms.ChoiceField(
        choices=COUNTRY_CODE_CHOICES,
        initial='+91',
        required=False,
        widget=forms.Select(attrs={"class": "form-select"})
    )
    phone = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "10-digit mobile number", "maxlength": "10"})
    )
    company_name = forms.CharField(
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Company Name (e.g., TechVision Solutions)"})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "At least 6 letters/numbers/symbols", "id": "recruiter_password"})
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Confirm password", "id": "recruiter_confirm_password"})
    )

    class Meta:
        model = User
        fields = ["username", "email", "password"]

    def clean_username(self):
        raw_username = self.cleaned_data.get("username", "").strip()
        username = raw_username.replace(" ", "_")
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("This username is already taken. Please choose another.")
        return username

    def clean_phone(self):
        phone = self.cleaned_data.get("phone", "").strip()
        if phone:
            digits = ''.join(filter(str.isdigit, phone))
            if len(digits) != 10:
                raise forms.ValidationError("Phone number must contain exactly 10 digits (e.g. 9876543210).")
            return digits
        return phone

    def clean_password(self):
        password = self.cleaned_data.get("password")
        if password and len(password) < 6:
            raise forms.ValidationError("Password must be at least 6 characters long (letters, numbers, or symbols).")
        return password

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")
        if password and confirm_password and password != confirm_password:
            self.add_error("confirm_password", "Passwords do not match.")
        return cleaned_data


class CompanyForm(forms.ModelForm):
    """Form used to create or edit a Company profile."""
    class Meta:
        model = Company
        fields = [
            "name",
            "logo",
            "email",
            "website",
            "location",
            "description",
        ]
        widgets = {
            "name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "e.g. TechVision Solutions"}
            ),
            "logo": forms.ClearableFileInput(
                attrs={"class": "form-control", "accept": "image/*"}
            ),
            "email": forms.EmailInput(
                attrs={"class": "form-control", "placeholder": "recruitment@techvision.com"}
            ),
            "website": forms.URLInput(
                attrs={"class": "form-control", "placeholder": "https://techvision.com"}
            ),
            "location": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "e.g. San Francisco, CA"}
            ),
            "description": forms.Textarea(
                attrs={"class": "form-control", "rows": 4, "placeholder": "Company background and culture..."}
            ),
        }
        labels = {
            "name": "Company Name",
            "logo": "Company Logo (Image)",
            "email": "Contact Email",
            "website": "Website URL",
            "location": "Headquarters / Location",
            "description": "Company Description",
        }

    def clean_name(self):
        name = self.cleaned_data.get("name", "").strip()
        if not name:
            raise forms.ValidationError("Company name cannot be empty.")
        return name


class ResumeUploadForm(forms.ModelForm):
    """Form used on the 'Upload Resume' page."""
    class Meta:
        model = Resume
        fields = ["uploaded_resume"]
        widgets = {
            "uploaded_resume": forms.ClearableFileInput(
                attrs={
                    "class": "form-control",
                    "accept": ".pdf,.docx",
                }
            ),
        }
        labels = {
            "uploaded_resume": "Select your resume (PDF or DOCX)",
        }

    def clean_uploaded_resume(self):
        uploaded_file = self.cleaned_data.get("uploaded_resume")

        if not uploaded_file:
            raise forms.ValidationError("Please select a resume file to upload.")

        file_extension = os.path.splitext(uploaded_file.name)[1].lower().lstrip(".")
        allowed_extensions = getattr(settings, "ALLOWED_RESUME_EXTENSIONS", ["pdf", "docx"])
        if file_extension not in allowed_extensions:
            raise forms.ValidationError(
                f"Unsupported file type '.{file_extension}'. "
                f"Allowed types are: {', '.join(allowed_extensions).upper()}."
            )

        max_size_mb = getattr(settings, "MAX_RESUME_UPLOAD_SIZE_MB", 5)
        max_size_bytes = max_size_mb * 1024 * 1024
        if uploaded_file.size > max_size_bytes:
            raise forms.ValidationError(
                f"File is too large ({uploaded_file.size / (1024 * 1024):.2f} MB). "
                f"Maximum allowed size is {max_size_mb} MB."
            )

        return uploaded_file


class JobForm(forms.ModelForm):
    """Form used on 'Add Job' / 'Edit Job' pages."""
    company = forms.ModelChoiceField(
        queryset=Company.objects.all(),
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
        label="Company"
    )
    company_name = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Acme Corporation"}),
        label="Company Name"
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in ["category", "job_type", "location", "salary", "vacancies", "deadline"]:
            if field_name in self.fields:
                self.fields[field_name].required = False

    class Meta:
        model = Job
        fields = [
            "job_title",
            "company",
            "category",
            "job_type",
            "location",
            "salary",
            "vacancies",
            "deadline",
            "job_description",
            "required_skills",
            "required_experience",
        ]
        widgets = {
            "job_title": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "e.g. Backend Engineer"}
            ),
            "company": forms.Select(
                attrs={"class": "form-select"}
            ),
            "category": forms.Select(
                attrs={"class": "form-select"}
            ),
            "job_type": forms.Select(
                attrs={"class": "form-select"}
            ),
            "location": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "e.g. San Francisco, CA or Remote"}
            ),
            "salary": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "e.g. $80,000 - $100,000 / year or Competitive"}
            ),
            "vacancies": forms.NumberInput(
                attrs={"class": "form-control", "min": 1}
            ),
            "deadline": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "job_description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 6,
                    "placeholder": "Paste full job description here...",
                }
            ),
            "required_skills": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 2,
                    "placeholder": "e.g. Python, Django, SQL, REST APIs",
                }
            ),
            "required_experience": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "e.g. 2-4 years"}
            ),
        }

    def clean_job_title(self):
        job_title = self.cleaned_data.get("job_title", "").strip()
        if not job_title:
            raise forms.ValidationError("Job title cannot be empty.")
        return job_title

    def clean_job_description(self):
        job_description = self.cleaned_data.get("job_description", "").strip()
        if len(job_description) < 20:
            raise forms.ValidationError(
                "Job description is too short. Please provide more detail "
                "so the matching engine can compare it accurately."
            )
        return job_description

    def save(self, commit=True):
        instance = super().save(commit=False)
        comp_name = self.cleaned_data.get("company_name")
        if comp_name and not instance.company:
            instance.company_name_legacy = comp_name
        if commit:
            instance.save()
        return instance


class AdminLoginForm(AuthenticationForm):
    """Styled login form."""
    username = forms.CharField(
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Enter username", "autofocus": True}
        )
    )
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "placeholder": "Enter password"}
        )
    )


class JobApplicationStatusForm(forms.ModelForm):
    """Form used by recruiters to update candidate application status."""
    class Meta:
        model = JobApplication
        fields = ["status"]
        widgets = {
            "status": forms.Select(attrs={"class": "form-select form-select-sm"}),
        }


class UserProfileEditForm(forms.Form):
    """Form to edit profile details (username, email, phone, company name, profile picture)."""
    username = forms.CharField(
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Username"})
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={"class": "form-control", "placeholder": "Email Address"})
    )
    country_code = forms.ChoiceField(
        choices=COUNTRY_CODE_CHOICES,
        initial='+91',
        required=False,
        widget=forms.Select(attrs={"class": "form-select"})
    )
    phone = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "10-digit mobile number", "maxlength": "10"})
    )
    company_name = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Company Name (Recruiters)"})
    )
    profile_picture = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={"class": "form-control", "accept": ".jpg,.jpeg,.png,.webp,.gif"})
    )

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_username(self):
        raw_username = self.cleaned_data.get("username", "").strip()
        username = raw_username.replace(" ", "_")
        if not username:
            raise forms.ValidationError("Username cannot be blank.")
        if self.user and User.objects.filter(username__iexact=username).exclude(pk=self.user.pk).exists():
            raise forms.ValidationError("This username is already taken. Please choose another.")
        return username

    def clean_phone(self):
        phone = self.cleaned_data.get("phone", "").strip()
        if phone:
            digits = ''.join(filter(str.isdigit, phone))
            if len(digits) != 10:
                raise forms.ValidationError("Phone number must contain exactly 10 digits (e.g. 9876543210).")
            return digits
        return phone

    def clean_profile_picture(self):
        picture = self.cleaned_data.get('profile_picture')
        if picture:
            ext = os.path.splitext(picture.name)[1].lower().lstrip('.')
            allowed = ['jpg', 'jpeg', 'png', 'webp', 'gif', 'bmp']
            if ext not in allowed:
                raise forms.ValidationError(
                    f"Invalid image format '.{ext}'. Allowed photo formats are: JPG, JPEG, PNG, WEBP."
                )
            if picture.size > 5 * 1024 * 1024:
                raise forms.ValidationError("Profile picture file size must be under 5MB.")
        return picture


class CustomPasswordChangeForm(PasswordChangeForm):
    """Styled PasswordChangeForm."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})

    def clean_new_password1(self):
        password = self.cleaned_data.get("new_password1")
        if password and len(password) < 6:
            raise forms.ValidationError("Password must be at least 6 characters long (letters, numbers, or symbols).")
        return password


class ForgotPasswordForm(forms.Form):
    """Form for resetting password by username, registered email, and new password."""
    username = forms.CharField(
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Enter your registered username"})
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={"class": "form-control", "placeholder": "Enter your registered email address"})
    )
    new_password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "At least 6 letters/numbers/symbols", "id": "forgot_new_password"})
    )
    confirm_new_password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Confirm new password", "id": "forgot_confirm_password"})
    )

    def clean_new_password(self):
        password = self.cleaned_data.get("new_password")
        if password and len(password) < 6:
            raise forms.ValidationError("Password must be at least 6 characters long (letters, numbers, or symbols).")
        return password

    def clean(self):
        cleaned_data = super().clean()
        pass1 = cleaned_data.get("new_password")
        pass2 = cleaned_data.get("confirm_new_password")
        if pass1 and pass2 and pass1 != pass2:
            self.add_error("confirm_new_password", "New passwords do not match.")
        return cleaned_data


class SendMessageForm(forms.ModelForm):
    """Form for sending internal messages between candidates and recruiters."""
    class Meta:
        model = Message
        fields = ["subject", "body"]
        widgets = {
            "subject": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Subject (e.g., Application Update / Interview Invitation)"}
            ),
            "body": forms.Textarea(
                attrs={"class": "form-control", "rows": 4, "placeholder": "Type your message here..."}
            ),
        }


class InterviewScheduleForm(forms.ModelForm):
    """Form for recruiters to propose 3 interview time slots for AI screening."""
    slot_1 = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={"type": "datetime-local", "class": "form-control"})
    )
    slot_2 = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={"type": "datetime-local", "class": "form-control"})
    )
    slot_3 = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={"type": "datetime-local", "class": "form-control"})
    )

    class Meta:
        model = InterviewSession
        fields = ["slot_1", "slot_2", "slot_3"]