import { TFile } from 'obsidian';

export interface VectorDocument {
    id: string;
    fileId: string;
    filePath: string;
    content: string;
    embedding: number[];
    chunkIndex: number;
    metadata: {
        modified: number;
        indexed: number;
    };
}

export interface FileIndex {
    fileId: string;
    filePath: string;
    modified: number;
    indexed: number;
    chunks: string[];
}

export class VectorStore {
    private dbName = 'obsidian-ollama-vectors';
    private dbVersion = 1;
    private db: IDBDatabase | null = null;

    async init(): Promise<void> {
        return new Promise((resolve, reject) => {
            const request = indexedDB.open(this.dbName, this.dbVersion);

            request.onerror = () => reject(request.error);
            request.onsuccess = () => {
                this.db = request.result;
                resolve();
            };

            request.onupgradeneeded = (event) => {
                const db = (event.target as IDBOpenDBRequest).result;
                
                // Store for vector documents
                if (!db.objectStoreNames.contains('vectors')) {
                    const vectorStore = db.createObjectStore('vectors', { keyPath: 'id' });
                    vectorStore.createIndex('fileId', 'fileId', { unique: false });
                    vectorStore.createIndex('filePath', 'filePath', { unique: false });
                }

                // Store for file metadata
                if (!db.objectStoreNames.contains('files')) {
                    const fileStore = db.createObjectStore('files', { keyPath: 'fileId' });
                    fileStore.createIndex('filePath', 'filePath', { unique: true });
                    fileStore.createIndex('modified', 'modified', { unique: false });
                }
            };
        });
    }

    async addDocument(doc: VectorDocument): Promise<void> {
        if (!this.db) throw new Error('Database not initialized');
        
        const transaction = this.db.transaction(['vectors'], 'readwrite');
        const store = transaction.objectStore('vectors');
        
        return new Promise((resolve, reject) => {
            const request = store.put(doc);
            request.onsuccess = () => resolve();
            request.onerror = () => reject(request.error);
        });
    }

    async addFileIndex(fileIndex: FileIndex): Promise<void> {
        if (!this.db) throw new Error('Database not initialized');
        
        const transaction = this.db.transaction(['files'], 'readwrite');
        const store = transaction.objectStore('files');
        
        return new Promise((resolve, reject) => {
            const request = store.put(fileIndex);
            request.onsuccess = () => resolve();
            request.onerror = () => reject(request.error);
        });
    }

    async getFileIndex(filePath: string): Promise<FileIndex | null> {
        if (!this.db) throw new Error('Database not initialized');
        
        const transaction = this.db.transaction(['files'], 'readonly');
        const store = transaction.objectStore('files');
        const index = store.index('filePath');
        
        return new Promise((resolve, reject) => {
            const request = index.get(filePath);
            request.onsuccess = () => resolve(request.result || null);
            request.onerror = () => reject(request.error);
        });
    }

    async needsReindex(file: TFile): Promise<boolean> {
        const fileIndex = await this.getFileIndex(file.path);
        if (!fileIndex) return true;
        return file.stat.mtime > fileIndex.modified;
    }

    async deleteFileVectors(fileId: string): Promise<void> {
        if (!this.db) throw new Error('Database not initialized');
        
        const transaction = this.db.transaction(['vectors'], 'readwrite');
        const store = transaction.objectStore('vectors');
        const index = store.index('fileId');
        
        const request = index.openCursor(IDBKeyRange.only(fileId));
        
        return new Promise((resolve, reject) => {
            request.onsuccess = (event) => {
                const cursor = (event.target as IDBRequest).result;
                if (cursor) {
                    cursor.delete();
                    cursor.continue();
                } else {
                    resolve();
                }
            };
            request.onerror = () => reject(request.error);
        });
    }

    async getAllDocuments(): Promise<VectorDocument[]> {
        if (!this.db) throw new Error('Database not initialized');
        
        const transaction = this.db.transaction(['vectors'], 'readonly');
        const store = transaction.objectStore('vectors');
        
        return new Promise((resolve, reject) => {
            const request = store.getAll();
            request.onsuccess = () => resolve(request.result);
            request.onerror = () => reject(request.error);
        });
    }

    async getStats(): Promise<{ totalDocs: number; totalFiles: number }> {
        if (!this.db) throw new Error('Database not initialized');
        
        const transaction = this.db.transaction(['vectors', 'files'], 'readonly');
        const vectorStore = transaction.objectStore('vectors');
        const fileStore = transaction.objectStore('files');
        
        const vectorCount = await new Promise<number>((resolve, reject) => {
            const request = vectorStore.count();
            request.onsuccess = () => resolve(request.result);
            request.onerror = () => reject(request.error);
        });

        const fileCount = await new Promise<number>((resolve, reject) => {
            const request = fileStore.count();
            request.onsuccess = () => resolve(request.result);
            request.onerror = () => reject(request.error);
        });

        return { totalDocs: vectorCount, totalFiles: fileCount };
    }

    async clear(): Promise<void> {
        if (!this.db) throw new Error('Database not initialized');
        
        const transaction = this.db.transaction(['vectors', 'files'], 'readwrite');
        
        await new Promise<void>((resolve, reject) => {
            const vectorClear = transaction.objectStore('vectors').clear();
            const fileClear = transaction.objectStore('files').clear();
            
            transaction.oncomplete = () => resolve();
            transaction.onerror = () => reject(transaction.error);
        });
    }
}