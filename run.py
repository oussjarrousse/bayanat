import logging
import os
from enferno.app import create_app
from enferno.settings import DevConfig, ProdConfig, TestConfig

#TODO: Improve this code using a configuration environment variable
#      Also consider using dynaconf https://dynaconf.readthedocs.io/

app_env = os.environ.get('BAYANAT_ENV')

if not app_env:
    # Keeping backward compatibility...
    CONFIG = ProdConfig if os.environ.get('FLASK_DEBUG') == '0' else DevConfig
else:
    if app_env == 'production':
        CONFIG = ProdConfig
    elif app_env == 'development':
        CONFIG = DevConfig
    elif app_env == 'testing':
        CONFIG = TestConfig
    else:
        logging.warning('Invalid value for BAYANAT_ENV. Please chose one of these values: '
                        '"production", "development" or "testing"')

app = create_app(CONFIG)
