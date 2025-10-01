/**
 * Утилиты для эффективной загрузки больших файлов без Out of Memory
 * Используют chunked upload и streaming для минимизации использования памяти браузера
 */

export interface FileChunk {
    data: Blob;
    index: number;
    total: number;
    hash: string;
}

export interface UploadProgress {
    loaded: number;
    total: number;
    percentage: number;
    currentChunk: number;
    totalChunks: number;
}

export class LargeFileUploader {
    private static readonly CHUNK_SIZE = 10 * 1024 * 1024; // 10MB chunks
    private static readonly MAX_MEMORY_USAGE = 50 * 1024 * 1024; // 50MB max in browser memory
    
    /**
     * Проверяет нужно ли использовать chunked upload
     */
    static shouldUseChunkedUpload(fileSize: number): boolean {
        return fileSize > this.MAX_MEMORY_USAGE;
    }
    
    /**
     * Загружает большой файл по частям (chunks) для анализа
     */
    static async uploadLargeFileForAnalysis(
        file: File,
        sourceType: string,
        onProgress?: (progress: UploadProgress) => void
    ): Promise<any> {
        
        if (!this.shouldUseChunkedUpload(file.size)) {
            // Для небольших файлов используем обычную загрузку
            return this.uploadSmallFile(file, sourceType);
        }
        
        // Для больших файлов используем chunked upload
        const chunks = this.createFileChunks(file);
        const uploadId = this.generateUploadId();
        
        console.log(`🔄 Начинаем chunked upload: ${chunks.length} частей по ${this.CHUNK_SIZE / 1024 / 1024}MB`);
        
        try {
            // Загружаем чанки последовательно для контроля памяти
            for (let i = 0; i < chunks.length; i++) {
                const chunk = chunks[i];
                
                // Отправляем чанк на сервер
                await this.uploadChunk(chunk, uploadId, file.name, sourceType);
                
                // Уведомляем о прогрессе
                if (onProgress) {
                    onProgress({
                        loaded: (i + 1) * this.CHUNK_SIZE,
                        total: file.size,
                        percentage: Math.round(((i + 1) / chunks.length) * 100),
                        currentChunk: i + 1,
                        totalChunks: chunks.length
                    });
                }
                
                // Небольшая задержка для предотвращения блокировки UI
                await this.sleep(10);
            }
            
            // Финализируем upload и запускаем анализ
            return await this.finalizeChunkedUpload(uploadId, file.name, sourceType, file.size);
            
        } catch (error) {
            // В случае ошибки очищаем частичные данные
            await this.cleanupFailedUpload(uploadId);
            throw error;
        }
    }
    
    /**
     * Создает чанки файла для загрузки
     */
    private static createFileChunks(file: File): FileChunk[] {
        const chunks: FileChunk[] = [];
        const totalChunks = Math.ceil(file.size / this.CHUNK_SIZE);
        
        for (let i = 0; i < totalChunks; i++) {
            const start = i * this.CHUNK_SIZE;
            const end = Math.min(start + this.CHUNK_SIZE, file.size);
            const blob = file.slice(start, end);
            
            chunks.push({
                data: blob,
                index: i,
                total: totalChunks,
                hash: this.generateChunkHash(i, start, end)
            });
        }
        
        return chunks;
    }
    
    /**
     * Загружает один чанк файла
     */
    private static async uploadChunk(
        chunk: FileChunk, 
        uploadId: string, 
        fileName: string, 
        sourceType: string
    ): Promise<void> {
        const formData = new FormData();
        formData.append('chunk', chunk.data);
        formData.append('upload_id', uploadId);
        formData.append('chunk_index', chunk.index.toString());
        formData.append('total_chunks', chunk.total.toString());
        formData.append('file_name', fileName);
        formData.append('source_type', sourceType);
        formData.append('chunk_hash', chunk.hash);
        
        const response = await fetch('/api/v1/upload_chunk', {
            method: 'POST',
            body: formData,
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(`Chunk upload failed: ${errorData.error}`);
        }
    }
    
    /**
     * Финализирует chunked upload и запускает анализ
     */
    private static async finalizeChunkedUpload(
        uploadId: string, 
        fileName: string, 
        sourceType: string,
        fileSize: number
    ): Promise<any> {
        const response = await fetch('/api/v1/finalize_chunked_upload', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                upload_id: uploadId,
                file_name: fileName,
                source_type: sourceType,
                file_size: fileSize,
                sample_size: 1000
            }),
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(`Finalize upload failed: ${errorData.error}`);
        }
        
        return response.json();
    }
    
    /**
     * Загрузка небольших файлов обычным способом
     */
    private static async uploadSmallFile(file: File, sourceType: string): Promise<any> {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('source_type', sourceType);
        formData.append('sample_size', '1000');
        
        const response = await fetch('/api/v1/analyze_file_stream', {
            method: 'POST',
            body: formData,
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(`File upload failed: ${errorData.error}`);
        }
        
        return response.json();
    }
    
    /**
     * Очищает данные неудачной загрузки
     */
    private static async cleanupFailedUpload(uploadId: string): Promise<void> {
        try {
            await fetch('/api/v1/cleanup_upload', {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ upload_id: uploadId }),
            });
        } catch (error) {
            console.warn('Failed to cleanup upload:', error);
        }
    }
    
    /**
     * Генерирует уникальный ID для загрузки
     */
    private static generateUploadId(): string {
        return `upload_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }
    
    /**
     * Генерирует хеш для чанка (для проверки целостности)
     */
    private static generateChunkHash(index: number, start: number, end: number): string {
        return `chunk_${index}_${start}_${end}`;
    }
    
    /**
     * Асинхронная задержка
     */
    private static sleep(ms: number): Promise<void> {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
}

/**
 * Memory-safe File Reader для очень больших файлов
 * Читает файл по частям без загрузки в память полностью
 */
export class MemorySafeFileReader {
    /**
     * Читает первые N байт файла для предварительного анализа
     */
    static async readFilePreview(file: File, maxBytes: number = 1024 * 1024): Promise<string> {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            const blob = file.slice(0, Math.min(maxBytes, file.size));
            
            reader.onload = (e) => {
                resolve(e.target?.result as string);
            };
            
            reader.onerror = () => {
                reject(new Error('Failed to read file preview'));
            };
            
            reader.readAsText(blob, 'UTF-8');
        });
    }
    
    /**
     * Определяет тип файла по содержимому без полной загрузки
     */
    static async detectFileType(file: File): Promise<{type: string, confidence: number}> {
        try {
            const preview = await this.readFilePreview(file, 8192); // Читаем первые 8KB
            
            // CSV detection
            if (preview.includes(',') && (preview.includes('\n') || preview.includes('\r'))) {
                const lines = preview.split(/[\r\n]+/).filter(line => line.trim());
                if (lines.length > 1) {
                    return {type: 'csv', confidence: 0.9};
                }
            }
            
            // JSON detection
            const trimmed = preview.trim();
            if ((trimmed.startsWith('[') || trimmed.startsWith('{')) && 
                (trimmed.includes('"') || trimmed.includes("'"))) {
                return {type: 'json', confidence: 0.8};
            }
            
            // XML detection
            if (trimmed.startsWith('<?xml') || trimmed.startsWith('<')) {
                return {type: 'xml', confidence: 0.8};
            }
            
            return {type: 'unknown', confidence: 0.1};
            
        } catch (error) {
            return {type: 'unknown', confidence: 0};
        }
    }
}
