import logging
import os
from enferno.app import create_app
from enferno.settings import DevConfig, ProdConfig, TestConfig

#TODO: Improve this code using a configuration environment variable
#      Also consider using dynaconf https://dynaconf.readthedocs.io/
bayanat_env = os.environ.get('BAYANAT_ENV')
if not bayanat_env:
    # Keeping backward compatibility...
    CONFIG = ProdConfig if os.environ.get('FLASK_DEBUG') == '0' else DevConfig
else:
    if bayanat_env == 'production':
        CONFIG = ProdConfig
    elif bayanat_env == 'development':
        CONFIG = DevConfig
    elif bayanat_env == 'testing':
        CONFIG = TestConfig
    else:
        logging.warning('Invalid value for BAYANAT_ENV. Please chose one of these values: '
                        '"production", "development" or "testing"')

app = create_app(CONFIG)
