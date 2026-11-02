"""
Django management command to populate the database with realistic sample Companies, Jobs, and Company Recruiter Users.

Usage:
    python manage.py seed_demo_data
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from matching_app.models import Company, Job, UserProfile


class Command(BaseCommand):
    help = 'Seeds the database with sample companies, jobs, and recruiter accounts for multi-user testing and demo.'

    def handle(self, *args, **options):
        # 1. Create Default Master System Admin User (Independent of any company)
        admin_username = "admin"
        admin_password = "admin123"
        admin_user, created = User.objects.get_or_create(username=admin_username, defaults={
            'email': "admin@jobfit.ai",
            'is_staff': True,
            'is_superuser': True
        })
        if created:
            admin_user.set_password(admin_password)
            admin_user.save()
            self.stdout.write(self.style.SUCCESS(f'Created Master Admin Superuser: username="{admin_username}", password="{admin_password}"'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Master Admin user "{admin_username}" already exists.'))

        UserProfile.objects.get_or_create(
            user=admin_user,
            defaults={'role': 'RECRUITER', 'company_name': 'JobFit AI System Admin'}
        )

        # 2. Create Dedicated Company Recruiter Accounts
        recruiters_data = [
            {
                'username': 'techvision_recruiter',
                'email': 'careers@techvision.com',
                'password': 'recruiter123',
                'company_name': 'TechVision Solutions',
            },
            {
                'username': 'datamind_recruiter',
                'email': 'hr@datamind.com',
                'password': 'recruiter123',
                'company_name': 'DataMind Analytics',
            },
            {
                'username': 'nextgen_recruiter',
                'email': 'jobs@nextgendigital.com',
                'password': 'recruiter123',
                'company_name': 'NextGen Digital',
            }
        ]

        recruiter_users = {}

        for r_data in recruiters_data:
            user, created = User.objects.get_or_create(
                username=r_data['username'],
                defaults={'email': r_data['email']}
            )
            if created:
                user.set_password(r_data['password'])
                user.save()
                self.stdout.write(self.style.SUCCESS(f'Created Recruiter User: username="{r_data["username"]}", password="{r_data["password"]}"'))
            else:
                user.set_password(r_data['password'])
                user.save()

            UserProfile.objects.get_or_create(
                user=user,
                defaults={'role': 'RECRUITER', 'company_name': r_data['company_name']}
            )
            recruiter_users[r_data['company_name']] = user

        # 3. Create Sample Companies
        sample_companies = [
            {
                "name": "TechVision Solutions",
                "email": "careers@techvision.com",
                "website": "https://techvision.example.com",
                "location": "San Francisco, CA",
                "description": "Leading enterprise cloud software and AI technology platform provider."
            },
            {
                "name": "DataMind Analytics",
                "email": "hr@datamind.com",
                "website": "https://datamind.example.com",
                "location": "New York, NY",
                "description": "Specialized machine learning and natural language processing research agency."
            },
            {
                "name": "NextGen Digital",
                "email": "jobs@nextgendigital.com",
                "website": "https://nextgen.example.com",
                "location": "Austin, TX",
                "description": "Full-service web application development and digital transformation consultancy."
            }
        ]

        companies_dict = {}
        for comp_data in sample_companies:
            comp, created = Company.objects.get_or_create(
                name=comp_data["name"],
                defaults=comp_data
            )
            companies_dict[comp.name] = comp
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created Company: "{comp.name}"'))

        # 4. Create Sample Jobs Linked to Each Company Recruiter
        sample_jobs = [
            {
                'job_title': 'Python Backend Engineer',
                'company': companies_dict.get('TechVision Solutions'),
                'posted_by': recruiter_users.get('TechVision Solutions'),
                'category': 'IT & Software',
                'job_type': 'Full Time',
                'location': 'San Francisco, CA (Hybrid)',
                'salary': '$90,000 - $115,000 / year',
                'vacancies': 2,
                'required_experience': '2-4 years',
                'required_skills': 'Python, Django, REST API, PostgreSQL, Docker, Git',
                'job_description': (
                    'We are seeking a skilled Python Backend Engineer to join our core API team. '
                    'In this role, you will design, develop, and maintain robust RESTful microservices using Django and PostgreSQL. '
                    'You will collaborate closely with frontend developers and DevOps engineers to deploy scalable applications using Docker. '
                    'Experience with unit testing, Git version control, and asynchronous task queues (Celery/Redis) is highly preferred.'
                )
            },
            {
                'job_title': 'Data Scientist & Machine Learning Specialist',
                'company': companies_dict.get('DataMind Analytics'),
                'posted_by': recruiter_users.get('DataMind Analytics'),
                'category': 'Data Science & AI',
                'job_type': 'Full Time',
                'location': 'New York, NY (Remote)',
                'salary': '$110,000 - $135,000 / year',
                'vacancies': 1,
                'required_experience': '3+ years',
                'required_skills': 'Python, Machine Learning, spaCy, Scikit-Learn, Pandas, NumPy, NLP',
                'job_description': (
                    'DataMind Analytics is looking for a Data Scientist specializing in Natural Language Processing (NLP) and Predictive Modeling. '
                    'You will extract insights from unstructured text data using Python libraries such as spaCy, NLTK, and Sentence-Transformers. '
                    'Requirements include strong familiarity with scikit-learn, pandas, numpy, model deployment, and evaluating machine learning metrics.'
                )
            },
            {
                'job_title': 'Full Stack Developer',
                'company': companies_dict.get('NextGen Digital'),
                'posted_by': recruiter_users.get('NextGen Digital'),
                'category': 'IT & Software',
                'job_type': 'Full Time',
                'location': 'Austin, TX',
                'salary': '$80,000 - $95,000 / year',
                'vacancies': 3,
                'required_experience': '1-3 years',
                'required_skills': 'JavaScript, HTML, CSS, Bootstrap, Python, Django, SQL',
                'job_description': (
                    'Join our fast-growing web development agency as a Full Stack Developer! '
                    'You will craft responsive user interfaces using HTML5, CSS3, Bootstrap 5, and JavaScript, while building solid server-side logic in Python/Django. '
                    'Must be comfortable interacting with SQLite/PostgreSQL databases, building API integrations, and maintaining clean code standards.'
                )
            }
        ]

        created_count = 0
        for job_data in sample_jobs:
            job = Job.objects.filter(job_title=job_data['job_title']).first()
            if not job:
                job = Job.objects.create(**job_data)
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'Created sample job: "{job.job_title}" at {job.company_name}'))
            else:
                job.posted_by = job_data['posted_by']
                job.company = job_data['company']
                job.save()
                self.stdout.write(self.style.SUCCESS(f'Updated job posting ownership for: "{job.job_title}" to recruiter {job.posted_by.username}'))

        self.stdout.write(self.style.SUCCESS('Successfully completed demo data seeding.'))
