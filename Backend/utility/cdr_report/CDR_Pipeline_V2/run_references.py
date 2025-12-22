import json
from configs import DB_NAME, CONT_NAME, cosmos_client
from utils import build_embeddings, build_vectorstore  # must point to same DB/CONT internally
from form_utils import build_ref
from references import references_main

def main():
    # 1) Recreate ONLY the handle to the existing vector store (no ingest)
    embeddings = build_embeddings()
    vs = build_vectorstore(embeddings)  # should connect to DB_NAME/CONT_NAME

    # Optional quick sanity check (won't modify DB)
    # print(vs.similarity_search("test", k=1))

    # 2) Build ref from your already generated TRF json
    with open("iec_output.json", "r", encoding="utf-8") as f:
        trf_filled = json.load(f)

    ref = build_ref(trf_filled)

    # 3) Run references
    out = references_main(vs, ref)
    print("✅ references_main finished")

    # If references_main returns something useful, you can save it:
    # with open("references_output.json", "w", encoding="utf-8") as f:
    #     json.dump(out, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    main()
