"""
URL configuration for matching_app application.

Routes:
    - Home & Navigation
    - Authentication (login, logout, jobseeker_signup, recruiter_signup, forgot_password, change_password)
    - User Profile & Contact Info Editing (profile)
    - Role-Based Dashboards & Recruiter Approval (jobseeker_dashboard, recruiter_dashboard, admin dashboard, approve_recruiter)
    - Company Management (list, add, detail, edit, delete)
    - Resume Upload & Parsing (upload, list, detail, delete)
    - Job Openings & Applications (list, add, detail, edit, delete, apply)
    - ATS Candidate Status Updates & Match PDF Report Export
    - Internal Messaging System (inbox, conversation_detail, send_message)
    - AI Screening Interview, Proctoring & Re-Attempt Workflow (invite_to_interview, interview_room, submit_interview_answer, record_tab_switch, interview_transcript, request_interview_reattempt, decide_interview_reattempt)
"""

from django.urls import path
from . import views

app_name = 'matching_app'

urlpatterns = [
    # --- Home ---
    path('', views.home, name='home'),

    # --- Authentication & Signups ---
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('forgot-password/', views.forgot_password, name='forgot_password'),
    path('password-change/', views.change_password, name='change_password'),
    path('signup/jobseeker/', views.jobseeker_signup, name='jobseeker_signup'),
    path('signup/recruiter/', views.recruiter_signup, name='recruiter_signup'),

    # --- User Profile ---
    path('profile/', views.user_profile, name='user_profile'),
    path('profile/delete/', views.delete_account, name='delete_account'),

    # --- Dashboards & Recruiter Approval ---
    path('dashboard/', views.dashboard, name='dashboard'),
    path('dashboard/jobseeker/', views.jobseeker_dashboard, name='jobseeker_dashboard'),
    path('dashboard/recruiter/', views.recruiter_dashboard, name='recruiter_dashboard'),
    path('recruiters/<int:pk>/approve/', views.approve_recruiter, name='approve_recruiter'),
    path('recruiters/<int:pk>/decline/', views.decline_recruiter, name='decline_recruiter'),

    # --- Company Management ---
    path('companies/', views.company_list, name='company_list'),
    path('companies/add/', views.company_create, name='company_create'),
    path('companies/<int:pk>/', views.company_detail, name='company_detail'),
    path('companies/<int:pk>/edit/', views.company_edit, name='company_edit'),
    path('companies/<int:pk>/delete/', views.company_delete, name='company_delete'),

    # --- Resume Upload & Management ---
    path('upload/', views.upload_resume, name='upload_resume'),
    path('resumes/', views.resume_list, name='resume_list'),
    path('resumes/<int:pk>/', views.resume_detail, name='resume_detail'),
    path('resumes/<int:pk>/delete/', views.resume_delete, name='resume_delete'),

    # --- Job Management & ATS Applications ---
    path('jobs/', views.job_list, name='job_list'),
    path('jobs/add/', views.job_create, name='job_create'),
    path('jobs/<int:pk>/', views.job_detail, name='job_detail'),
    path('jobs/<int:pk>/edit/', views.job_edit, name='job_edit'),
    path('jobs/<int:pk>/delete/', views.job_delete, name='job_delete'),
    path('jobs/<int:pk>/apply/', views.apply_for_job, name='apply_for_job'),
    path('applications/<int:pk>/status/', views.update_application_status, name='update_application_status'),

    # --- Matching, Recommendations & PDF Export ---
    path('resumes/<int:pk>/match/', views.match_results, name='match_results'),
    path('resumes/<int:pk>/recommendations/', views.recommendations, name='recommendations'),
    path('resumes/<int:pk>/match/pdf/', views.download_match_pdf, name='download_match_pdf'),

    # --- Internal Messaging System & Safety Reporting ---
    path('messages/', views.inbox, name='inbox'),
    path('messages/<int:user_id>/', views.conversation_detail, name='conversation_detail'),
    path('messages/send/<int:recipient_id>/', views.send_message, name='send_message'),
    path('messages/<int:pk>/delete/', views.delete_message, name='delete_message'),
    path('messages/conversation/<int:user_id>/delete/', views.delete_conversation, name='delete_conversation'),
    path('users/<int:user_id>/report/', views.submit_user_report, name='submit_user_report'),
    path('reports/<int:report_id>/resolve/', views.resolve_user_report, name='resolve_user_report'),

    # --- AI Screening Interview & Re-Attempt Workflow ---
    path('applications/<int:app_id>/invite-interview/', views.invite_to_interview, name='invite_to_interview'),
    path('interview/<int:session_id>/select-slot/<int:slot_num>/', views.select_interview_slot, name='select_interview_slot'),
    path('interview/<int:session_id>/', views.interview_room, name='interview_room'),
    path('interview/<int:session_id>/answer/', views.submit_interview_answer, name='submit_interview_answer'),
    path('interview/<int:session_id>/tab-switch/', views.record_tab_switch, name='record_tab_switch'),
    path('interview/<int:session_id>/expire/', views.expire_interview_session, name='expire_interview_session'),
    path('interview/<int:session_id>/transcript/', views.interview_transcript, name='interview_transcript'),
    path('interview/<int:session_id>/request-reattempt/', views.request_interview_reattempt, name='request_interview_reattempt'),
    path('interview/<int:session_id>/decide-reattempt/', views.decide_interview_reattempt, name='decide_interview_reattempt'),
]