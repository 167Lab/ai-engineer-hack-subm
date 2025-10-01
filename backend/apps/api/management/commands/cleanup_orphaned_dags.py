"""
Django Management Command для автоматической очистки осиротевших DAG файлов
Использование: python manage.py cleanup_orphaned_dags [--dry-run] [--force]
"""
import logging
import sys
from datetime import datetime
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = """
    Автоматическая очистка осиротевших DAG файлов в Airflow.
    Удаляет физические .py файлы, которые не зарегистрированы в базе данных Airflow.
    
    Примеры использования:
        python manage.py cleanup_orphaned_dags --dry-run    # Просмотр без удаления
        python manage.py cleanup_orphaned_dags --force      # Реальное удаление
    """

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            default=False,
            help='Режим просмотра - показать что будет удалено, но не удалять'
        )
        
        parser.add_argument(
            '--force',
            action='store_true',
            default=False,
            help='Принудительное удаление без подтверждения'
        )
        
        parser.add_argument(
            '--max-files',
            type=int,
            default=50,
            help='Максимальное количество файлов для удаления за раз (безопасность)'
        )

    def handle(self, *args, **options):
        """Главная логика команды"""
        
        self.stdout.write("=" * 60)
        self.stdout.write(f"🧹 АВТОМАТИЧЕСКАЯ ОЧИСТКА ОСИРОТЕВШИХ DAG ФАЙЛОВ")
        self.stdout.write(f"📅 Время запуска: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.stdout.write("=" * 60)
        
        dry_run = options['dry_run']
        force = options['force']
        max_files = options['max_files']
        
        # Режим работы
        if dry_run:
            self.stdout.write(self.style.WARNING("🔍 [DRY RUN] Режим просмотра - файлы НЕ будут удалены"))
        elif not force:
            self.stdout.write(self.style.WARNING("⚠️  [INTERACTIVE] Потребуется подтверждение удаления"))
        else:
            self.stdout.write(self.style.SUCCESS("🗑️  [FORCE] Автоматическое удаление включено"))

        try:
            # Проверяем, что мы в Docker окружении Airflow
            self._validate_environment()
            
            # Инициализируем менеджер
            from generators.dag_cleanup_utils import DAGManager
            manager = DAGManager()
            
            # Поиск осиротевших файлов
            self.stdout.write("\n🔍 Поиск осиротевших файлов DAG...")
            orphaned_files = manager.list_orphaned_files()
            
            if not orphaned_files:
                self.stdout.write(self.style.SUCCESS("✅ Осиротевших файлов не найдено. Система чистая!"))
                return
            
            # Проверка лимита безопасности
            if len(orphaned_files) > max_files:
                raise CommandError(
                    f"⚠️ Найдено {len(orphaned_files)} файлов, что превышает лимит безопасности {max_files}. "
                    f"Используйте --max-files для увеличения лимита."
                )
            
            # Показываем найденные файлы
            self.stdout.write(f"\n📋 Найдено {len(orphaned_files)} осиротевших файлов:")
            for i, file_id in enumerate(orphaned_files, 1):
                self.stdout.write(f"   {i:2d}. {file_id}.py")
            
            # Режим просмотра
            if dry_run:
                self.stdout.write(f"\n🔍 [DRY RUN] Было бы удалено {len(orphaned_files)} файлов")
                self.stdout.write(self.style.SUCCESS("✅ Режим просмотра завершен"))
                return
            
            # Подтверждение пользователем
            if not force:
                confirm = input(f"\n❓ Удалить {len(orphaned_files)} файлов? [y/N]: ").strip().lower()
                if confirm not in ['y', 'yes', 'да']:
                    self.stdout.write(self.style.WARNING("❌ Операция отменена пользователем"))
                    return
            
            # Выполняем удаление
            self.stdout.write(f"\n🗑️ Удаление {len(orphaned_files)} файлов...")
            deleted_count = manager.cleanup_all_orphaned()
            
            # Результаты
            if deleted_count == len(orphaned_files):
                self.stdout.write(self.style.SUCCESS(f"✅ Успешно удалено все {deleted_count} файлов"))
                logger.info(f"Cleanup completed successfully: {deleted_count} files deleted")
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f"⚠️ Удалено {deleted_count} из {len(orphaned_files)} файлов. "
                        f"Проверьте логи для деталей."
                    )
                )
                logger.warning(f"Partial cleanup: {deleted_count}/{len(orphaned_files)} files deleted")

        except Exception as e:
            error_msg = f"💥 Критическая ошибка очистки: {str(e)}"
            self.stdout.write(self.style.ERROR(error_msg))
            logger.exception(error_msg)
            raise CommandError(error_msg)
        
        finally:
            self.stdout.write(f"\n📅 Завершено: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    def _validate_environment(self):
        """Проверка, что команда запущена в правильном окружении"""
        import os
        
        # Проверяем наличие директории DAG Airflow
        dags_folder = "/opt/airflow/dags"
        if not os.path.exists(dags_folder):
            raise CommandError(
                f"⚠️ Директория {dags_folder} не найдена. "
                f"Команда должна запускаться в Docker-окружении Airflow."
            )
        
        # Проверяем права доступа
        if not os.access(dags_folder, os.R_OK | os.W_OK):
            raise CommandError(
                f"⚠️ Недостаточно прав для доступа к {dags_folder}. "
                f"Запустите команду от пользователя с правами на запись."
            )
        
        self.stdout.write(self.style.SUCCESS(f"✅ Окружение валидно: {dags_folder}"))
