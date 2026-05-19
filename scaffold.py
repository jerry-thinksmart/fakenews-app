import os

folders = [
    "database", "models", "routes", "services",
    "static/css", "static/js", "static/images",
    "templates/public", "templates/dashboard"
]

files = [
    "app.py", "config.py", ".env", "setup_nltk.py",
    "models/__init__.py", "models/user.py", "models/detection.py",
    "models/article.py", "models/log.py",
    "routes/__init__.py", "routes/public.py", "routes/auth.py", "routes/dashboard.py",
    "services/__init__.py", "services/predictor.py", "services/report_generator.py",
    "static/css/public.css", "static/css/dashboard.css",
    "static/js/public.js", "static/js/dashboard.js",
    "templates/base_public.html", "templates/base_dashboard.html",
    "templates/public/home.html", "templates/public/about.html",
    "templates/public/register.html", "templates/public/login.html",
    "templates/dashboard/index.html", "templates/dashboard/detect.html",
    "templates/dashboard/history.html", "templates/dashboard/records.html",
    "templates/dashboard/analytics.html", "templates/dashboard/reports.html",
    "templates/dashboard/model_management.html", "templates/dashboard/logs.html"
]

for folder in folders:
    os.makedirs(folder, exist_ok=True)
for file in files:
    with open(file, 'w') as f:
        pass

print("All folders and files created!")
