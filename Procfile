web: gunicorn --timeout 120 --workers 2 nfse_abrasf.wsgi --log-file -
worker: celery -A nfse-abrasf-project worker --loglevel=info
