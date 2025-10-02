# Мультиагентная система (МАС) для AI Data Engineer

## 📋 Описание

Мультиагентная система для автоматизации работы инженера данных, включающая:
- Анализ источников данных
- Выбор оптимального хранилища
- Генерацию DDL скриптов
- Создание Airflow пайплайнов
- Формирование отчетов

## 🏗️ Архитектура

```
backend/apps/agents/
├── config/                    # Конфигурация
│   ├── general_config.yaml   # Основные настройки
│   └── prompts/              # Промпты агентов
├── core/                      # Ядро системы
│   ├── state.py              # Определение состояния
│   ├── llm_manager.py        # Управление LLM
│   ├── agent_executor.py     # Базовый исполнитель
│   └── graph.py              # LangGraph граф
├── agents/                    # Реализация агентов
│   ├── input_analyzer.py     # Анализ данных
│   ├── ddl_generator.py      # Генерация DDL
│   ├── pipeline_generator.py # Создание пайплайнов
│   └── report_generator.py   # Генерация отчетов
├── tools/                     # Инструменты
│   ├── data_tools.py         # Работа с данными
│   └── db_tools.py           # Работа с БД
└── integration.py            # Интеграция с API
```

## 🚀 Быстрый старт

### 1. Установка зависимостей

```bash
cd backend
pip install -r requirements.txt

# Дополнительные зависимости для МАС
pip install langchain langgraph langchain-ollama langchain-groq
```

### 2. Настройка Ollama (для локальных моделей)

```bash
# Установка Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Загрузка моделей
ollama pull llama3.2
ollama pull qwen2.5:14b

# Проверка
ollama list
```

### 3. Конфигурация

Отредактируйте `backend/apps/agents/config/general_config.yaml`:

```yaml
llm_config:
  provider: "hybrid"  # ollama, openai, groq, hybrid
  
  ollama:
    enabled: true
    url: "http://localhost:11434"
    models:
      input_analysis: "qwen2.5:14b"
      ddl_generation: "llama3.2:latest"
```

Для облачных моделей установите переменные окружения:
```bash
export GROQ_API_KEY="your_api_key"
export OPENAI_API_KEY="your_api_key"
```

### 4. Тестирование

```bash
cd backend/apps/agents
python test_mas.py
```

## 💻 Использование

### Через Django API

```python
from apps.agents.integration import MASIntegration

# Создание экземпляра МАС
mas = MASIntegration()

# Анализ источника данных
request_data = {
    'source_type': 'csv',
    'connection_params': {
        'file_path': '/path/to/data.csv'
    }
}

result = await mas.analyze_data_source(request_data)
```

### Интерактивный режим

```python
# Начало анализа
result = await mas.analyze_with_feedback(request_data)
session_id = result['session_id']

# Применение обратной связи
feedback = {
    'user_feedback': {
        'stage': 'input_analysis',
        'storage_override': 'clickhouse'
    }
}

result = await mas.analyze_with_feedback(feedback, session_id)
```

## 🔧 Поддерживаемые источники данных

- **Файлы**: CSV, JSON, XML
- **Базы данных**: PostgreSQL, ClickHouse
- **В разработке**: Kafka, HDFS, Spark

## 🗄️ Целевые хранилища

### PostgreSQL
- Транзакционные данные
- OLTP нагрузка
- Сложные связи между таблицами

### ClickHouse
- Аналитические данные
- Временные ряды
- OLAP нагрузка

### HDFS
- Большие объемы сырых данных
- Архивное хранение
- Data Lake сценарии

## 📊 Этапы работы МАС

1. **Анализ входных данных**
   - Извлечение метаданных
   - Профилирование данных
   - Рекомендация хранилища

2. **Генерация DDL**
   - Создание структуры таблиц
   - Оптимизация индексов
   - Партицирование

3. **Создание пайплайна**
   - Генерация Airflow DAG
   - Настройка трансформаций
   - Конфигурация расписания

4. **Формирование отчета**
   - Технический анализ
   - Рекомендации
   - Документация

## 🔍 Мониторинг и логи

Логи сохраняются в:
- `/backend/apps/agents/logs/` - логи агентов
- `/tmp/mas_temp/` - промежуточные результаты
- `/tmp/mas_sessions/` - сессии интерактивного режима

## ⚙️ Настройка промптов

Промпты агентов находятся в `config/prompts/`:
- `input_analysis_prompt.yaml` - анализ данных
- `ddl_generation_prompt.yaml` - генерация DDL
- `pipeline_generation_prompt.yaml` - создание пайплайнов
- `report_generation_prompt.yaml` - генерация отчетов

## 🐛 Отладка

Включить подробное логирование:
```yaml
agents_config:
  verbose: true
  save_intermediate: true
```

Проверка работы LLM:
```python
from apps.agents.core import LLMManager

manager = LLMManager()
llm = manager.get_llm('input_analysis')
response = llm.invoke("Test message")
```

## 📝 Требования

- Python 3.8+
- Django 4.2+
- LangChain 0.1+
- LangGraph 0.0.20+
- Pandas, NumPy
- Ollama (для локальных моделей)

## 🤝 Интеграция с фронтендом

МАС готова к интеграции через Django REST API:

```python
# views.py
from apps.agents.integration import MASIntegration

class AnalyzeDataSourceView(APIView):
    def post(self, request):
        mas = MASIntegration()
        result = asyncio.run(
            mas.analyze_data_source(request.data)
        )
        return Response(result)
```

## 📚 Дополнительная документация

- [LangGraph документация](https://langchain-ai.github.io/langgraph/)
- [Ollama руководство](https://ollama.com/docs)
- [Apache Airflow](https://airflow.apache.org/docs/)

## 🔮 Планы развития

- [ ] Поддержка Kafka и Spark
- [ ] Интеграция с Kubernetes
- [ ] Веб-интерфейс для настройки агентов
- [ ] Автоматическое тестирование пайплайнов
- [ ] Мониторинг качества данных

## 📧 Поддержка

При возникновении проблем:
1. Проверьте логи в `/backend/apps/agents/logs/`
2. Убедитесь, что Ollama запущена
3. Проверьте конфигурацию в `general_config.yaml`
4. Запустите тестовый скрипт `test_mas.py`
