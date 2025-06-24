web: gunicorn --timeout 120 --workers 2 nfse_abrasf.wsgi --log-file -
worker: celery -A nfse_abrasf worker --concurrency=1 --loglevel=info
# streamlit: sh -c "export PYTHONPATH=$(pwd):$PYTHONPATH && streamlit run extract/dashboard.py --server.port=$PORT --server.enableCORS=false"