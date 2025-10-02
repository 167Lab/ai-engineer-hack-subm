#!/usr/bin/env python
"""
Скрипт для локального тестирования МАС без фронтенда
Использование: python test_mas.py
"""

import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime

# Добавляем путь к backend в sys.path
backend_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_path))

# Настраиваем Django
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from apps.agents.integration import MASIntegration


def create_test_csv_data():
    """Создание тестового CSV файла"""
    import pandas as pd
    import numpy as np
    
    # Генерируем тестовые данные
    np.random.seed(42)
    
    data = {
        'order_id': range(1, 1001),
        'customer_id': np.random.randint(1, 101, 1000),
        'order_date': pd.date_range('2024-01-01', periods=1000, freq='h'),
        'product_id': np.random.randint(1, 51, 1000),
        'quantity': np.random.randint(1, 10, 1000),
        'price': np.random.uniform(10.0, 1000.0, 1000).round(2),
        'status': np.random.choice(['pending', 'processing', 'completed', 'cancelled'], 1000),
        'payment_method': np.random.choice(['card', 'cash', 'transfer'], 1000),
        'shipping_city': np.random.choice(['Moscow', 'St.Petersburg', 'Novosibirsk', 'Yekaterinburg'], 1000),
        'discount': np.random.uniform(0, 0.3, 1000).round(2)
    }
    
    df = pd.DataFrame(data)
    df['total_amount'] = (df['quantity'] * df['price'] * (1 - df['discount'])).round(2)
    
    # Добавляем некоторые null значения
    df.loc[np.random.choice(df.index, 50, replace=False), 'discount'] = np.nan
    df.loc[np.random.choice(df.index, 20, replace=False), 'shipping_city'] = np.nan
    
    # Сохраняем в CSV
    csv_path = '/tmp/test_orders.csv'
    df.to_csv(csv_path, index=False)
    
    print(f"✅ Создан тестовый файл: {csv_path}")
    print(f"   Размер: {len(df)} строк, {len(df.columns)} колонок")
    
    return csv_path, df.to_csv(index=False)


async def test_csv_analysis():
    """Тест анализа CSV файла"""
    print("\n" + "="*60)
    print("🧪 ТЕСТ 1: Анализ CSV файла")
    print("="*60)
    
    # Создаем тестовые данные
    csv_path, csv_content = create_test_csv_data()
    
    # Подготавливаем запрос
    request_data = {
        'source_type': 'csv',
        'connection_params': {
            'file_path': csv_path,
            'file_content': csv_content,
            'is_uploaded': True
        }
    }
    
    print("\n📋 Параметры запроса:")
    print(f"   Тип источника: {request_data['source_type']}")
    print(f"   Путь к файлу: {csv_path}")
    
    # Создаем экземпляр МАС
    mas = MASIntegration()
    
    print("\n🚀 Запуск анализа...")
    print("   (Это может занять несколько минут)")
    
    try:
        # Запускаем анализ
        result = await mas.analyze_data_source(request_data)
        
        # Выводим результаты
        print("\n✅ Анализ завершен!")
        print("\n📊 Результаты анализа:")
        print("-" * 40)
        
        if result.get('status') == 'success':
            analysis = result.get('analysis_result', {})
            
            # Рекомендация по хранилищу
            print(f"\n🗄️  Рекомендованное хранилище: {analysis.get('storage_recommendation', 'Не определено')}")
            print(f"   Обоснование: {analysis.get('storage_reasoning', 'Не указано')}")
            
            # Альтернативы
            if analysis.get('storage_alternatives'):
                print("\n   Альтернативные варианты:")
                for alt in analysis['storage_alternatives'][:3]:
                    print(f"   - {alt.get('storage', '')}: {alt.get('reason', '')}")
            
            # DDL скрипты
            ddl_scripts = result.get('ddl_scripts', [])
            if ddl_scripts:
                print(f"\n📝 Сгенерировано DDL скриптов: {len(ddl_scripts)}")
                for script in ddl_scripts[:2]:
                    print(f"   - {script.get('type', '')}: {script.get('name', '')}")
            
            # Пайплайн
            pipeline_config = result.get('pipeline_config', {})
            if pipeline_config:
                print(f"\n🔄 Конфигурация пайплайна:")
                print(f"   DAG ID: {pipeline_config.get('dag_id', 'Не указан')}")
                print(f"   Расписание: {pipeline_config.get('schedule', 'Не указано')}")
            
            # Ошибки и предупреждения
            errors = result.get('errors', [])
            warnings = result.get('warnings', [])
            
            if errors:
                print(f"\n⚠️  Ошибки ({len(errors)}):")
                for error in errors[:3]:
                    print(f"   - {error.get('agent', '')}: {error.get('error', '')[:100]}")
            
            if warnings:
                print(f"\n⚡ Предупреждения ({len(warnings)}):")
                for warning in warnings[:3]:
                    print(f"   - {warning}")
            
            # Сохраняем отчет
            if result.get('report'):
                report_path = f"/tmp/mas_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
                with open(report_path, 'w', encoding='utf-8') as f:
                    f.write(result['report'])
                print(f"\n📄 Полный отчет сохранен: {report_path}")
            
            # Сохраняем пайплайн
            if result.get('pipeline_code'):
                dag_path = f"/tmp/mas_dag_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py"
                with open(dag_path, 'w', encoding='utf-8') as f:
                    f.write(result['pipeline_code'])
                print(f"🔧 Код пайплайна сохранен: {dag_path}")
            
        else:
            print(f"\n❌ Статус: {result.get('status', 'unknown')}")
            print(f"   Ошибка: {result.get('error', 'Неизвестная ошибка')}")
        
    except Exception as e:
        print(f"\n❌ Ошибка выполнения: {e}")
        import traceback
        traceback.print_exc()


async def test_interactive_mode():
    """Тест интерактивного режима с обратной связью"""
    print("\n" + "="*60)
    print("🧪 ТЕСТ 2: Интерактивный режим")
    print("="*60)
    
    # Создаем тестовые данные
    csv_path, csv_content = create_test_csv_data()
    
    request_data = {
        'source_type': 'csv',
        'connection_params': {
            'file_path': csv_path,
            'file_content': csv_content,
            'is_uploaded': True
        }
    }
    
    mas = MASIntegration()
    
    print("\n🚀 Запуск интерактивного анализа...")
    
    try:
        # Этап 1: Анализ данных
        print("\n📊 Этап 1: Анализ источника данных")
        result1 = await mas.analyze_with_feedback(request_data)
        
        if result1.get('status') == 'waiting_for_feedback':
            print("   ⏸️  Ожидание обратной связи...")
            print(f"   Рекомендация: {result1.get('data', {}).get('storage_recommendation', 'Не определено')}")
            
            # Симулируем обратную связь - меняем хранилище
            feedback_data = {
                'user_feedback': {
                    'stage': 'input_analysis',
                    'storage_override': 'clickhouse',
                    'reason': 'Планируется аналитическая нагрузка'
                }
            }
            
            print("\n   ✏️  Применяем корректировку: меняем хранилище на ClickHouse")
            
            # Продолжаем с обратной связью
            session_id = result1.get('session_id')
            result2 = await mas.analyze_with_feedback(feedback_data, session_id)
            
            print(f"   Новый статус: {result2.get('status', 'unknown')}")
            print(f"   Текущий этап: {result2.get('current_stage', 'unknown')}")
        
        print("\n✅ Интерактивный тест завершен")
        
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()


async def test_error_handling():
    """Тест обработки ошибок"""
    print("\n" + "="*60)
    print("🧪 ТЕСТ 3: Обработка ошибок")
    print("="*60)
    
    # Некорректные данные
    request_data = {
        'source_type': 'unknown_type',
        'connection_params': {}
    }
    
    mas = MASIntegration()
    
    print("\n🚀 Запуск с некорректными данными...")
    
    try:
        result = await mas.analyze_data_source(request_data)
        
        if result.get('status') == 'error':
            print(f"\n✅ Ошибка обработана корректно:")
            print(f"   Сообщение: {result.get('error', 'Не указано')}")
        else:
            print(f"\n⚠️  Неожиданный результат: {result.get('status', 'unknown')}")
        
    except Exception as e:
        print(f"\n❌ Необработанная ошибка: {e}")


async def main():
    """Главная функция тестирования"""
    print("\n" + "🔬 МАС - ЛОКАЛЬНОЕ ТЕСТИРОВАНИЕ " + "🔬")
    print("="*60)
    print(f"Время запуска: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Backend путь: {backend_path}")
    
    # Проверяем доступность Ollama
    print("\n🔍 Проверка окружения...")
    
    try:
        import ollama
        client = ollama.Client(host='http://localhost:11434')
        models = client.list()
        print(f"   ✅ Ollama доступна, моделей: {len(models.get('models', []))}")
        for model in models.get('models', [])[:3]:
            print(f"      - {model.get('name', 'unknown')}")
    except Exception as e:
        print(f"   ⚠️  Ollama недоступна: {e}")
        print("   Будут использоваться заглушки или облачные модели")
    
    # Выбор теста
    print("\n📋 Доступные тесты:")
    print("   1. Анализ CSV файла (полный цикл)")
    print("   2. Интерактивный режим")
    print("   3. Обработка ошибок")
    print("   4. Все тесты")
    
    choice = input("\n🔢 Выберите тест (1-4): ").strip()
    
    if choice == '1':
        await test_csv_analysis()
    elif choice == '2':
        await test_interactive_mode()
    elif choice == '3':
        await test_error_handling()
    elif choice == '4':
        await test_csv_analysis()
        await test_interactive_mode()
        await test_error_handling()
    else:
        print("❌ Некорректный выбор")
    
    print("\n" + "="*60)
    print("✅ ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")
    print("="*60)


if __name__ == "__main__":
    # Запускаем асинхронную главную функцию
    asyncio.run(main())
