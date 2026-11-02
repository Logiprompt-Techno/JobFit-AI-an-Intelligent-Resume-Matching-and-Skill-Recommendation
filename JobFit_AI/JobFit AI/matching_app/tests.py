"""
Integration and Unit Test Suite for matching_app application.

Tests included:
    1. Model Creation & Properties Tests
    2. NLP Extraction & Hybrid Match Calculation Core Logic Tests
    3. Resume Quality Score Evaluator Tests
    4. HTTP Response Codes, Landing Page, & Access Control Integration Tests
    5. Recruiter Registration & Admin Approval Workflow Tests
    6. AI Screening Interview Chatbot, Proctoring & Re-Attempt Workflow Tests
"""

from datetime import timedelta
from django.utils import timezone
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from matching_app.models import (
    Resume, Job, MatchResult, Company, UserProfile, JobApplication, Message,
    InterviewSession, InterviewQA
)
from matching_app.services.matcher import calculate_match
from matching_app.services.skill_recommender import recommend_skills_for_gap
from matching_app.services.resume_scorer import calculate_resume_score
from matching_app.services.interview_ai import generate_interview_questions, evaluate_interview_answers


class ModelTests(TestCase):
    """Test model creation, custom methods, string representations, and properties."""

    def test_company_model(self):
        comp = Company.objects.create(
            name="TechCorp",
            website="https://techcorp.com",
            location="San Francisco, CA"
        )
        self.assertEqual(str(comp), "TechCorp")

    def test_job_model(self):
        comp = Company.objects.create(name="CyberInc")
        job = Job.objects.create(
            job_title="Python Developer",
            company=comp,
            job_description="Develop backend microservices.",
            required_skills="Python, Django"
        )
        self.assertEqual(job.company_name, "CyberInc")
        self.assertIn("Python Developer at CyberInc", str(job))

    def test_resume_model(self):
        resume = Resume.objects.create(
            candidate_name="John Doe",
            email="john@example.com",
            extracted_skills="Python, Django, SQL"
        )
        self.assertEqual(str(resume), "John Doe")

    def test_match_result_model(self):
        resume = Resume.objects.create(candidate_name="Jane Smith")
        job = Job.objects.create(job_title="Python Developer", company_name_legacy="TechInc")
        match = MatchResult.objects.create(resume=resume, job=job, match_percentage=85.5)
        self.assertEqual(match.match_percentage, 85.5)
        self.assertIn("85.5%", str(match))

    def test_user_profile_and_job_application_models(self):
        user = User.objects.create_user(username="candidate1", password="password123")
        profile = UserProfile.objects.create(user=user, role='JOB_SEEKER', is_approved=True)
        self.assertEqual(profile.role, 'JOB_SEEKER')
        self.assertTrue(profile.is_approved)

        resume = Resume.objects.create(user=user, candidate_name="Candidate 1")
        job = Job.objects.create(job_title="Test Job", company_name_legacy="Test Co")
        app = JobApplication.objects.create(resume=resume, job=job, status='Applied')
        self.assertEqual(app.status, 'Applied')


class MatchingLogicTests(TestCase):
    """Test NLP matching calculation algorithms and skill recommendations."""

    def setUp(self):
        self.job = Job.objects.create(
            job_title="Senior Python Backend Developer",
            job_description="Seeking a Senior Python Backend Developer with experience in Django, PostgreSQL, Docker, AWS, and REST APIs.",
            required_skills="Python, Django, PostgreSQL, Docker, AWS, REST API"
        )

    def test_high_skill_match(self):
        high_match_resume = Resume.objects.create(
            candidate_name="Alice Developer",
            extracted_text="Alice is a Senior Python Developer skilled in Django, PostgreSQL, Docker, and AWS.",
            extracted_skills="Python, Django, PostgreSQL, Docker, AWS"
        )
        result = calculate_match(high_match_resume, self.job)
        self.assertGreater(result['match_percentage'], 70.0)
        self.assertIn('REST API', result['missing_skills'])

    def test_low_skill_match(self):
        low_match_resume = Resume.objects.create(
            candidate_name="Bob Designer",
            extracted_text="Bob is a UI/UX designer specializing in Figma, Adobe XD, HTML, CSS.",
            extracted_skills="Figma, Adobe XD, HTML, CSS"
        )
        result = calculate_match(low_match_resume, self.job)
        self.assertLess(result['match_percentage'], 40.0)


class ResumeScorerTests(TestCase):
    """Test Resume Score evaluator algorithm and suggestion generation."""

    def test_calculate_resume_score(self):
        full_resume = Resume(
            candidate_name="John Doe",
            email="john@example.com",
            phone="+1 234 567 8900",
            extracted_skills="Python, Django, PostgreSQL, Docker, AWS, REST API, Git, Linux, Kubernetes, React, JavaScript, HTML, CSS, Redis, Celery",
            education="Bachelor of Science in Computer Science, Stanford University. Graduated with Honors and Magna Cum Laude distinctions.",
            experience="Senior Backend Engineer at Tech Corp (4 years). Designed and built scalable Django APIs, microservices, Docker containers, and AWS cloud infrastructure."
        )
        full_score_data = calculate_resume_score(full_resume)
        self.assertGreaterEqual(full_score_data['score'], 88)
        self.assertEqual(full_score_data['grade'], "Excellent")

        partial_resume = Resume(
            candidate_name="Jane Doe",
            email="jane@example.com",
            phone="1234567890",
            extracted_skills="Python, Django, SQL",
            education="B.S. Computer Science",
            experience="Intern Developer"
        )
        partial_score_data = calculate_resume_score(partial_resume)
        self.assertLess(partial_score_data['score'], 80)
        self.assertTrue(len(partial_score_data['suggestions']) > 0)

    def test_recommend_skills_for_gap(self):
        missing_skills = ['AWS', 'Docker']
        recommendations = recommend_skills_for_gap(missing_skills)
        self.assertTrue(len(recommendations) > 0)


class ViewIntegrationTests(TestCase):
    """Test HTTP response codes, landing page, and login access controls."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", password="password123")
        UserProfile.objects.create(user=self.user, role='JOB_SEEKER', is_approved=True)

        self.job = Job.objects.create(
            job_title="Backend Developer",
            company_name_legacy="Innovate Ltd",
            job_description="Build web APIs using Django framework and PostgreSQL database.",
            required_skills="Python, Django, PostgreSQL",
            required_experience="2 years"
        )
        self.resume = Resume.objects.create(
            user=self.user,
            candidate_name="Alice Smith",
            email="alice@example.com",
            extracted_text="Alice Smith. Python Developer proficient in Django and PostgreSQL.",
            extracted_skills="Python, Django, PostgreSQL"
        )

    def test_home_view_unauthenticated(self):
        response = self.client.get(reverse('matching_app:home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "JobFit AI")

    def test_protected_views_redirect_when_logged_out(self):
        upload_url = reverse('matching_app:upload_resume')
        response = self.client.get(upload_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('matching_app:login'), response.url)

    def test_protected_views_accessible_when_logged_in(self):
        self.client.login(username="testuser", password="password123")
        upload_url = reverse('matching_app:upload_resume')
        response = self.client.get(upload_url)
        self.assertEqual(response.status_code, 200)

    def test_job_list_and_detail_public_access(self):
        list_response = self.client.get(reverse('matching_app:job_list'))
        self.assertEqual(list_response.status_code, 200)

        detail_response = self.client.get(reverse('matching_app:job_detail', args=[self.job.pk]))
        self.assertEqual(detail_response.status_code, 200)


class RecruiterApprovalWorkflowTests(TestCase):
    """Test Recruiter registration approval workflow."""

    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_superuser(username="adminuser", password="adminpassword123")

    def test_recruiter_signup_requires_admin_approval(self):
        response = self.client.post(reverse('matching_app:recruiter_signup'), {
            'username': 'newrecruiter',
            'email': 'recruiter@company.com',
            'password': 'Password123!',
            'confirm_password': 'Password123!',
            'company_name': 'Acme Corp',
            'phone': '1234567890'
        })
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('matching_app:login'), response.url)

        recruiter_user = User.objects.get(username='newrecruiter')
        profile = recruiter_user.profile
        self.assertEqual(profile.role, 'RECRUITER')
        self.assertFalse(profile.is_approved)

        # Attempt to log in unapproved recruiter
        login_response = self.client.post(reverse('matching_app:login'), {
            'username': 'newrecruiter',
            'password': 'Password123!'
        })
        self.assertEqual(login_response.status_code, 302)
        self.assertIn(reverse('matching_app:login'), login_response.url)

    def test_admin_can_approve_recruiter(self):
        recruiter_user = User.objects.create_user(username="pendingrecruiter", password="password123")
        profile = UserProfile.objects.create(user=recruiter_user, role='RECRUITER', is_approved=False, company_name="Pending Inc")

        self.client.login(username="adminuser", password="adminpassword123")
        approve_url = reverse('matching_app:approve_recruiter', args=[profile.pk])
        response = self.client.get(approve_url)
        self.assertEqual(response.status_code, 302)

        profile.refresh_from_db()
        self.assertTrue(profile.is_approved)


class InterviewChatbotAndProctoringTests(TestCase):
    """Test AI Screening Interview session creation, question generation, proctoring violations, and re-attempt requests."""

    def setUp(self):
        self.client = Client()
        self.recruiter = User.objects.create_user(username="recruiter1", password="password123")
        UserProfile.objects.create(user=self.recruiter, role='RECRUITER', is_approved=True)

        self.candidate = User.objects.create_user(username="candidate1", password="password123")
        UserProfile.objects.create(user=self.candidate, role='JOB_SEEKER', is_approved=True)

        self.job = Job.objects.create(
            job_title="Python Backend Engineer",
            posted_by=self.recruiter,
            required_skills="Python, Django, PostgreSQL, Docker",
            job_description="Develop backend APIs using Python and Django."
        )
        self.resume = Resume.objects.create(user=self.candidate, candidate_name="Candidate 1")
        self.application = JobApplication.objects.create(resume=self.resume, job=self.job, status='Applied')

    def test_invite_to_interview(self):
        self.client.login(username="recruiter1", password="password123")
        invite_url = reverse('matching_app:invite_to_interview', args=[self.application.pk])
        response_get = self.client.get(invite_url)
        self.assertEqual(response_get.status_code, 200)

        now = timezone.now()
        post_data = {
            'slot_1': (now + timedelta(hours=2)).strftime('%Y-%m-%dT%H:%M'),
            'slot_2': (now + timedelta(days=1)).strftime('%Y-%m-%dT%H:%M'),
            'slot_3': (now + timedelta(days=2)).strftime('%Y-%m-%dT%H:%M'),
        }
        response = self.client.post(invite_url, post_data)
        self.assertEqual(response.status_code, 302)

        session = InterviewSession.objects.get(application=self.application)
        self.assertEqual(session.candidate, self.candidate)
        self.assertIsNotNone(session.slot_1)
        self.assertEqual(session.questions.count(), 4)

    def test_scheduled_interview_timing_gate(self):
        now = timezone.now()
        future_slot = now + timedelta(hours=2)
        session = InterviewSession.objects.create(
            application=self.application,
            candidate=self.candidate,
            job=self.job,
            slot_1=future_slot,
            chosen_slot=future_slot,
            status='Pending'
        )

        self.assertFalse(session.is_room_open)

        # Candidate attempts to enter room 2 hours early -> blocked & redirected
        self.client.login(username="candidate1", password="password123")
        room_url = reverse('matching_app:interview_room', args=[session.pk])
        response = self.client.get(room_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('matching_app:jobseeker_dashboard'), response.url)

        # Simulate arrival at scheduled time window (10 minutes before slot)
        session.chosen_slot = timezone.now() + timedelta(minutes=10)
        session.save()
        self.assertTrue(session.is_room_open)

        open_response = self.client.get(room_url)
        self.assertEqual(open_response.status_code, 200)

    def test_tab_switch_proctoring_violation(self):
        session = InterviewSession.objects.create(
            application=self.application,
            candidate=self.candidate,
            job=self.job,
            status='In Progress'
        )

        self.client.login(username="candidate1", password="password123")
        tab_switch_url = reverse('matching_app:record_tab_switch', args=[session.pk])

        for count in range(1, 4):
            res = self.client.post(tab_switch_url)
            self.assertEqual(res.json()['tab_switch_count'], count)
            self.assertFalse(res.json()['terminated'])

        # 4th violation exceeds 3 allowed -> should auto-terminate
        final_res = self.client.post(tab_switch_url)
        self.assertTrue(final_res.json()['terminated'])

        session.refresh_from_db()
        self.assertEqual(session.status, 'Terminated (Tab Switch Violation)')

    def test_interview_transcript_evaluation(self):
        session = InterviewSession.objects.create(
            application=self.application,
            candidate=self.candidate,
            job=self.job,
            status='In Progress'
        )
        q1 = InterviewQA.objects.create(
            session=session,
            question_number=1,
            question_text="Describe Python experience.",
            candidate_answer="I have 3 years of hands-on experience building web services using Python, Django, and PostgreSQL."
        )

        evaluate_interview_answers(session)
        session.refresh_from_db()

        self.assertEqual(session.status, 'In Progress')
        q1.refresh_from_db()
        self.assertGreater(q1.score, 50.0)

        # Test Recruiter Transcript Access
        self.client.login(username="recruiter1", password="password123")
        transcript_url = reverse('matching_app:interview_transcript', args=[session.pk])
        res = self.client.get(transcript_url)
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Describe Python experience.")

    def test_reattempt_request_and_approval_workflow(self):
        session = InterviewSession.objects.create(
            application=self.application,
            candidate=self.candidate,
            job=self.job,
            status='Terminated (Tab Switch Violation)',
            tab_switch_count=4
        )

        # Candidate submits re-attempt request
        self.client.login(username="candidate1", password="password123")
        req_url = reverse('matching_app:request_interview_reattempt', args=[session.pk])
        res = self.client.post(req_url, {'reason': 'Network drop occurred during Q2'})
        self.assertEqual(res.status_code, 302)

        session.refresh_from_db()
        self.assertTrue(session.is_reattempt_requested)
        self.assertEqual(session.reattempt_status, 'Requested')
        self.assertIn('Network drop', session.reattempt_reason)

        # Recruiter approves re-attempt request
        self.client.login(username="recruiter1", password="password123")
        decide_url = reverse('matching_app:decide_interview_reattempt', args=[session.pk])
        decide_res = self.client.post(decide_url, {'decision': 'approve'})
        self.assertEqual(decide_res.status_code, 302)

        session.refresh_from_db()
        self.assertEqual(session.status, 'Pending')
        self.assertEqual(session.tab_switch_count, 0)
        self.assertEqual(session.reattempt_status, 'Approved')

    def test_user_profile_picture_upload(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        self.client.login(username="candidate1", password="password123")
        profile_url = reverse('matching_app:user_profile')

        # Create a small valid 1x1 GIF image
        gif_data = b'GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;'
        image_file = SimpleUploadedFile("avatar.jpg", gif_data, content_type="image/jpeg")

        response = self.client.post(profile_url, {
            'username': 'candidate1',
            'email': 'candidate1_updated@example.com',
            'phone': '1234567890',
            'profile_picture': image_file
        }, follow=True)

        self.assertEqual(response.status_code, 200)
        profile = UserProfile.objects.get(user__username="candidate1")
        self.assertTrue(profile.profile_picture)
        self.assertIn("avatar", profile.profile_picture.name)

    def test_user_can_edit_username(self):
        self.client.login(username="candidate1", password="password123")
        profile_url = reverse('matching_app:user_profile')

        response = self.client.post(profile_url, {
            'username': 'candidate1_renamed',
            'email': 'candidate1@example.com',
            'phone': '1234567890'
        }, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(User.objects.filter(username='candidate1_renamed').exists())

    def test_delete_account_workflow(self):
        user_to_delete = User.objects.create_user(username="delete_me", password="password123")
        UserProfile.objects.create(user=user_to_delete, role='JOB_SEEKER')
        self.client.login(username="delete_me", password="password123")

        delete_url = reverse('matching_app:delete_account')
        response = self.client.post(delete_url)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(User.objects.filter(username="delete_me").exists())

    def test_forgot_password_security(self):
        # 1. Superuser cannot be reset via web form
        admin_user = User.objects.create_superuser(username="admin_sec", email="admin_sec@example.com", password="password123")
        forgot_url = reverse('matching_app:forgot_password')
        res1 = self.client.post(forgot_url, {
            'username': 'admin_sec',
            'email': 'admin_sec@example.com',
            'new_password': 'newpassword123',
            'confirm_new_password': 'newpassword123'
        })
        self.assertEqual(res1.status_code, 200)
        admin_user.refresh_from_db()
        self.assertTrue(admin_user.check_password('password123'))

        # 2. Candidate password reset requires matching email
        cand = User.objects.create_user(username="cand_sec", email="cand_sec@example.com", password="password123")
        res2 = self.client.post(forgot_url, {
            'username': 'cand_sec',
            'email': 'wrong_email@example.com',
            'new_password': 'newpassword123',
            'confirm_new_password': 'newpassword123'
        })
        self.assertEqual(res2.status_code, 200)
        cand.refresh_from_db()
        self.assertTrue(cand.check_password('password123'))

    def test_unread_messages_navbar_badge(self):
        sender = User.objects.create_user(username="sender_u", password="password123")
        recipient = User.objects.create_user(username="recipient_u", password="password123")
        Message.objects.create(sender=sender, recipient=recipient, subject="Test", body="Hello")

        self.client.login(username="recipient_u", password="password123")
        response = self.client.get(reverse('matching_app:home'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['unread_messages_count'], 1)
        self.assertContains(response, '<span class="badge bg-danger rounded-pill ms-1"')

    def test_decline_recruiter_registration(self):
        admin = User.objects.create_superuser(username="admin_user", password="adminpassword")
        unapproved_user = User.objects.create_user(username="pending_recruiter", password="password123")
        unapproved_profile = UserProfile.objects.create(user=unapproved_user, role='RECRUITER', is_approved=False)

        self.client.login(username="admin_user", password="adminpassword")
        decline_url = reverse('matching_app:decline_recruiter', args=[unapproved_profile.pk])
        res = self.client.get(decline_url)
        self.assertEqual(res.status_code, 302)
        self.assertFalse(User.objects.filter(username="pending_recruiter").exists())

    def test_safety_report_submission_and_admin_ban_action(self):
        from matching_app.models import UserReport
        candidate = User.objects.create_user(username="reporter_cand", password="password123")
        scammer = User.objects.create_user(username="scammer_rec", password="password123")
        admin = User.objects.create_superuser(username="safety_admin", password="adminpassword")

        # 1. Submit safety report
        self.client.login(username="reporter_cand", password="password123")
        report_url = reverse('matching_app:submit_user_report', args=[scammer.pk])
        rep_res = self.client.post(report_url, {
            'reason': 'SCAM',
            'description': 'Requested payment before interview.'
        })
        self.assertEqual(rep_res.status_code, 302)

        report = UserReport.objects.filter(reporter=candidate, reported_user=scammer).first()
        self.assertIsNotNone(report)
        self.assertEqual(report.reason, 'SCAM')
        self.assertEqual(report.status, 'Pending')

        # 2. Admin bans reported user
        self.client.login(username="safety_admin", password="adminpassword")
        resolve_url = reverse('matching_app:resolve_user_report', args=[report.pk])
        ban_res = self.client.post(resolve_url, {'action': 'ban'})
        self.assertEqual(ban_res.status_code, 302)

        scammer.refresh_from_db()
        report.refresh_from_db()
        self.assertFalse(scammer.is_active)
        self.assertEqual(report.status, 'Resolved')


class MessageDeletionTests(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(username='user1', email='user1@example.com', password='password123')
        self.user2 = User.objects.create_user(username='user2', email='user2@example.com', password='password123')
        self.user3 = User.objects.create_user(username='user3', email='user3@example.com', password='password123')
        UserProfile.objects.create(user=self.user1, role='JOB_SEEKER')
        UserProfile.objects.create(user=self.user2, role='RECRUITER')
        UserProfile.objects.create(user=self.user3, role='JOB_SEEKER')

        self.msg1 = Message.objects.create(
            sender=self.user1,
            recipient=self.user2,
            subject='Hello Recruiter',
            body='Are you hiring?'
        )
        self.msg2 = Message.objects.create(
            sender=self.user2,
            recipient=self.user1,
            subject='Re: Hello Recruiter',
            body='Yes we are!'
        )

    def test_delete_individual_message(self):
        self.client.login(username='user1', password='password123')
        delete_url = reverse('matching_app:delete_message', kwargs={'pk': self.msg1.pk})
        response = self.client.post(delete_url)
        self.assertEqual(response.status_code, 302)

        self.msg1.refresh_from_db()
        self.assertTrue(self.msg1.deleted_by_sender)
        self.assertFalse(self.msg1.deleted_by_recipient)

        # Check conversation view for user1 does not include msg1
        conv_url = reverse('matching_app:conversation_detail', kwargs={'user_id': self.user2.id})
        res = self.client.get(conv_url)
        self.assertNotIn('Are you hiring?', res.content.decode())
        self.assertIn('Yes we are!', res.content.decode())

    def test_clear_entire_conversation_thread(self):
        self.client.login(username='user1', password='password123')
        delete_conv_url = reverse('matching_app:delete_conversation', kwargs={'user_id': self.user2.id})
        response = self.client.post(delete_conv_url)
        self.assertEqual(response.status_code, 302)

        self.msg1.refresh_from_db()
        self.msg2.refresh_from_db()
        self.assertTrue(self.msg1.deleted_by_sender)
        self.assertTrue(self.msg2.deleted_by_recipient)

        # Inbox for user1 should now have 0 conversations
        inbox_url = reverse('matching_app:inbox')
        res = self.client.get(inbox_url)
        self.assertIn('No Messages Yet', res.content.decode())

    def test_unauthorized_user_cannot_delete_message(self):
        self.client.login(username='user3', password='password123')
        delete_url = reverse('matching_app:delete_message', kwargs={'pk': self.msg1.pk})
        response = self.client.post(delete_url)
        self.assertEqual(response.status_code, 302)

        self.msg1.refresh_from_db()
        self.assertFalse(self.msg1.deleted_by_sender)
        self.assertFalse(self.msg1.deleted_by_recipient)


class JobEditOwnershipPermissionTests(TestCase):
    def setUp(self):
        self.rec1 = User.objects.create_user(username='recruiter_a', email='rec1@company.com', password='password123')
        self.rec2 = User.objects.create_user(username='recruiter_b', email='rec2@company.com', password='password123')
        UserProfile.objects.create(user=self.rec1, role='RECRUITER', company_name='Company A', is_approved=True)
        UserProfile.objects.create(user=self.rec2, role='RECRUITER', company_name='Company B', is_approved=True)

        self.comp1 = Company.objects.create(name='Company A')
        self.comp2 = Company.objects.create(name='Company B')

        self.job1 = Job.objects.create(job_title='Job A', company=self.comp1, posted_by=self.rec1)
        self.job2 = Job.objects.create(job_title='Job B', company=self.comp2, posted_by=self.rec2)

    def test_recruiter_cannot_edit_other_recruiter_job(self):
        self.client.login(username='recruiter_a', password='password123')
        edit_url = reverse('matching_app:job_edit', kwargs={'pk': self.job2.pk})
        response = self.client.get(edit_url)
        # Should deny access and redirect to job list
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('matching_app:job_list'))

        # On Browse Jobs page, recruiter_a should see Edit for Job A but NOT Job B
        list_url = reverse('matching_app:job_list')
        list_res = self.client.get(list_url)
        content = list_res.content.decode()
        self.assertIn(reverse('matching_app:job_edit', kwargs={'pk': self.job1.pk}), content)
        self.assertNotIn(reverse('matching_app:job_edit', kwargs={'pk': self.job2.pk}), content)


