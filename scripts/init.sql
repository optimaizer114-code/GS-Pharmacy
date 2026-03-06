-- إعداد قاعدة البيانات الأولي
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- للبحث النصي السريع

-- Index hints for performance
-- (الجداول تنشأ بواسطة SQLAlchemy)
