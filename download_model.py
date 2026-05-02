from sentence_transformers import SentenceTransformer
import os

model_name = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
# Save to a path that will be copied to the final image
save_path = "/app/model_cache"

print(f"Pre-downloading {model_name}...")
model = SentenceTransformer(model_name)
model.save(save_path)
print("Model saved to /app/model_cache")