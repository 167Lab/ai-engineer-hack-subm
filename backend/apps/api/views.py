from django.shortcuts import render
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import ValidationError
from .serializers import (
    DataSourceAnalysisRequestSer, DAGGenerationRequestSer,
    DataSourceAnalysisResponseSer, DAGDeploymentRequestSer
)
from apps.agents.integration import LLMIntegration
from services.airflow import render_dag_py, deploy_dag_to_airflow, get_recs_for_source, delete_dag_properly

# Create your views here.

# /api/v1/analyze
class AnalyzeDataSourceView(APIView):
    def post(self, request):
        import asyncio
        
        ser = DataSourceAnalysisRequestSer(data=request.data)
        ser.is_valid(raise_exception=True)
        
        try:
            mas = LLMIntegration()
            # Запускаем async функцию в event loop
            result = asyncio.run(mas.analyze_data_source(ser.validated_data))
            return Response(result)
        except Exception as e:
            return Response({
                'error': str(e),
                'status': 'failed'
            }, status=400)

# /api/v1/analyze_file_stream
class AnalyzeFileStreamView(APIView):
    """
    Production-ready streaming file upload для больших файлов
    Обрабатывает файлы по частям, не загружая все в память
    """
    def post(self, request):
        """
        Streaming анализ загружаемого файла
        
        Ожидает multipart/form-data:
        - file: файл для анализа
        - source_type: тип источника (csv, json, xml)
        - sample_size: количество строк для анализа (по умолчанию 1000)
        """
        import tempfile
        import os
        import logging
        import asyncio
        from django.core.files.storage import default_storage
        from django.core.files.base import ContentFile
        
        logger = logging.getLogger(__name__)
        
        try:
            # Получаем загружаемый файл
            uploaded_file = request.FILES.get('file')
            if not uploaded_file:
                return Response({
                    'error': 'Файл не найден в запросе',
                    'status': 'failed'
                }, status=400)
            
            # Получаем параметры
            source_type = request.data.get('source_type', 'csv').lower()
            sample_size = int(request.data.get('sample_size', 1000))
            persist = request.data.get('persist', 'true').lower() == 'true'
            
            # Валидация размера файла
            max_size = 1024 * 1024 * 1024  # 1 GB
            if uploaded_file.size > max_size:
                return Response({
                    'error': f'Файл слишком большой. Максимум: {max_size // (1024*1024)} MB',
                    'details': {
                        'file_size': uploaded_file.size,
                        'max_size': max_size,
                        'file_name': uploaded_file.name
                    },
                    'status': 'failed'
                }, status=413)
            
            logger.info(f"Streaming анализ файла: {uploaded_file.name} ({uploaded_file.size} bytes)")
            
            # Создаем временный файл для streaming обработки
            with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{source_type}') as tmp_file:
                # Записываем файл по частям (chunks) чтобы не загружать в память
                chunk_size = 64 * 1024  # 64KB chunks
                total_written = 0
                
                for chunk in uploaded_file.chunks(chunk_size):
                    tmp_file.write(chunk)
                    total_written += len(chunk)
                
                tmp_file.flush()
                logger.info(f"Записано во временный файл: {total_written} bytes")
                
                try:
                    # Используем гибридный анализатор (Stack Overflow + наши улучшения)
                    from analyzers.hybrid_file_analyzer import HybridFileAnalyzer
                    
                    analyzer = HybridFileAnalyzer()
                    result = analyzer.analyze_uploaded_file(
                        file_path=tmp_file.name,
                        source_type=source_type,
                        sample_size=sample_size,
                        original_filename=uploaded_file.name
                    )
                    
                    logger.info(f"Streaming анализ завершен для файла {uploaded_file.name}")
                    
                    persisted_path = None
                    if persist:
                        # Сохраняем копию в общий каталог для Airflow
                        safe_name = os.path.basename(uploaded_file.name)
                        uploads_dir = '/opt/airflow/data/uploads'
                        os.makedirs(uploads_dir, exist_ok=True)
                        persisted_path = os.path.join(uploads_dir, safe_name)
                        try:
                            # Перекопируем временный файл в общий том
                            import shutil
                            shutil.copy2(tmp_file.name, persisted_path)
                            logger.info(f"Файл сохранен для деплоя: {persisted_path}")
                        except Exception as save_err:
                            logger.warning(f"Не удалось сохранить файл в общий каталог: {save_err}")
                            persisted_path = None
                    
                    return Response({
                        'status': 'success',
                        'analysis_result': result,
                        'file_info': {
                            'name': uploaded_file.name,
                            'size': uploaded_file.size,
                            'processed_size': total_written,
                            'source_type': source_type,
                            'sample_size': sample_size,
                            'persisted_path': persisted_path
                        }
                    })
                    
                except Exception as analysis_error:
                    logger.exception(f"❌ Ошибка анализа файла {uploaded_file.name}: {analysis_error}")
                    
                    return Response({
                        'error': f'Ошибка анализа файла: {str(analysis_error)}',
                        'details': {
                            'file_name': uploaded_file.name,
                            'analysis_error': str(analysis_error)
                        },
                        'status': 'failed'
                    }, status=500)
                
                finally:
                    # Очищаем временный файл
                    try:
                        os.unlink(tmp_file.name)
                        logger.info(f"Удален временный файл: {tmp_file.name}")
                    except Exception as cleanup_error:
                        logger.warning(f"Не удалось удалить временный файл: {cleanup_error}")
        
        except Exception as e:
            logger.exception(f"Критическая ошибка streaming upload: {e}")
            
            return Response({
                'error': f'Системная ошибка обработки файла: {str(e)}',
                'status': 'failed'
            }, status=500)

# /api/v1/generate_dag
class GenerateDAGView(APIView):
    def post(self, request):
        try:
            ser = DAGGenerationRequestSer(data=request.data)
            ser.is_valid(raise_exception=True)
            dag_py, dag_id = render_dag_py(ser.validated_data)
            return Response({"dag_id": dag_id, "dag_py": dag_py})
        except Exception as e:
            return Response({
                'status': 'failed',
                'error': str(e)
            }, status=400)

    def get(self, request):
        # Упрощенный GET для тестирования из браузера
        try:
            data = {
                'dag_name': request.query_params.get('dag_name'),
                'source_config': {
                    'type': request.query_params.get('source_type', 'csv'),
                    'path': request.query_params.get('source_path', '/opt/airflow/data/sample.csv'),
                },
                'target_config': {
                    'type': request.query_params.get('target_type', 'postgres'),
                    'table': request.query_params.get('target_table', 'processed_data'),
                },
                'schedule': request.query_params.get('schedule', '@once'),
                'owner': request.query_params.get('owner', 'etl-system'),
                'description': request.query_params.get('description')
            }
            ser = DAGGenerationRequestSer(data=data)
            ser.is_valid(raise_exception=True)
            dag_py, dag_id = render_dag_py(ser.validated_data)
            return Response({"dag_id": dag_id, "dag_py": dag_py})
        except Exception as e:
            return Response({
                'status': 'failed',
                'error': str(e)
            }, status=400)

# /api/v1/recommendations?source_id=...
class GetRecommendationsView(APIView):
    def get(self, request):
        source_id = request.query_params.get("source_id")
        if not source_id:
            raise ValidationError({"source_id": "This query parameter is required"})
        recs = get_recs_for_source(source_id)
        return Response({"source_id": source_id, "recommendations": recs})

# /api/v1/deploy_dag
class DeployDAGView(APIView):
    def post(self, request):
        ser = DAGDeploymentRequestSer(data=request.data)
        ser.is_valid(raise_exception=True)
        deploy_info = deploy_dag_to_airflow(ser.validated_data)
        return Response(deploy_info)

    def get(self, request):
        # Поддержка GET для удобства тестирования из браузера/линков
        data = {
            'dag_name': request.query_params.get('dag_name'),
            'source_config': {
                'type': request.query_params.get('source_type'),
                'path': request.query_params.get('source_path'),
            },
            'target_config': {
                'type': request.query_params.get('target_type'),
                'table': request.query_params.get('target_table'),
            },
            'schedule': request.query_params.get('schedule'),
            'owner': request.query_params.get('owner'),
            'description': request.query_params.get('description'),
            'retries': request.query_params.get('retries'),
            'retry_delay': request.query_params.get('retry_delay'),
        }
        # Очистка пустых значений
        data['source_config'] = {k: v for k, v in data['source_config'].items() if v}
        data['target_config'] = {k: v for k, v in data['target_config'].items() if v}
        data = {k: v for k, v in data.items() if v is not None}

        ser = DAGDeploymentRequestSer(data=data)
        ser.is_valid(raise_exception=True)
        deploy_info = deploy_dag_to_airflow(ser.validated_data)
        return Response(deploy_info)

# /api/v1/delete_dag_complete
class DeleteDAGCompleteView(APIView):
    """
    Production-ready endpoint для полного удаления DAG
    Удаляет DAG из базы данных Airflow И физический файл
    """
    def delete(self, request, dag_id):
        """
        Полное удаление DAG по dag_id
        
        Args:
            dag_id: Идентификатор DAG из URL path
            
        Returns:
            JSON с результатом операции удаления
        """
        import logging
        
        logger = logging.getLogger(__name__)
        logger.info(f"Запрос на полное удаление DAG: {dag_id}")
        
        # Валидация dag_id
        if not dag_id or not isinstance(dag_id, str):
            return Response({
                "status": "error",
                "message": "Некорректный dag_id",
                "details": {"dag_id": dag_id}
            }, status=400)
        
        # Санитизация dag_id (безопасность)
        dag_id = dag_id.strip()
        if not dag_id.replace('_', '').replace('-', '').isalnum():
            return Response({
                "status": "error", 
                "message": "DAG ID содержит недопустимые символы",
                "details": {"allowed": "буквы, цифры, _, -"}
            }, status=400)
        
        try:
            # Выполняем удаление
            result = delete_dag_properly(dag_id)
            
            # Логируем результат
            if result["status"] == "success":
                logger.info(f"DAG '{dag_id}' успешно удален полностью")
                status_code = 200
            else:
                logger.error(f"Ошибка удаления DAG '{dag_id}': {result.get('message')}")
                status_code = 500
                
            return Response(result, status=status_code)
            
        except Exception as e:
            # Критическая ошибка - логируем подробно
            logger.exception(f"Критическая ошибка удаления DAG '{dag_id}': {e}")
            
            return Response({
                "status": "error",
                "message": f"Системная ошибка при удалении DAG '{dag_id}'",
                "details": {
                    "exception": str(e),
                    "dag_id": dag_id
                }
            }, status=500)

# /api/v1/dags/cleanup_orphaned
class CleanupOrphanedDAGsView(APIView):
    """
    Эндпоинт для очистки осиротевших DAG файлов
    (файлы есть, но DAG не зарегистрированы в Airflow)
    """
    def post(self, request):
        """
        Поиск и удаление осиротевших файлов DAG
        
        Query params:
            dry_run: если true, только показывает что будет удалено
        """
        import logging
        from generators.dag_cleanup_utils import DAGManager
        
        logger = logging.getLogger(__name__)
        dry_run = request.query_params.get('dry_run', 'false').lower() == 'true'
        
        logger.info(f"Запрос очистки осиротевших DAG (dry_run={dry_run})")
        
        try:
            manager = DAGManager()
            
            # Сначала находим осиротевшие файлы
            orphaned_files = manager.list_orphaned_files()
            
            if not orphaned_files:
                return Response({
                    "status": "success",
                    "message": "Осиротевших файлов не найдено",
                    "details": {
                        "orphaned_count": 0,
                        "files_deleted": 0,
                        "dry_run": dry_run
                    }
                })
            
            if dry_run:
                # Режим просмотра - не удаляем
                logger.info(f"[DRY RUN] Найдено {len(orphaned_files)} осиротевших файлов")
                return Response({
                    "status": "success",
                    "message": f"[DRY RUN] Найдено {len(orphaned_files)} осиротевших файлов",
                    "details": {
                        "orphaned_files": orphaned_files,
                        "orphaned_count": len(orphaned_files),
                        "would_delete": len(orphaned_files),
                        "dry_run": True
                    }
                })
            
            # Режим реального удаления
            deleted_count = manager.cleanup_all_orphaned()
            
            logger.info(f"Удалено {deleted_count} осиротевших файлов из {len(orphaned_files)}")
            
            return Response({
                "status": "success",
                "message": f"Удалено {deleted_count} осиротевших файлов",
                "details": {
                    "orphaned_files": orphaned_files,
                    "orphaned_count": len(orphaned_files),
                    "files_deleted": deleted_count,
                    "dry_run": False
                }
            })
            
        except Exception as e:
            logger.exception(f"Ошибка очистки осиротевших файлов: {e}")
            
            return Response({
                "status": "error",
                "message": "Ошибка при очистке осиротевших файлов",
                "details": {
                    "exception": str(e),
                    "dry_run": dry_run
                }
            }, status=500)

# /api/v1/dags/health_report
class DAGHealthReportView(APIView):
    """
    Эндпоинт для получения отчета о состоянии системы управления DAG
    """
    def get(self, request):
        """
        Получение отчета о здоровье системы
        
        Query params:
            hours: количество часов для анализа (по умолчанию 24)
        """
        import logging
        from services.dag_monitoring import get_monitoring_service
        
        logger = logging.getLogger(__name__)
        
        try:
            # Получаем параметры
            hours = int(request.query_params.get('hours', '24'))
            
            # Валидация параметров
            if hours < 1 or hours > 168:  # От 1 часа до 7 дней
                return Response({
                    "status": "error",
                    "message": "Параметр hours должен быть от 1 до 168 (7 дней)",
                    "details": {"provided_hours": hours}
                }, status=400)
            
            # Получаем сервис мониторинга
            monitoring = get_monitoring_service()
            
            # Генерируем отчет
            health_report = monitoring.get_health_report(hours=hours)
            
            logger.info(f"Создан health report за {hours} часов, статус: {health_report.get('status')}")
            
            return Response(health_report)
            
        except ValueError:
            return Response({
                "status": "error",
                "message": "Некорректное значение параметра hours",
                "details": {"hours": request.query_params.get('hours')}
            }, status=400)
            
        except Exception as e:
            logger.exception(f"Ошибка создания health report: {e}")
            
            return Response({
                "status": "error",
                "message": "Ошибка при создании отчета о состоянии",
                "details": {"exception": str(e)}
            }, status=500)

# /api/v1/upload_chunk
class UploadChunkView(APIView):
    """
    Endpoint для загрузки файла по частям (chunks)
    Минимизирует использование памяти браузера и сервера
    """
    def post(self, request):
        """
        Принимает и сохраняет один чанк файла
        
        Form data:
        - chunk: часть файла (Blob)
        - upload_id: уникальный ID загрузки
        - chunk_index: индекс чанка
        - total_chunks: общее количество чанков
        - file_name: имя файла
        - source_type: тип файла
        - chunk_hash: хеш для проверки целостности
        """
        import os
        import logging
        from django.conf import settings
        
        logger = logging.getLogger(__name__)
        
        try:
            # Получаем данные чанка
            chunk = request.FILES.get('chunk')
            if not chunk:
                return Response({
                    'error': 'Чанк файла не найден',
                    'status': 'failed'
                }, status=400)
            
            upload_id = request.data.get('upload_id')
            chunk_index = int(request.data.get('chunk_index', 0))
            total_chunks = int(request.data.get('total_chunks', 1))
            file_name = request.data.get('file_name')
            source_type = request.data.get('source_type')
            chunk_hash = request.data.get('chunk_hash')
            
            logger.info(f"Получен чанк {chunk_index + 1}/{total_chunks} для файла {file_name}")
            
            # Создаем директорию для временных файлов загрузки
            upload_dir = os.path.join(settings.FILE_UPLOAD_TEMP_DIR or '/tmp', 'chunked_uploads', upload_id)
            os.makedirs(upload_dir, exist_ok=True)
            
            # Сохраняем чанк
            chunk_path = os.path.join(upload_dir, f'chunk_{chunk_index:04d}')
            with open(chunk_path, 'wb') as f:
                for chunk_data in chunk.chunks():
                    f.write(chunk_data)
            
            # Сохраняем метаданные чанка
            metadata_path = os.path.join(upload_dir, f'chunk_{chunk_index:04d}.meta')
            with open(metadata_path, 'w') as f:
                import json
                json.dump({
                    'index': chunk_index,
                    'total_chunks': total_chunks,
                    'file_name': file_name,
                    'source_type': source_type,
                    'chunk_hash': chunk_hash,
                    'size': chunk.size
                }, f)
            
            logger.info(f"Чанк {chunk_index + 1}/{total_chunks} сохранен: {chunk.size} bytes")
            
            return Response({
                'status': 'success',
                'message': f'Чанк {chunk_index + 1}/{total_chunks} успешно загружен',
                'details': {
                    'upload_id': upload_id,
                    'chunk_index': chunk_index,
                    'chunk_size': chunk.size,
                    'progress': round(((chunk_index + 1) / total_chunks) * 100, 1)
                }
            })
            
        except Exception as e:
            logger.exception(f"❌ Ошибка загрузки чанка: {e}")
            return Response({
                'error': f'Ошибка загрузки чанка: {str(e)}',
                'status': 'failed'
            }, status=500)

# /api/v1/finalize_chunked_upload  
class FinalizeChunkedUploadView(APIView):
    """
    Endpoint для объединения чанков и запуска анализа
    """
    def post(self, request):
        """
        Объединяет все чанки в один файл и запускает streaming анализ
        """
        import os
        import logging
        import json
        import asyncio
        from django.conf import settings
        
        logger = logging.getLogger(__name__)
        
        try:
            data = request.data
            upload_id = data.get('upload_id')
            file_name = data.get('file_name')
            source_type = data.get('source_type')
            file_size = data.get('file_size', 0)
            sample_size = int(data.get('sample_size', 1000))
            persist = str(data.get('persist', 'true')).lower() == 'true'
            
            logger.info(f"Финализация chunked upload: {file_name} ({file_size} bytes)")
            
            upload_dir = os.path.join(settings.FILE_UPLOAD_TEMP_DIR or '/tmp', 'chunked_uploads', upload_id)
            
            if not os.path.exists(upload_dir):
                return Response({
                    'error': f'Данные загрузки не найдены: {upload_id}',
                    'status': 'failed'
                }, status=404)
            
            # Собираем информацию о чанках
            chunks_info = []
            for file in os.listdir(upload_dir):
                if file.endswith('.meta'):
                    with open(os.path.join(upload_dir, file), 'r') as f:
                        chunks_info.append(json.load(f))
            
            # Сортируем чанки по индексу
            chunks_info.sort(key=lambda x: x['index'])
            
            if not chunks_info:
                return Response({
                    'error': 'Чанки файла не найдены',
                    'status': 'failed'
                }, status=400)
            
            # Создаем временный файл для объединенных данных
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{source_type}') as combined_file:
                combined_path = combined_file.name
                
                # Объединяем чанки
                total_size = 0
                for chunk_info in chunks_info:
                    chunk_path = os.path.join(upload_dir, f'chunk_{chunk_info["index"]:04d}')
                    if os.path.exists(chunk_path):
                        with open(chunk_path, 'rb') as chunk_file:
                            data_chunk = chunk_file.read()
                            combined_file.write(data_chunk)
                            total_size += len(data_chunk)
                
                logger.info(f"Объединено {len(chunks_info)} чанков в файл: {total_size} bytes")
            
            try:
                # Запускаем гибридный анализ объединенного файла
                from analyzers.hybrid_file_analyzer import HybridFileAnalyzer
                
                analyzer = HybridFileAnalyzer()
                result = analyzer.analyze_uploaded_file(
                    file_path=combined_path,
                    source_type=source_type,
                    sample_size=sample_size,
                    original_filename=file_name
                )
                
                logger.info(f"Chunked анализ завершен для файла {file_name}")
                
                persisted_path = None
                if persist:
                    # Сохраняем собранный файл в общий каталог для Airflow
                    safe_name = os.path.basename(file_name)
                    uploads_dir = '/opt/airflow/data/uploads'
                    os.makedirs(uploads_dir, exist_ok=True)
                    persisted_path = os.path.join(uploads_dir, safe_name)
                    try:
                        import shutil
                        shutil.copy2(combined_path, persisted_path)
                        logger.info(f"Файл сохранен для деплоя: {persisted_path}")
                    except Exception as save_err:
                        logger.warning(f"Не удалось сохранить файл в общий каталог: {save_err}")
                        persisted_path = None
                
                return Response({
                    'status': 'success',
                    'analysis_result': result,
                    'file_info': {
                        'name': file_name,
                        'size': file_size,
                        'processed_size': total_size,
                        'source_type': source_type,
                        'sample_size': sample_size,
                        'chunks_processed': len(chunks_info),
                        'persisted_path': persisted_path
                    }
                })
                
            finally:
                # Очищаем временные файлы
                try:
                    os.unlink(combined_path)
                    logger.info(f"Удален объединенный файл: {combined_path}")
                except:
                    pass
                
                # Очищаем директорию с чанками
                try:
                    import shutil
                    shutil.rmtree(upload_dir)
                    logger.info(f"Удалена директория чанков: {upload_dir}")
                except:
                    pass
                    
        except Exception as e:
            logger.exception(f"Ошибка финализации chunked upload: {e}")
            return Response({
                'error': f'Ошибка обработки загрузки: {str(e)}',
                'status': 'failed'
            }, status=500)

# /api/v1/cleanup_upload
class CleanupUploadView(APIView):
    """
    Endpoint для очистки неудачных загрузок
    """
    def delete(self, request):
        """Очищает временные данные неудачной загрузки"""
        import os
        import logging
        import shutil
        from django.conf import settings
        
        logger = logging.getLogger(__name__)
        
        try:
            upload_id = request.data.get('upload_id')
            if not upload_id:
                return Response({
                    'error': 'upload_id не указан',
                    'status': 'failed'
                }, status=400)
            
            upload_dir = os.path.join(settings.FILE_UPLOAD_TEMP_DIR or '/tmp', 'chunked_uploads', upload_id)
            
            if os.path.exists(upload_dir):
                shutil.rmtree(upload_dir)
            logger.info(f"Очищена директория неудачной загрузки: {upload_id}")
            
            return Response({
                'status': 'success',
                'message': f'Данные загрузки {upload_id} очищены'
            })
            
        except Exception as e:
            logger.exception(f"Ошибка очистки загрузки: {e}")
            return Response({
                'error': f'Ошибка очистки: {str(e)}',
                'status': 'failed'
            }, status=500)