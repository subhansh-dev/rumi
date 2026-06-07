"""DrugBank - Drug and drug target database (public subset via PubChem)."""

def search_drug_targets(drug_name):
    try:
        from discovery.pubchem import search_compound, get_targets
        result = search_compound(drug_name)
        if result:
            targets = get_targets(drug_name)
            return {"drug": drug_name, "targets": targets, "source": "drugbank_via_pubchem"}
    except Exception:
        pass
    return None

def enrich_entities(graph): return 0
