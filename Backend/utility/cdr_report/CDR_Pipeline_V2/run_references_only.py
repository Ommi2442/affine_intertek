import json
from form_utils import build_ref
from references import references_main
from utils import build_embeddings, build_vectorstore

def main():
    # Recreate ONLY vectorstore handle (no ingest)
    embeddings = build_embeddings()
    vs = build_vectorstore(embeddings)

    with open("iec_output.json", "r", encoding="utf-8") as f:
        trf_filled = json.load(f)

    ref = build_ref(trf_filled)
    print(ref)
    print("✅ Running references_main(vs, ref)...")
    template = references_main(vs, ref)
    print("✅ Done")

    # optional save if template is JSON-serializable
    # with open("references_output.json", "w", encoding="utf-8") as f:
    #     json.dump(template, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    main()
