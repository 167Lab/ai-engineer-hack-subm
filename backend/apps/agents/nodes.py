# Placeholder classes for agent nodes

from analyzers import DataSourceAnalyzer, DatabaseSourceAnalyzer
from apps.agents.llm_integration import OllamaIntegration

class AnalystNode:
    async def __call__(self, state: dict):
        print("AnalystNode called")
        
        source_type = state.get("source_data", {}).get("source_type")
        connection_params = state.get("source_data", {}).get("connection_params", {})
        
        analysis_result = {}
        error = None
        
        try:
            if source_type in ['csv', 'json', 'xml']:
                analyzer = DataSourceAnalyzer()
                
                # Проверяем тип источника файла
                is_uploaded = connection_params.get('is_uploaded', False)
                
                if is_uploaded:
                    # Анализируем загруженный файл
                    file_content = connection_params.get('file_content')
                    file_name = connection_params.get('file_name')
                    if not file_content or not file_name:
                        raise ValueError("Для загруженного файла требуются file_content и file_name")
                    analysis_result = await analyzer.analyze_file_source(
                        file_content=file_content,
                        file_name=file_name
                    )
                else:
                    # Анализируем файл по пути на сервере
                    file_path = connection_params.get('file_path')
                    if not file_path:
                        raise ValueError("Для серверного файла требуется file_path")
                    analysis_result = await analyzer.analyze_file_source(file_path=file_path)
            
            elif source_type == 'postgres':
                table_name = connection_params.get('table')
                if not table_name:
                    raise ValueError("`table` name is required for database sources.")
                db_analyzer = DatabaseSourceAnalyzer()
                analysis_result = await db_analyzer.analyze_postgres_table(connection_params, table_name)

            elif source_type == 'clickhouse':
                table_name = connection_params.get('table')
                if not table_name:
                    raise ValueError("`table` name is required for database sources.")
                db_analyzer = DatabaseSourceAnalyzer()
                analysis_result = await db_analyzer.analyze_clickhouse_table(connection_params, table_name)

            else:
                raise NotImplementedError(f"Source type '{source_type}' is not supported yet.")

            # Enhance with LLM
            ollama = OllamaIntegration()
            llm_recommendations = await ollama.analyze_data_structure(analysis_result)
            analysis_result['llm_recommendations'] = llm_recommendations

        except Exception as e:
            error = str(e)
            print(f"Error in AnalystNode: {e}")

        return {
            "analysis_result": analysis_result,
            "error": error
        }

class TechWriterNode:
    def __call__(self, inputs):
        print("TechWriterNode called")
        return {"report": "dummy report"}

class ReviewerNode:
    def __call__(self, inputs):
        print("ReviewerNode called")
        return {"reviewed_report": "dummy reviewed report"}
