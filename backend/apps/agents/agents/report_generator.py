"""
Агент генерации отчетов
"""
import json
import logging
from typing import Dict, Any, List
from datetime import datetime
from langchain_core.messages import HumanMessage, AIMessage

from ..core.agent_executor import AgentExecutor
from ..core.state import MASState

logger = logging.getLogger(__name__)


class ReportGeneratorAgent(AgentExecutor):
    """
    Агент для генерации финального отчета о проделанной работе
    """
    
    def __init__(self, **kwargs):
        super().__init__(agent_name='report_generation', **kwargs)
        
    def execute(self, state: MASState) -> MASState:
        """
        Генерация отчета о проделанной работе
        
        Args:
            state: Текущее состояние МАС
            
        Returns:
            Обновленное состояние с отчетом
        """
        logger.info("Начало генерации отчета")
        
        try:
            # Собираем всю информацию из состояния
            report_data = self._collect_report_data(state)
            
            # Подготавливаем контекст для LLM
            context = self._prepare_report_context(report_data)
            
            # Вызываем LLM для генерации отчета
            messages = [
                HumanMessage(content=f"""
Создай подробный технический отчет о выполненном анализе и настройке ETL пайплайна.

Данные для отчета:
{context}

Структура отчета должна включать:
1. **Резюме** - краткое описание выполненной работы
2. **Анализ источника данных** - характеристики и особенности
3. **Выбор хранилища** - обоснование и альтернативы
4. **Структура данных** - DDL скрипты и оптимизации
5. **ETL пайплайн** - описание процессов и трансформаций
6. **Рекомендации** - советы по оптимизации и масштабированию
7. **Потенциальные проблемы** - на что обратить внимание
8. **Заключение** - итоги и следующие шаги

Формат: Markdown
Язык: Русский
Стиль: Технический, но понятный
""")
            ]
            
            response = self.llm_manager.invoke_with_retry(self.llm, messages)
            
            # Генерируем финальный отчет
            report = self._format_report(response.content, report_data)
            
            # Сохраняем отчет в состоянии
            state['report'] = report
            state['report_sections'] = self._extract_report_sections(report)
            
            # Добавляем статистику выполнения
            state['execution_stats'] = {
                'total_agents_run': len(state.get('completed_agents', [])),
                'errors_count': len(state.get('errors', [])),
                'warnings_count': len(state.get('warnings', [])),
                'execution_time': self._calculate_execution_time(state)
            }
            
            # Добавляем сообщение в историю
            if 'messages' not in state:
                state['messages'] = []
            
            state['messages'].append(AIMessage(content=f"""
Отчет успешно сгенерирован.
Разделов: {len(state['report_sections'])}
Общий размер: {len(report)} символов
"""))
            
            # Обновляем информацию об агенте
            state['current_agent'] = self.agent_name
            state['end_time'] = datetime.now().isoformat()
            
            if 'completed_agents' not in state:
                state['completed_agents'] = []
            
            if self.agent_name not in state['completed_agents']:
                state['completed_agents'].append(self.agent_name)
            
            logger.info("Отчет успешно сгенерирован")
            
            # Сохраняем финальные результаты
            self._save_final_report(state)
            
            return state
            
        except Exception as e:
            logger.error(f"Ошибка генерации отчета: {e}")
            
            if 'errors' not in state:
                state['errors'] = []
            
            state['errors'].append({
                'agent': self.agent_name,
                'error': str(e),
                'stage': 'report_generation'
            })
            
            # Генерируем базовый отчет
            state['report'] = self._generate_fallback_report(state)
            
            return state
    
    def _collect_report_data(self, state: MASState) -> Dict[str, Any]:
        """
        Сбор всех данных для отчета из состояния
        """
        return {
            'source': {
                'type': state.get('source_config', {}).get('source_type', 'unknown'),
                'metadata': state.get('source_metadata', {}),
                'profile': state.get('data_profile', {})
            },
            'storage': {
                'recommendation': state.get('storage_recommendation', 'unknown'),
                'reasoning': state.get('storage_reasoning', ''),
                'alternatives': state.get('storage_alternatives', [])
            },
            'ddl': {
                'scripts': state.get('ddl_scripts', []),
                'recommendations': state.get('ddl_recommendations', {})
            },
            'pipeline': {
                'config': state.get('pipeline_config', {}),
                'transformations': state.get('transformations', []),
                'code_generated': bool(state.get('pipeline_code'))
            },
            'execution': {
                'completed_agents': state.get('completed_agents', []),
                'errors': state.get('errors', []),
                'warnings': state.get('warnings', []),
                'start_time': state.get('start_time', ''),
                'execution_id': state.get('execution_id', '')
            }
        }
    
    def _prepare_report_context(self, report_data: Dict[str, Any]) -> str:
        """
        Подготовка контекста для генерации отчета
        """
        context_parts = []
        
        # Источник данных
        source = report_data['source']
        context_parts.append(f"Источник данных: {source['type']}")
        
        if source['metadata']:
            meta = source['metadata']
            context_parts.append(f"- Колонок: {meta.get('column_count', 0)}")
            context_parts.append(f"- Строк (образец): {meta.get('row_count', 0)}")
            
            if meta.get('statistics'):
                stats = meta['statistics']
                context_parts.append(f"- Nulls: {stats.get('total_nulls', 0)}")
                context_parts.append(f"- Дубликаты: {stats.get('duplicated_rows', 0)}")
        
        # Хранилище
        storage = report_data['storage']
        context_parts.append(f"\nВыбранное хранилище: {storage['recommendation']}")
        context_parts.append(f"Обоснование: {storage['reasoning']}")
        
        if storage['alternatives']:
            context_parts.append("Альтернативы:")
            for alt in storage['alternatives']:
                context_parts.append(f"- {alt.get('storage', '')}: {alt.get('reason', '')}")
        
        # DDL
        ddl = report_data['ddl']
        if ddl['scripts']:
            context_parts.append(f"\nDDL скриптов сгенерировано: {len(ddl['scripts'])}")
            for script in ddl['scripts']:
                context_parts.append(f"- {script.get('type', '')}: {script.get('name', '')}")
        
        # Пайплайн
        pipeline = report_data['pipeline']
        if pipeline['config']:
            config = pipeline['config']
            context_parts.append(f"\nПайплайн: {config.get('dag_id', 'unknown')}")
            context_parts.append(f"- Расписание: {config.get('schedule', 'unknown')}")
            context_parts.append(f"- Трансформации: {', '.join(pipeline['transformations'][:5])}")
        
        # Ошибки и предупреждения
        execution = report_data['execution']
        if execution['errors']:
            context_parts.append(f"\nОбнаружено ошибок: {len(execution['errors'])}")
            for error in execution['errors'][:3]:
                context_parts.append(f"- {error.get('agent', '')}: {error.get('error', '')[:100]}")
        
        return "\n".join(context_parts)
    
    def _format_report(self, llm_response: str, report_data: Dict[str, Any]) -> str:
        """
        Форматирование финального отчета
        """
        # Если LLM вернула хороший отчет, используем его
        if len(llm_response) > 500 and '#' in llm_response:
            report = llm_response
        else:
            # Иначе генерируем структурированный отчет
            report = self._generate_structured_report(report_data)
        
        # Добавляем метаданные
        header = f"""---
title: Отчет о настройке ETL пайплайна
date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
execution_id: {report_data['execution'].get('execution_id', 'unknown')}
---

"""
        
        return header + report
    
    def _generate_structured_report(self, report_data: Dict[str, Any]) -> str:
        """
        Генерация структурированного отчета
        """
        source = report_data['source']
        storage = report_data['storage']
        ddl = report_data['ddl']
        pipeline = report_data['pipeline']
        execution = report_data['execution']
        
        report = f"""# Отчет о настройке ETL пайплайна

## 1. Резюме

Выполнен комплексный анализ источника данных типа **{source['type']}** и настроен ETL пайплайн для загрузки в **{storage['recommendation']}**.

**Ключевые результаты:**
- ✅ Проанализирована структура данных
- ✅ Выбрано оптимальное хранилище
- ✅ Сгенерированы DDL скрипты
- ✅ Создан Airflow DAG для автоматизации

## 2. Анализ источника данных

**Тип источника:** {source['type']}

**Характеристики данных:**
"""
        
        if source['metadata']:
            meta = source['metadata']
            report += f"""
- Количество колонок: {meta.get('column_count', 0)}
- Количество строк (образец): {meta.get('row_count', 0)}
"""
            
            if meta.get('statistics'):
                stats = meta['statistics']
                report += f"""
- Общее количество null значений: {stats.get('total_nulls', 0)}
- Дублированные строки: {stats.get('duplicated_rows', 0)}
- Использование памяти: {stats.get('memory_usage', 0):,} байт
"""
        
        if source['profile'] and source['profile'].get('data_characteristics'):
            chars = source['profile']['data_characteristics']
            report += f"""
**Особенности данных:**
- Временные данные: {'✓' if chars.get('has_temporal_data') else '✗'}
- Преимущественно числовые: {'✓' if chars.get('mostly_numeric') else '✗'}
- Текстовые данные: {'✓' if chars.get('has_text_data') else '✗'}
"""
        
        report += f"""
## 3. Выбор хранилища

**Рекомендованное хранилище:** {storage['recommendation']}

**Обоснование:** {storage['reasoning']}
"""
        
        if storage['alternatives']:
            report += "\n**Альтернативные варианты:**\n"
            for alt in storage['alternatives']:
                report += f"- **{alt.get('storage', '')}**: {alt.get('reason', '')}\n"
        
        report += """
## 4. Структура данных (DDL)
"""
        
        if ddl['scripts']:
            report += f"\nСгенерировано **{len(ddl['scripts'])}** DDL скриптов:\n"
            for script in ddl['scripts']:
                report += f"- {script.get('type', '').title()}: `{script.get('name', '')}`\n"
            
            if ddl['recommendations'] and ddl['recommendations'].get('optimization_notes'):
                report += "\n**Рекомендации по оптимизации:**\n"
                for note in ddl['recommendations']['optimization_notes']:
                    report += f"- {note}\n"
        
        report += """
## 5. ETL пайплайн
"""
        
        if pipeline['config']:
            config = pipeline['config']
            report += f"""
**Конфигурация пайплайна:**
- DAG ID: `{config.get('dag_id', 'unknown')}`
- Расписание: `{config.get('schedule', 'unknown')}`
- Повторные попытки: {config.get('config', {}).get('retries', 0)}
- Задержка между попытками: {config.get('config', {}).get('retry_delay', 0)} мин
"""
        
        if pipeline['transformations']:
            report += "\n**Применяемые трансформации:**\n"
            for transform in pipeline['transformations']:
                report += f"- {transform}\n"
        
        report += """
## 6. Рекомендации

### Оптимизация производительности
- Настроить индексы для часто используемых колонок
- Рассмотреть партицирование для больших объемов данных
- Мониторить использование ресурсов

### Масштабирование
- При росте объемов данных рассмотреть миграцию на распределенные системы
- Настроить параллельную обработку в Airflow
- Использовать инкрементальную загрузку данных

## 7. Потенциальные проблемы
"""
        
        if execution['errors']:
            report += f"\n⚠️ **Обнаружено ошибок: {len(execution['errors'])}**\n"
            for error in execution['errors']:
                report += f"- {error.get('agent', '')}: {error.get('error', '')[:100]}...\n"
        else:
            report += """
- Проверить доступность источников данных
- Убедиться в наличии необходимых прав доступа
- Мониторить использование дискового пространства
"""
        
        report += f"""
## 8. Заключение

ETL пайплайн успешно настроен и готов к использованию. 

**Следующие шаги:**
1. Развернуть DAG в Airflow
2. Выполнить тестовый запуск
3. Настроить мониторинг и алерты
4. Документировать бизнес-логику трансформаций

---
*Отчет сгенерирован автоматически системой AI Data Engineer Assistant*
*Время выполнения: {self._calculate_execution_time(report_data)}*
"""
        
        return report
    
    def _extract_report_sections(self, report: str) -> Dict[str, str]:
        """
        Извлечение секций из отчета
        """
        sections = {}
        current_section = None
        current_content = []
        
        for line in report.split('\n'):
            if line.startswith('## '):
                if current_section:
                    sections[current_section] = '\n'.join(current_content)
                current_section = line[3:].strip()
                current_content = []
            elif current_section:
                current_content.append(line)
        
        if current_section:
            sections[current_section] = '\n'.join(current_content)
        
        return sections
    
    def _calculate_execution_time(self, data: Any) -> str:
        """
        Расчет времени выполнения
        """
        if isinstance(data, dict):
            start = data.get('execution', {}).get('start_time', '')
        else:
            start = data.get('start_time', '')
        
        if start:
            try:
                start_dt = datetime.fromisoformat(start)
                end_dt = datetime.now()
                delta = end_dt - start_dt
                
                if delta.total_seconds() < 60:
                    return f"{delta.total_seconds():.1f} сек"
                elif delta.total_seconds() < 3600:
                    return f"{delta.total_seconds() / 60:.1f} мин"
                else:
                    return f"{delta.total_seconds() / 3600:.1f} ч"
            except:
                pass
        
        return "неизвестно"
    
    def _save_final_report(self, state: MASState):
        """
        Сохранение финального отчета
        """
        if state.get('report'):
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            report_file = self.temp_dir / f"report_{timestamp}.md"
            
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(state['report'])
            
            logger.info(f"Отчет сохранен: {report_file}")
    
    def _generate_fallback_report(self, state: MASState) -> str:
        """
        Генерация отчета при ошибке
        """
        return f"""# Отчет о настройке ETL пайплайна

## Статус: Частично выполнено

Во время выполнения анализа произошли ошибки.

**Выполненные этапы:**
{', '.join(state.get('completed_agents', []))}

**Ошибки:**
{len(state.get('errors', []))} ошибок обнаружено

**Рекомендации:**
- Проверить входные данные
- Убедиться в доступности всех сервисов
- Обратиться к логам для детальной информации

---
*Отчет сгенерирован: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
