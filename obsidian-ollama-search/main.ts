import { App, Plugin, PluginSettingTab, Setting, Notice, TFile, Modal, TextComponent, ProgressBarComponent } from 'obsidian';
import { VectorStore, VectorDocument, FileIndex } from './vector-store';

interface OllamaSemanticSearchSettings {
    ollamaUrl: string;
    embeddingModel: string;
    chunkSize: number;
    chunkOverlap: number;
    autoIndex: boolean;
    indexOnStartup: boolean;
}

const DEFAULT_SETTINGS: OllamaSemanticSearchSettings = {
    ollamaUrl: 'http://localhost:11434',
    embeddingModel: 'snowflake-arctic-embed2:latest',
    chunkSize: 1000,
    chunkOverlap: 200,
    autoIndex: true,
    indexOnStartup: false
}

export default class OllamaSemanticSearchPlugin extends Plugin {
    settings: OllamaSemanticSearchSettings;
    vectorStore: VectorStore;
    indexingInProgress = false;

    async onload() {
        await this.loadSettings();
        
        // Initialize vector store
        this.vectorStore = new VectorStore();
        await this.vectorStore.init();

        // Add ribbon icon for quick search
        this.addRibbonIcon('search', 'Semantic search', () => {
            this.openSearchModal();
        });

        this.addCommand({
            id: 'index-vault',
            name: 'Index vault for semantic search',
            callback: () => this.indexVault()
        });

        this.addCommand({
            id: 'semantic-search',
            name: 'Semantic search',
            callback: () => this.openSearchModal()
        });

        this.addCommand({
            id: 'clear-index',
            name: 'Clear semantic search index',
            callback: async () => {
                await this.vectorStore.clear();
                new Notice('Search index cleared');
            }
        });

        this.addCommand({
            id: 'index-stats',
            name: 'Show index statistics',
            callback: async () => {
                const stats = await this.vectorStore.getStats();
                new Notice(`Indexed: ${stats.totalFiles} files, ${stats.totalDocs} chunks`);
            }
        });

        this.addSettingTab(new OllamaSemanticSearchSettingTab(this.app, this));

        // Watch for file changes
        if (this.settings.autoIndex) {
            this.registerEvent(
                this.app.vault.on('modify', async (file) => {
                    if (file instanceof TFile && file.extension === 'md') {
                        await this.indexFile(file, true);
                    }
                })
            );

            this.registerEvent(
                this.app.vault.on('delete', async (file) => {
                    if (file instanceof TFile && file.extension === 'md') {
                        const fileIndex = await this.vectorStore.getFileIndex(file.path);
                        if (fileIndex) {
                            await this.vectorStore.deleteFileVectors(fileIndex.fileId);
                        }
                    }
                })
            );
        }

        // Index on startup if enabled
        if (this.settings.indexOnStartup) {
            this.app.workspace.onLayoutReady(() => {
                this.indexVault(true);
            });
        }
    }

    async loadSettings() {
        this.settings = Object.assign({}, DEFAULT_SETTINGS, await this.loadData());
    }

    async saveSettings() {
        await this.saveData(this.settings);
    }

    async getEmbedding(text: string): Promise<number[]> {
        try {
            const response = await fetch(`${this.settings.ollamaUrl}/api/embeddings`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    model: this.settings.embeddingModel,
                    prompt: text
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            return data.embedding;
        } catch (error) {
            console.error('Error getting embedding:', error);
            throw error;
        }
    }

    chunkText(text: string): string[] {
        const chunks: string[] = [];
        const words = text.split(/\s+/);
        
        for (let i = 0; i < words.length; i += this.settings.chunkSize - this.settings.chunkOverlap) {
            const chunk = words.slice(i, i + this.settings.chunkSize).join(' ');
            if (chunk.trim().length > 0) {
                chunks.push(chunk);
            }
        }
        
        return chunks.length > 0 ? chunks : [text];
    }

    generateFileId(filePath: string): string {
        // Simple hash function for file ID
        let hash = 0;
        for (let i = 0; i < filePath.length; i++) {
            const char = filePath.charCodeAt(i);
            hash = ((hash << 5) - hash) + char;
            hash = hash & hash;
        }
        return Math.abs(hash).toString(36);
    }

    async indexFile(file: TFile, silent = false): Promise<void> {
        try {
            // Check if file needs reindexing
            const needsReindex = await this.vectorStore.needsReindex(file);
            if (!needsReindex && !silent) {
                return;
            }

            const content = await this.app.vault.read(file);
            const chunks = this.chunkText(content);
            const fileId = this.generateFileId(file.path);

            // Delete old vectors for this file
            await this.vectorStore.deleteFileVectors(fileId);

            // Create new vectors
            for (let i = 0; i < chunks.length; i++) {
                const embedding = await this.getEmbedding(chunks[i]);
                
                const doc: VectorDocument = {
                    id: `${fileId}-${i}`,
                    fileId: fileId,
                    filePath: file.path,
                    content: chunks[i],
                    embedding: embedding,
                    chunkIndex: i,
                    metadata: {
                        modified: file.stat.mtime,
                        indexed: Date.now()
                    }
                };

                await this.vectorStore.addDocument(doc);
            }

            // Update file index
            const fileIndex: FileIndex = {
                fileId: fileId,
                filePath: file.path,
                modified: file.stat.mtime,
                indexed: Date.now(),
                chunks: chunks.map((_, i) => `${fileId}-${i}`)
            };

            await this.vectorStore.addFileIndex(fileIndex);

            if (!silent) {
                console.log(`Indexed ${file.path} (${chunks.length} chunks)`);
            }
        } catch (error) {
            console.error(`Error indexing file ${file.path}:`, error);
            if (!silent) {
                new Notice(`Error indexing ${file.name}: ${error.message}`);
            }
        }
    }

    async indexVault(silent = false) {
        if (this.indexingInProgress) {
            new Notice('Indexing already in progress');
            return;
        }

        this.indexingInProgress = true;
        const progressModal = silent ? null : new IndexingProgressModal(this.app);
        
        try {
            if (progressModal) progressModal.open();
            
            const files = this.app.vault.getMarkdownFiles();
            let indexed = 0;
            let skipped = 0;

            for (const file of files) {
                const needsReindex = await this.vectorStore.needsReindex(file);
                
                if (needsReindex) {
                    if (progressModal) {
                        progressModal.updateProgress(indexed + skipped, files.length, `Indexing: ${file.name}`);
                    }
                    await this.indexFile(file, true);
                    indexed++;
                } else {
                    skipped++;
                }
            }

            if (progressModal) progressModal.close();
            
            const stats = await this.vectorStore.getStats();
            if (!silent) {
                new Notice(`Indexing complete! Indexed ${indexed} files (${skipped} unchanged). Total: ${stats.totalFiles} files, ${stats.totalDocs} chunks`);
            }
        } catch (error) {
            if (progressModal) progressModal.close();
            new Notice(`Indexing error: ${error.message}`);
        } finally {
            this.indexingInProgress = false;
        }
    }

    cosineSimilarity(a: number[], b: number[]): number {
        let dotProduct = 0;
        let normA = 0;
        let normB = 0;
        
        for (let i = 0; i < a.length; i++) {
            dotProduct += a[i] * b[i];
            normA += a[i] * a[i];
            normB += b[i] * b[i];
        }
        
        return dotProduct / (Math.sqrt(normA) * Math.sqrt(normB));
    }

    async search(query: string, topK: number = 10): Promise<Array<{document: VectorDocument, score: number}>> {
        const queryEmbedding = await this.getEmbedding(query);
        const allDocs = await this.vectorStore.getAllDocuments();
        
        const results: Array<{document: VectorDocument, score: number}> = [];

        for (const doc of allDocs) {
            const score = this.cosineSimilarity(queryEmbedding, doc.embedding);
            results.push({ document: doc, score });
        }

        results.sort((a, b) => b.score - a.score);
        
        // Deduplicate by file, keeping highest scoring chunk per file
        const seenFiles = new Set<string>();
        const deduped = results.filter(result => {
            if (seenFiles.has(result.document.filePath)) {
                return false;
            }
            seenFiles.add(result.document.filePath);
            return true;
        });

        return deduped.slice(0, topK);
    }

    openSearchModal() {
        new SearchModal(this.app, this).open();
    }
}

class IndexingProgressModal extends Modal {
    progressBar: ProgressBarComponent;
    statusText: HTMLElement;

    constructor(app: App) {
        super(app);
    }

    onOpen() {
        const { contentEl } = this;
        contentEl.empty();
        
        contentEl.createEl('h2', { text: 'Indexing Vault' });
        this.statusText = contentEl.createEl('p', { text: 'Starting...' });
        
        const progressContainer = contentEl.createDiv();
        progressContainer.style.marginTop = '20px';
        
        this.progressBar = new ProgressBarComponent(progressContainer);
        this.progressBar.setValue(0);
    }

    updateProgress(current: number, total: number, status: string) {
        const progress = (current / total) * 100;
        this.progressBar.setValue(progress);
        this.statusText.setText(`${status} (${current}/${total})`);
    }

    onClose() {
        const { contentEl } = this;
        contentEl.empty();
    }
}

class SearchModal extends Modal {
    plugin: OllamaSemanticSearchPlugin;
    searchInput: TextComponent;
    resultsEl: HTMLElement;
    searchTimeout: NodeJS.Timeout | null = null;

    constructor(app: App, plugin: OllamaSemanticSearchPlugin) {
        super(app);
        this.plugin = plugin;
    }

    onOpen() {
        const { contentEl } = this;
        contentEl.empty();

        contentEl.createEl('h2', { text: 'Semantic Search' });

        new Setting(contentEl)
            .setName('Search query')
            .addText(text => {
                this.searchInput = text;
                text.setPlaceholder('Enter your search query...');
                text.inputEl.style.width = '100%';
                
                // Search as you type with debouncing
                text.inputEl.addEventListener('input', () => {
                    if (this.searchTimeout) {
                        clearTimeout(this.searchTimeout);
                    }
                    
                    this.searchTimeout = setTimeout(() => {
                        if (text.getValue().length > 2) {
                            this.performSearch();
                        }
                    }, 500);
                });

                text.inputEl.addEventListener('keypress', async (e) => {
                    if (e.key === 'Enter') {
                        if (this.searchTimeout) {
                            clearTimeout(this.searchTimeout);
                        }
                        await this.performSearch();
                    }
                });
            });

        this.resultsEl = contentEl.createDiv('search-results');
        this.resultsEl.style.marginTop = '20px';
        this.resultsEl.style.maxHeight = '400px';
        this.resultsEl.style.overflowY = 'auto';

        // Show stats on open
        this.showStats();
    }

    async showStats() {
        const stats = await this.plugin.vectorStore.getStats();
        const statsEl = this.resultsEl.createEl('p', {
            text: `Search index: ${stats.totalFiles} files, ${stats.totalDocs} chunks`,
            cls: 'search-stats'
        });
        statsEl.style.color = 'var(--text-muted)';
        statsEl.style.fontSize = '0.9em';
    }

    async performSearch() {
        const query = this.searchInput.getValue();
        if (!query || query.length < 2) {
            this.resultsEl.empty();
            this.showStats();
            return;
        }

        this.resultsEl.empty();
        const loadingEl = this.resultsEl.createEl('p', { text: 'Searching...' });

        try {
            const results = await this.plugin.search(query);
            this.resultsEl.empty();

            if (results.length === 0) {
                this.resultsEl.createEl('p', { text: 'No results found.' });
            } else {
                results.forEach(({ document, score }) => {
                    const resultEl = this.resultsEl.createDiv('search-result');
                    resultEl.style.marginBottom = '15px';
                    resultEl.style.padding = '10px';
                    resultEl.style.border = '1px solid var(--background-modifier-border)';
                    resultEl.style.borderRadius = '5px';
                    resultEl.style.cursor = 'pointer';

                    resultEl.addEventListener('click', () => {
                        this.close();
                        this.app.workspace.openLinkText(document.filePath, '');
                    });

                    const titleEl = resultEl.createEl('h4');
                    titleEl.style.margin = '0 0 5px 0';
                    titleEl.setText(document.filePath.split('/').pop() || document.filePath);

                    const contentEl = resultEl.createEl('p');
                    contentEl.style.margin = '5px 0';
                    contentEl.style.fontSize = '0.9em';
                    contentEl.setText(document.content.substring(0, 200) + '...');
                    
                    const metaEl = resultEl.createEl('div');
                    metaEl.style.display = 'flex';
                    metaEl.style.justifyContent = 'space-between';
                    metaEl.style.fontSize = '0.8em';
                    metaEl.style.color = 'var(--text-muted)';
                    
                    metaEl.createEl('span', { 
                        text: `Similarity: ${(score * 100).toFixed(1)}%` 
                    });
                    
                    metaEl.createEl('span', { 
                        text: `Chunk ${document.chunkIndex + 1}` 
                    });
                });
            }
        } catch (error) {
            this.resultsEl.empty();
            this.resultsEl.createEl('p', { 
                text: `Error: ${error.message}`,
                cls: 'search-error'
            });
        }
    }

    onClose() {
        if (this.searchTimeout) {
            clearTimeout(this.searchTimeout);
        }
        const { contentEl } = this;
        contentEl.empty();
    }
}

class OllamaSemanticSearchSettingTab extends PluginSettingTab {
    plugin: OllamaSemanticSearchPlugin;

    constructor(app: App, plugin: OllamaSemanticSearchPlugin) {
        super(app, plugin);
        this.plugin = plugin;
    }

    display(): void {
        const { containerEl } = this;
        containerEl.empty();

        containerEl.createEl('h2', { text: 'Ollama Semantic Search Settings' });

        new Setting(containerEl)
            .setName('Ollama URL')
            .setDesc('URL of your Ollama instance')
            .addText(text => text
                .setPlaceholder('http://localhost:11434')
                .setValue(this.plugin.settings.ollamaUrl)
                .onChange(async (value) => {
                    this.plugin.settings.ollamaUrl = value;
                    await this.plugin.saveSettings();
                }));

        new Setting(containerEl)
            .setName('Embedding Model')
            .setDesc('Ollama model to use for embeddings')
            .addText(text => text
                .setPlaceholder('snowflake-arctic-embed2:latest')
                .setValue(this.plugin.settings.embeddingModel)
                .onChange(async (value) => {
                    this.plugin.settings.embeddingModel = value;
                    await this.plugin.saveSettings();
                }));

        new Setting(containerEl)
            .setName('Chunk Size')
            .setDesc('Number of words per chunk')
            .addText(text => text
                .setPlaceholder('1000')
                .setValue(String(this.plugin.settings.chunkSize))
                .onChange(async (value) => {
                    const num = parseInt(value);
                    if (!isNaN(num) && num > 0) {
                        this.plugin.settings.chunkSize = num;
                        await this.plugin.saveSettings();
                    }
                }));

        new Setting(containerEl)
            .setName('Chunk Overlap')
            .setDesc('Number of words to overlap between chunks')
            .addText(text => text
                .setPlaceholder('200')
                .setValue(String(this.plugin.settings.chunkOverlap))
                .onChange(async (value) => {
                    const num = parseInt(value);
                    if (!isNaN(num) && num >= 0) {
                        this.plugin.settings.chunkOverlap = num;
                        await this.plugin.saveSettings();
                    }
                }));

        new Setting(containerEl)
            .setName('Auto-index on file change')
            .setDesc('Automatically update index when files are modified')
            .addToggle(toggle => toggle
                .setValue(this.plugin.settings.autoIndex)
                .onChange(async (value) => {
                    this.plugin.settings.autoIndex = value;
                    await this.plugin.saveSettings();
                }));

        new Setting(containerEl)
            .setName('Index on startup')
            .setDesc('Automatically index new/changed files when Obsidian starts')
            .addToggle(toggle => toggle
                .setValue(this.plugin.settings.indexOnStartup)
                .onChange(async (value) => {
                    this.plugin.settings.indexOnStartup = value;
                    await this.plugin.saveSettings();
                }));

        containerEl.createEl('h3', { text: 'Index Management' });

        new Setting(containerEl)
            .setName('Reindex vault')
            .setDesc('Force reindex all files in the vault')
            .addButton(button => button
                .setButtonText('Reindex All')
                .onClick(async () => {
                    await this.plugin.vectorStore.clear();
                    await this.plugin.indexVault();
                }));

        new Setting(containerEl)
            .setName('Clear index')
            .setDesc('Remove all indexed data')
            .addButton(button => button
                .setButtonText('Clear Index')
                .setWarning()
                .onClick(async () => {
                    await this.plugin.vectorStore.clear();
                    new Notice('Search index cleared');
                }));
    }
}