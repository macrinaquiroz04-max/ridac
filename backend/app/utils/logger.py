# backend/app/utils/logger.py

import logging
import sys
from pathlib import Path
from datetime import datetime
from app.config import settings

def setup_logger(name: str = "ridac_ocr") -> logging.Logger:
    """Configurar logger del sistema"""

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # Evitar duplicados
    if logger.handlers:
        return logger

    # Formato
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Handler para consola
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Handler para archivo
    try:
        log_dir = Path(settings.LOG_PATH)
        log_dir.mkdir(parents=True, exist_ok=True)

        log_file = log_dir / f"sistema_{datetime.now().strftime('%Y%m%d')}.log"

        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        logger.error(f"No se pudo crear archivo de log: {e}")

    return logger

# Logger global
logger = setup_logger()
