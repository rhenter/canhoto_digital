# Canhoto Digital API

## Requirements

This project requires:

* Python 3.12
* PostgreSQL 9.3+
* Redis (for Celery broker running locally)
* Git
* virtualenvwrapper, pyenv virtualenv or virtualenv for local development

## Installation

### 1. Clone the repository

```shell
$ git clone <repository-url>
$ cd canhoto_digital
```

### 2. Set up Python environment

Using pyenv (recommended):

```shell
# Install pyenv if not already installed
$ curl https://pyenv.run | bash
$ export PATH="$HOME/.pyenv/bin:$PATH"
$ eval "$(pyenv init -)"
$ eval "$(pyenv virtualenv-init -)"

# Restart terminal or exec
$ exec "$SHELL"

# Install Python 3.12 and create virtual environment
$ pyenv install 3.12.0
$ pyenv virtualenv 3.12.0 canhoto_digital
$ pyenv activate canhoto_digital
```

### 3. Install dependencies

```shell
$ pip install -r requirements/local.txt
```

Or using make:

```shell
$ make deps
```

### 4. Configure environment

```shell
$ cp local.env .env
# Edit .env file with your local settings
```

### 5. Set up database

```shell
$ python src/manage.py migrate
```

Or using make:

```shell
$ make migrate
```

### 6. Create superuser (optional)

```shell
$ python src/manage.py createsuperuser
```

## Development

### Running the Development Server Locally

```shell
$ python src/manage.py runserver
```

Or using make:

```shell
$ make run
```

The API will be available at `http://localhost:8000/`

### Running the Development Server using Docker

```shell
$ docker compose up --build
# admin: http://localhost:8000/admin
```

### Running Celery Worker

For background task processing:

```shell
$ make celery
```

Or manually:

```shell
$ cd src
$ celery -A proj_settings worker --loglevel=info
```

### Available Make Commands

* `make deps` - Install dependencies
* `make run` - Run development server
* `make migrate` - Apply database migrations
* `make migrations` - Create new migrations
* `make test` - Run tests
* `make celery` - Start Celery worker
* `make clean` - Clean temporary files

## Testing

We use `pytest` with additional plugins for comprehensive testing.

Run all tests:

```shell
$ cd src
$ pytest -vv -s
```

Run tests with coverage:

```shell
$ cd src
$ pytest --cov=apps --cov-report=html
```


## SEFAZ Integration — How to use

The project includes a real integration with SEFAZ DF-e distribution to fetch your company's latest invoices. The client lives at `src/apps/invoice/sefaz/` and is used by an Admin action and a Celery task.

### Prerequisites
- A Company record with the following fields filled:
  - `cnpj` (numbers only)
  - `uf` (state)
  - `sefaz_environment` ("production" or "homologation")
  - `certificate` (A1 e-CNPJ file: .pfx or .p12)
  - `certificate_password`
- Celery worker running.
- Optional setting (already defaulted): `SEFAZ_HTTP_TIMEOUT_SECONDS` in `proj_settings.settings` to tune HTTP timeout (default: 60 seconds).

### Option 1 — Import via Django Admin
1) Go to Admin → Invoices.
2) Click "Import from SEFAZ" in the top-right actions.
3) Fill the form: Company and date range.
4) Submit. A Celery task will be enqueued and progress will appear in Celery logs.

Invoices that match the selected date range will be created/updated in the `Invoice` model. The company's `last_nsu` is updated as batches are processed.

### Option 2 — Programmatic import (Celery task)
You can trigger the same import task programmatically, for example, from the Django shell:

```python
from datetime import date
from apps.company.models import Company
from apps.invoice.tasks import import_from_sefaz

company = Company.objects.get(cnpj="00000000000000")  # replace with your CNPJ
res = import_from_sefaz.delay(company.id, date(2025, 1, 1).isoformat(), date(2025, 1, 31).isoformat())
print(res.id)  # Celery task id
```

When the task finishes, it returns a payload like `{ "created": X, "updated": Y }`.

### Notes
- The integration uses the official national DF-e SOAP endpoint with mutual TLS (client certificate). No paid providers are required.
- SEFAZ may return summary documents (`resNFe`) or full NF-e (`procNFe`). The importer maps available data into `Invoice` fields; XML/PDF files are not persisted by default.
- The NSU cursor (`company.last_nsu`) advances even if no invoices fall within the chosen date filter, which avoids re-reading old batches.
- If you switch environments (homologation/production) or certificates, you may want to reset `last_nsu` to `0`.
- Errors will surface in Admin messages or Celery logs. Check certificate validity and password if TLS errors occur.
