"""
add_jobs.py  —  Run this once to populate ResumeAI with 10 IT job listings.
Usage: python add_jobs.py
"""
import requests
import json

API = "http://localhost:8000"

jobs = [
    {
        "resume_text": """
        Software Engineer — Python Backend
        Company: TechCorp Solutions
        Location: Bangalore, India | Remote OK

        We are looking for a Python backend developer to build scalable APIs and data pipelines.

        Required Skills: Python, FastAPI, PostgreSQL, Docker, REST API, Git, Linux
        Preferred Skills: Redis, Kubernetes, AWS, SQLAlchemy

        Responsibilities:
        - Design and build RESTful APIs using FastAPI or Django
        - Write clean, well-tested Python code
        - Manage PostgreSQL databases and write complex queries
        - Deploy services using Docker and CI/CD pipelines

        Requirements:
        - 2+ years of experience in Python backend development
        - Strong knowledge of SQL and relational databases
        - Experience with Docker and containerization
        - Familiarity with Linux command line

        Salary: 8-15 LPA
        """,
        "career_goals": "Python backend developer role"
    },
    {
        "resume_text": """
        Data Scientist — Machine Learning Engineer
        Company: DataMind Analytics
        Location: Hyderabad, India | Hybrid

        Join our ML team to build predictive models and recommendation systems.

        Required Skills: Python, Machine Learning, Scikit-learn, Pandas, NumPy, SQL, TensorFlow
        Preferred Skills: PyTorch, Spark, Airflow, AWS SageMaker, Deep Learning, NLP

        Responsibilities:
        - Build and deploy machine learning models for production
        - Work with large datasets using Pandas and NumPy
        - Implement deep learning solutions using TensorFlow or PyTorch
        - Collaborate with data engineers on data pipelines

        Requirements:
        - 3+ years in data science or machine learning
        - Strong Python and statistics knowledge
        - Experience with ML model deployment
        - Knowledge of SQL for data extraction

        Salary: 12-22 LPA
        """,
        "career_goals": "Machine learning engineer"
    },
    {
        "resume_text": """
        Full Stack Developer — React and Node.js
        Company: WebWorks Digital
        Location: Mumbai, India | On-site

        Build modern web applications for enterprise clients.

        Required Skills: JavaScript, React, Node.js, HTML, CSS, REST API, Git, MongoDB
        Preferred Skills: TypeScript, GraphQL, Redis, Docker, AWS

        Responsibilities:
        - Develop responsive frontend applications using React
        - Build backend APIs with Node.js and Express
        - Work with MongoDB and design database schemas
        - Write unit and integration tests

        Requirements:
        - 2-5 years in full stack web development
        - Strong JavaScript and React skills
        - Experience with RESTful API design
        - Familiarity with version control using Git

        Salary: 10-18 LPA
        """,
        "career_goals": "Full stack web developer"
    },
    {
        "resume_text": """
        DevOps Engineer — Cloud Infrastructure
        Company: CloudBase Technologies
        Location: Pune, India | Remote

        Manage and automate cloud infrastructure for high-availability services.

        Required Skills: AWS, Docker, Kubernetes, Linux, Terraform, Jenkins, Bash, Git
        Preferred Skills: Azure, Ansible, Prometheus, Grafana, Python, CI/CD

        Responsibilities:
        - Design and maintain AWS cloud infrastructure
        - Build CI/CD pipelines using Jenkins or GitHub Actions
        - Manage Kubernetes clusters and containerized applications
        - Write infrastructure-as-code using Terraform

        Requirements:
        - 3+ years in DevOps or cloud infrastructure
        - Strong AWS and Linux knowledge
        - Experience with Docker and Kubernetes
        - Scripting skills in Bash or Python

        Salary: 12-20 LPA
        """,
        "career_goals": "DevOps cloud engineer"
    },
    {
        "resume_text": """
        Java Developer — Spring Boot Microservices
        Company: FinTech Systems Pvt Ltd
        Location: Chennai, India | Hybrid

        Build microservices-based banking and payment applications.

        Required Skills: Java, Spring Boot, Microservices, SQL, REST API, Maven, Git
        Preferred Skills: Kafka, Docker, Redis, PostgreSQL, AWS, JUnit

        Responsibilities:
        - Develop Spring Boot microservices for financial applications
        - Design and implement RESTful APIs
        - Write unit tests using JUnit and Mockito
        - Work with relational databases and write SQL queries

        Requirements:
        - 2-4 years of Java development experience
        - Strong Spring Boot and microservices knowledge
        - Experience with SQL databases
        - Understanding of software design patterns

        Salary: 8-16 LPA
        """,
        "career_goals": "Java Spring Boot developer"
    },
    {
        "resume_text": """
        Data Engineer — Big Data Pipeline
        Company: Analytics Hub
        Location: Bangalore, India | Remote OK

        Build and maintain large-scale data pipelines and ETL systems.

        Required Skills: Python, SQL, Apache Spark, Airflow, AWS, Kafka, PostgreSQL
        Preferred Skills: Scala, Redshift, dbt, Databricks, Docker, Linux

        Responsibilities:
        - Build scalable ETL pipelines using Apache Spark and Airflow
        - Manage data warehouse on AWS Redshift or similar
        - Write complex SQL queries for data transformation
        - Work with streaming data using Kafka

        Requirements:
        - 3+ years in data engineering
        - Strong Python and SQL skills
        - Experience with Apache Spark and distributed computing
        - Knowledge of cloud data platforms (AWS or GCP)

        Salary: 14-24 LPA
        """,
        "career_goals": "Data engineer big data"
    },
    {
        "resume_text": """
        Android Developer — Mobile Applications
        Company: AppStudio India
        Location: Delhi, India | On-site

        Develop consumer and enterprise Android applications.

        Required Skills: Kotlin, Java, Android SDK, REST API, Git, SQLite, XML
        Preferred Skills: Jetpack Compose, Retrofit, Firebase, MVVM, Room Database

        Responsibilities:
        - Build and maintain Android applications from scratch
        - Integrate REST APIs and third-party SDKs
        - Implement MVVM architecture with Jetpack components
        - Optimize app performance and battery usage

        Requirements:
        - 2+ years of Android development experience
        - Strong Kotlin or Java skills
        - Experience with Android SDK and Jetpack libraries
        - Knowledge of RESTful API integration

        Salary: 7-14 LPA
        """,
        "career_goals": "Android mobile developer"
    },
    {
        "resume_text": """
        Cybersecurity Analyst — Information Security
        Company: SecureNet Solutions
        Location: Hyderabad, India | Hybrid

        Protect organizational systems and networks from cyber threats.

        Required Skills: Linux, Networking, Python, SQL, Firewall, SIEM, Penetration Testing
        Preferred Skills: AWS Security, Docker, Kubernetes, CEH, CISSP, Splunk

        Responsibilities:
        - Monitor security events and respond to incidents
        - Conduct vulnerability assessments and penetration testing
        - Analyze logs using SIEM tools like Splunk
        - Implement and manage firewall and network security policies

        Requirements:
        - 2+ years in cybersecurity or information security
        - Strong Linux and networking fundamentals
        - Experience with security tools and SIEM platforms
        - Knowledge of Python for security automation

        Salary: 10-18 LPA
        """,
        "career_goals": "Cybersecurity information security analyst"
    },
    {
        "resume_text": """
        AI Engineer — Natural Language Processing
        Company: AI Labs India
        Location: Bangalore, India | Remote

        Build AI-powered NLP applications and conversational systems.

        Required Skills: Python, NLP, Machine Learning, TensorFlow, Scikit-learn, SQL, Git
        Preferred Skills: PyTorch, Hugging Face, Transformers, BERT, FastAPI, Docker, spaCy

        Responsibilities:
        - Build and fine-tune NLP models for text classification and extraction
        - Deploy ML models as REST APIs using FastAPI
        - Work with transformer models including BERT and GPT variants
        - Process and analyze large text datasets

        Requirements:
        - 2+ years in NLP or AI engineering
        - Strong Python and machine learning fundamentals
        - Experience with transformer models and Hugging Face
        - Knowledge of model deployment and MLOps

        Salary: 15-28 LPA
        """,
        "career_goals": "NLP AI engineer"
    },
    {
        "resume_text": """
        IT Support Engineer — Technical Support Level 2
        Company: Global IT Services
        Location: Bangalore, India | On-site

        Provide technical support and system administration for enterprise clients.

        Required Skills: Linux, Windows Server, Networking, Active Directory, SQL, Troubleshooting, Hardware
        Preferred Skills: Azure, AWS, Python, Bash scripting, ITIL, VMware

        Responsibilities:
        - Provide Level 2 technical support for hardware and software issues
        - Administer Linux and Windows Server environments
        - Manage Active Directory users, groups and group policies
        - Monitor network performance and resolve connectivity issues

        Requirements:
        - 1-3 years in IT support or system administration
        - Strong Linux and Windows Server knowledge
        - Experience with Active Directory and Group Policy
        - Good understanding of networking fundamentals TCP/IP DNS DHCP

        Salary: 4-8 LPA
        """,
        "career_goals": "IT support system administrator"
    },
]

print("Adding 10 job listings to ResumeAI...\n")
success = 0
for i, job in enumerate(jobs):
    try:
        r = requests.post(f"{API}/recommend", json=job, timeout=120)
        data = r.json()
        if data.get("success"):
            print(f"✓ Job {i+1} added: {job['career_goals']}")
            success += 1
        else:
            print(f"✗ Job {i+1} failed: {data.get('detail', 'unknown error')}")
    except Exception as e:
        print(f"✗ Job {i+1} error: {e}")

print(f"\nDone. {success}/10 jobs added successfully.")
print("You can now use the Job Recommend tab in the dashboard.")