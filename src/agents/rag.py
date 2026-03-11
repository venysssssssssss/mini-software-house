import os
import glob

# Soft dependency check for RAG
try:
    import chromadb
except ImportError:
    chromadb = None

class RAGEngine:
    def __init__(self, persist_directory="workspace/chroma_db"):
        self.enabled = chromadb is not None
        if self.enabled:
            self.client = chromadb.PersistentClient(path=persist_directory)
            self.collection = self.client.get_or_create_collection(name="project_codebase")
        else:
            print("Warning: chromadb not installed. RAG features disabled.")

    def index_workspace(self, workspace_dir="workspace"):
        if not self.enabled: return
        
        files_data = []
        metadatas = []
        ids = []

        for root, _, files in os.walk(workspace_dir):
            for file in files:
                if file.endswith((".py", ".md", ".txt")):
                    path = os.path.join(root, file)
                    with open(path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                        if content.strip():
                            files_data.append(content)
                            metadatas.append({"source": file, "path": path})
                            ids.append(path)
        
        if files_data:
            self.collection.upsert(
                documents=files_data,
                metadatas=metadatas,
                ids=ids
            )

    def query(self, query_text: str, n_results=3) -> str:
        if not self.enabled: return ""
        
        results = self.collection.query(
            query_texts=[query_text],
            n_results=n_results
        )
        
        context = ""
        for i, doc in enumerate(results['documents'][0]):
            meta = results['metadatas'][0][i]
            context += f"\n--- Reference from {meta['source']} ---\n{doc}\n"
        
        return context