import os
from celery import Celery

# Establecer la configuración de Django para Celery
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('gestion_aulas')

# Usar configuración de Django para Celery
app.config_from_object('django.conf:settings', namespace='CELERY')

# Autodiscover tasks en todas las apps
app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')