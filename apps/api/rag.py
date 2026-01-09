import json
import faiss
from sentence_transformers import SentenceTransformer
import torch
from transformers import pipeline
from accelerate import init_empty_weights, infer_auto_device_map
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

# Path to FAQ docs
FAQ_PATH = "/app/data/faq_docs.json"

# Embedding + Generator setup
embedder = SentenceTransformer("all-MiniLM-L6-v2")
#generator = pipeline("text2text-generation", model="google/flan-t5-small")
# generator = pipeline(
#     "text-generation",
#     model="mistralai/Mistral-7B-Instruct-v0.2",  <-- tooo arge a very bigger modle for the scope of our project about 7B parameters 
#     device_map="auto",
#     torch_dtype=torch.float16
# )

_generator = None
def get_generator():
    global _generator
    if _generator is None:
        # 1️⃣ Load tokenizer
        tokenizer = AutoTokenizer.from_pretrained("google/flan-t5-xl")

        # 2️⃣ Load model efficiently with accelerate
        # previous models tried 
        # google/flan-t5-xl <-- too large about 3 GB in size and takes long to load, 
        # google/flan-t5-large <-- large is taking over 30 secs to provide the response  
        model = AutoModelForSeq2SeqLM.from_pretrained(
            "google/flan-t5-small",        
            device_map="auto",          # auto assigns CPU/GPU
            offload_folder="offload",   # optional for CPU offloading
            offload_state_dict=True     # offload weights to CPU to save GPU memory
        )

         # 3️⃣ Create pipeline
        _generator = pipeline(
            "text2text-generation",
            model=model,
            tokenizer=tokenizer
        )

    return _generator

docs: list[str] = []
index = None

def load_faq_docs() -> None:
    """
    Load FAQ documents and build FAISS index.
    """
    global docs, index
    with open(FAQ_PATH, "r") as f:
        docs = json.load(f)

    embeddings = embedder.encode(docs)
    index = faiss.IndexFlatL2(embeddings.shape[1])
    index.add(embeddings)

def retrieve_docs(query: str, k: int = 4, threshold: float = 2.5) -> list[str]:
    """
    Retrieve top-k FAQ docs relevant to the query.
    """
    if not index:
        load_faq_docs()

    q_emb = embedder.encode([query])
    distances, indices = index.search(q_emb, k)

    results = []
    for dist, idx in zip(distances[0], indices[0]):
        if dist <= threshold:
            results.append(docs[idx])
    return results

# Load FAQ docs on startup
load_faq_docs()