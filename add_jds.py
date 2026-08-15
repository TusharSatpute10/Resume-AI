"""
add_jds.py — Add sample job descriptions to the database.
Usage: python add_jds.py
"""
import requests
import json

API = "http://localhost:8000"

jds = [
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
        """
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
        """
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
        """
    },
    {
        "resume_text": """
        DevOps Engineer — Cloud Infrastructure
        Company: CloudBase Technologies
        Location: Pune, India | Remote

        Manage and automate cloud infrastructure for high-availability services.

        Required Skills: AWS, Docker, Kubernetes, Linux, Terraform, Jenkins, Bash, Git
        Preferred Skills: Azure, GCP, Ansible, Prometheus, Grafana

        Responsibilities:
        - Manage and automate cloud infrastructure using Terraform and Ansible
        - Deploy and monitor applications using Kubernetes and Docker
        - Implement CI/CD pipelines with Jenkins and GitLab CI
        - Monitor system performance and set up alerting with Prometheus

        Requirements:
        - 3+ years in DevOps or cloud engineering
        - Strong Linux and scripting skills
        - Experience with AWS or Azure cloud platforms
        - Knowledge of containerization and orchestration

        Salary: 12-20 LPA
        """
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
        """
    }
]

print("Adding 5 job descriptions to ResumeAI...\n")
success = 0
for i, jd in enumerate(jds):
    try:
        r = requests.post(f"{API}/parse/jd", json=jd, timeout=120)
        data = r.json()
        if data.get("success"):
            print(f"✓ JD {i+1} added successfully")
            success += 1
        else:
            print(f"✗ JD {i+1} failed: {data.get('detail', 'unknown error')}")
    except Exception as e:
        print(f"✗ JD {i+1} error: {e}")

print(f"\nDone. {success}/5 JDs added successfully.")