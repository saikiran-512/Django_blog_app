# Django Blog Application

A blog application developed using Django 5.2 and PostgreSQL, following the *Django 5 By Example – Fifth Edition* book.

## Features

- Create, edit, and manage blog posts.
- Display a list of published blog posts.
- View individual blog posts.
- Share blog posts via email.
- Add comments to blog posts.
- Paginate blog posts.
- Search blog posts.

## Technologies Used

- Python
- Django 5.2
- PostgreSQL
- Psycopg 3
- python-decouple
- HTML

## Project Structure

```text
mysite/
├── blog/
│   ├── migrations/
│   ├── templates/
│   ├── templatetags/
│   ├── models.py
│   ├── views.py
│   ├── forms.py
│   └── urls.py
├── mysite/
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── manage.py
├── requirements.txt
├── .env.example
└── .gitignore
```

## Setup Instructions

1. Clone the repository:

   ```bash
   git clone YOUR_REPOSITORY_URL
   cd mysite
   ```

2. Create and activate a virtual environment:

   ```bash
   python -m venv venv
   ```

   Windows PowerShell:

   ```powershell
   .\venv\Scripts\Activate.ps1
   ```

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file using `.env.example` as a reference. Configure your Django secret key, PostgreSQL credentials, and email settings.

5. Create the PostgreSQL database and configure its credentials.

6. Apply database migrations:

   ```bash
   python manage.py migrate
   ```

7. Start the development server:

   ```bash
   python manage.py runserver
   ```

8. Open http://127.0.0.1:8000/ in your browser.

## License

This project is currently for learning and development purposes.
