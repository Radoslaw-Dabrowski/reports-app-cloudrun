"""
Configuration module for Reports App Cloud Run version.
Optimized for stateless, on-demand scaling.
"""
import os
from typing import Optional


class Config:
    """Base configuration class"""

    # Flask
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    FLASK_ENV = os.getenv('FLASK_ENV', 'production')

    # Database - Support both Cloud SQL Unix Socket and TCP
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_PORT = int(os.getenv('DB_PORT', '5432'))
    DB_NAME = os.getenv('DB_NAME', 'reports_db')
    DB_USER = os.getenv('DB_USER', 'postgres')
    DB_PASSWORD = os.getenv('DB_PASSWORD', '')
    DB_UNIX_SOCKET = os.getenv('DB_UNIX_SOCKET')  # For Cloud SQL

    @classmethod
    def get_database_url(cls) -> str:
        """Generate database URL based on connection type"""
        if cls.DB_UNIX_SOCKET:
            # Cloud SQL Unix Socket connection
            return f"postgresql://{cls.DB_USER}:{cls.DB_PASSWORD}@/{cls.DB_NAME}?host={cls.DB_UNIX_SOCKET}"
        else:
            # Standard TCP connection
            return f"postgresql://{cls.DB_USER}:{cls.DB_PASSWORD}@{cls.DB_HOST}:{cls.DB_PORT}/{cls.DB_NAME}"

    # AWS S3
    AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
    AWS_DEFAULT_REGION = os.getenv('AWS_DEFAULT_REGION', 'eu-north-1')
    S3_BUCKET_NAME = os.getenv('S3_BUCKET_NAME', 'dhc-reports')

    # Redis Cache (Cloud Memorystore)
    REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
    REDIS_PORT = int(os.getenv('REDIS_PORT', '6379'))
    REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', '')

    # Caching
    CACHE_TYPE = 'redis' if os.getenv('ENABLE_CACHE', 'true').lower() == 'true' else 'simple'
    CACHE_REDIS_HOST = REDIS_HOST
    CACHE_REDIS_PORT = REDIS_PORT
    CACHE_REDIS_PASSWORD = REDIS_PASSWORD
    CACHE_DEFAULT_TIMEOUT = int(os.getenv('CACHE_TTL', '3600'))

    # Cloud Run specific
    PORT = int(os.getenv('PORT', '8080'))
    WORKERS = int(os.getenv('WORKERS', '2'))
    THREADS = int(os.getenv('THREADS', '4'))
    TIMEOUT = int(os.getenv('TIMEOUT', '300'))

    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

    # Session
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = 3600  # 1 hour


class DevelopmentConfig(Config):
    """Development configuration"""
    FLASK_ENV = 'development'
    DEBUG = True
    CACHE_TYPE = 'simple'  # Use simple cache for dev
    SESSION_COOKIE_SECURE = False


class ProductionConfig(Config):
    """Production configuration"""
    FLASK_ENV = 'production'
    DEBUG = False


# Config dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': ProductionConfig
}


def get_config() -> Config:
    """Get configuration based on environment"""
    env = os.getenv('FLASK_ENV', 'production')
    return config.get(env, config['default'])
