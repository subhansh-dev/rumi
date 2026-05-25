"""Domain definitions for the Discovery Engine."""

DOMAINS = {
    "drug_discovery": {
        "label": "Drug Discovery",
        "description": "Drugs, diseases, genes, proteins, mechanisms — with PubChem + OpenFDA enrichment and molecule generation",
        "aliases": ["drug", "pharma", "medicine", "pharmaceutical"],
        "entity_types": {
            "drug":        {"color": "#4ade80", "description": "Chemical compound used for treatment"},
            "disease":     {"color": "#f87171", "description": "Medical condition or disorder"},
            "gene":        {"color": "#60a5fa", "description": "Genetic sequence or marker"},
            "protein":     {"color": "#a78bfa", "description": "Protein or enzyme"},
            "mechanism":   {"color": "#fb923c", "description": "Mechanism of action or biological process"},
            "pathway":     {"color": "#fbbf24", "description": "Biological signaling or metabolic pathway"},
            "cell_type":   {"color": "#34d399", "description": "Cell type or tissue"},
            "side_effect": {"color": "#e879f9", "description": "Adverse drug reaction"},
            "property":    {"color": "#fcd34d", "description": "Molecular property or attribute"},
        },
        "enrichment": ["pubchem", "openfda", "pdb", "semantic_scholar"],
        "generation": "molecule",
    },

    "materials_science": {
        "label": "Materials Science",
        "description": "Materials, compounds, properties, synthesis methods, applications — with PubChem + Materials Project enrichment",
        "aliases": ["materials", "material", "chemistry", "nanotech"],
        "entity_types": {
            "material":        {"color": "#ff6b6b", "description": "Engineered substance with specific properties"},
            "compound":        {"color": "#4ecdc4", "description": "Chemical compound or formulation"},
            "property":        {"color": "#fcd34d", "description": "Physical or chemical property"},
            "synthesis_method": {"color": "#45b7d1", "description": "Method of synthesis or fabrication"},
            "application":     {"color": "#96ceb4", "description": "Use case or application domain"},
            "element":         {"color": "#ffeaa7", "description": "Chemical element"},
        },
        "enrichment": ["pubchem", "materials_project", "semantic_scholar"],
        "generation": "material",
    },

    "neuroscience": {
        "label": "Neuroscience",
        "description": "Brain regions, neurotransmitters, disorders, genes, behaviors — with UniProt + PDB enrichment",
        "aliases": ["neuro", "neuroscience", "brain"],
        "entity_types": {
            "brain_region":     {"color": "#dda0dd", "description": "Specific brain area or nucleus"},
            "neurotransmitter": {"color": "#98fb98", "description": "Neurotransmitter or neuromodulator"},
            "disorder":         {"color": "#f08080", "description": "Neurological or psychiatric disorder"},
            "gene":             {"color": "#60a5fa", "description": "Gene associated with neural function"},
            "protein":          {"color": "#a78bfa", "description": "Neural protein or receptor"},
            "behavior":         {"color": "#ffd700", "description": "Behavioral phenotype or response"},
            "neuron_type":      {"color": "#20b2aa", "description": "Type of neuron"},
            "mechanism":        {"color": "#fb923c", "description": "Neural mechanism or process"},
        },
        "enrichment": ["uniprot", "pdb", "semantic_scholar"],
        "generation": "hypothesis",
    },

    "molecular_biology": {
        "label": "Molecular Biology",
        "description": "Genes, proteins, pathways, organisms, phenotypes — with UniProt + PDB enrichment",
        "aliases": ["molbio", "molecular", "biology", "genetics", "genomics"],
        "entity_types": {
            "gene":      {"color": "#60a5fa", "description": "Gene or genetic locus"},
            "protein":   {"color": "#a78bfa", "description": "Protein or enzyme"},
            "pathway":   {"color": "#fbbf24", "description": "Biological pathway"},
            "organism":  {"color": "#34d399", "description": "Model organism or species"},
            "phenotype": {"color": "#f87171", "description": "Observable trait or characteristic"},
            "cell_type": {"color": "#4ade80", "description": "Cell type or line"},
        },
        "enrichment": ["uniprot", "pdb", "semantic_scholar"],
        "generation": "hypothesis",
    },

    "climate_energy": {
        "label": "Climate & Energy",
        "description": "Emissions, technologies, policies, environmental impacts, regions — with NASA POWER climate data + Semantic Scholar",
        "aliases": ["climate", "energy", "environment", "climate change"],
        "entity_types": {
            "emission_source": {"color": "#ff7675", "description": "Source of greenhouse gas or pollutant"},
            "technology":      {"color": "#74b9ff", "description": "Energy or mitigation technology"},
            "policy":          {"color": "#a29bfe", "description": "Regulation, treaty, or policy"},
            "impact":          {"color": "#fd79a8", "description": "Environmental or health impact"},
            "region":          {"color": "#55efc4", "description": "Geographic region or country"},
            "resource":        {"color": "#ffeaa7", "description": "Natural resource or fuel type"},
        },
        "enrichment": ["nasa_power", "semantic_scholar"],
        "generation": "hypothesis",
    },

    "general": {
        "label": "General Science",
        "description": "Any scientific topic — entities auto-detected from paper content, with Semantic Scholar citation enrichment",
        "aliases": ["general", "science", "any"],
        "entity_types": {
            "concept":       {"color": "#dfe6e9", "description": "General scientific concept or term"},
            "method":        {"color": "#74b9ff", "description": "Experimental or analytical method"},
            "finding":       {"color": "#55efc4", "description": "Key scientific finding or result"},
            "technology":    {"color": "#fdcb6e", "description": "Technology or tool"},
            "organism":      {"color": "#e17055", "description": "Organism or biological system"},
            "material":      {"color": "#00cec9", "description": "Substance or material"},
        },
        "enrichment": ["semantic_scholar"],
        "generation": "hypothesis",
    },
}

DOMAIN_ALIAS_MAP = {}
for key, config in DOMAINS.items():
    for alias in config["aliases"]:
        DOMAIN_ALIAS_MAP[alias] = key


def get_domain(domain_key: str) -> dict | None:
    """Get domain config by key, falling back to alias lookup."""
    if domain_key in DOMAINS:
        return DOMAINS[domain_key]
    return DOMAINS.get(DOMAIN_ALIAS_MAP.get(domain_key))


def list_domains() -> list[dict]:
    """Return list of domain summaries."""
    return [
        {"key": key, "label": cfg["label"], "description": cfg["description"]}
        for key, cfg in DOMAINS.items()
    ]


def entity_types_list(domain_key: str) -> str:
    """Return a formatted string of entity types for a domain."""
    cfg = get_domain(domain_key)
    if not cfg:
        cfg = DOMAINS["general"]
    return ", ".join(sorted(cfg["entity_types"].keys()))


def entity_colors(domain_key: str) -> dict[str, str]:
    """Return entity_type -> color map for a domain."""
    cfg = get_domain(domain_key)
    if not cfg:
        cfg = DOMAINS["general"]
    return {et: info["color"] for et, info in cfg["entity_types"].items()}


DETECT_DOMAIN_PROMPT = """You are a scientific domain classifier. Given a research topic, classify it into ONE of these domains:

%s

Respond with EXACTLY the domain key and nothing else.

Topic: "%s" """


def build_detect_prompt() -> str:
    """Build the prompt prefix for domain detection (without topic)."""
    parts = []
    for key, cfg in DOMAINS.items():
        aliases_str = ", ".join(cfg["aliases"])
        parts.append(f"- {key}: {cfg['description']} (aliases: {aliases_str})")
    return "You are a scientific domain classifier. Given a research topic, classify it into ONE of these domains:\n\n" + "\n".join(parts) + '\n\nRespond with EXACTLY the domain key and nothing else.\n\nTopic: "'
