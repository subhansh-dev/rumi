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
        "extraction_guide": "Extract SPECIFIC scientific entities: named genes (KRAS, EGFR, TP53), specific proteins (EGFR T790M, KRAS G12C), named drugs (sotorasib, olaparib), specific mutations, cell lines, numerical properties (IC50, EC50), exact pathway names. AVOID generic categories like 'drug resistance' or 'cancer' without specific names.",
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
        "extraction_guide": "Extract SPECIFIC materials: exact chemical formulae (TiO2, CH3NH3PbI3), named compounds, exact bandgap values (1.55 eV), synthesis parameters (temperature, pressure, time), characterization data (XRD peaks, SEM dimensions). AVOID generic categories like 'nanomaterial' or 'polymer' without specific names.",
    },

    "neuroscience": {
        "label": "Neuroscience",
        "description": "Brain regions, neurotransmitters, disorders, genes, behaviors — with UniProt + PDB enrichment",
        "aliases": ["neuro", "neuroscience", "brain"],
        "entity_types": {
            "brain_region":      {"color": "#dda0dd", "description": "Specific brain area or nucleus"},
            "neurotransmitter":  {"color": "#98fb98", "description": "Neurotransmitter or neuromodulator"},
            "disorder":          {"color": "#f08080", "description": "Neurological or psychiatric disorder"},
            "gene":              {"color": "#60a5fa", "description": "Gene associated with neural function"},
            "protein":           {"color": "#a78bfa", "description": "Neural protein or receptor"},
            "behavior":          {"color": "#ffd700", "description": "Behavioral phenotype or response"},
            "neuron_type":       {"color": "#20b2aa", "description": "Type of neuron"},
            "mechanism":         {"color": "#fb923c", "description": "Neural mechanism or process"},
        },
        "enrichment": ["uniprot", "pdb", "semantic_scholar"],
        "generation": "hypothesis",
        "extraction_guide": "Extract SPECIFIC neural entities: named brain regions (ventral tegmental area, dorsolateral prefrontal cortex), specific neurotransmitters (dopamine, serotonin, glutamate), named receptors (DRD2, 5-HT2A, NMDA), exact genes (COMT, BDNF, DRD4), behavioral paradigms (Morris water maze, fear conditioning), channel types (Nav1.7, Kv4.2). AVOID generic categories without specific names.",
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
        "extraction_guide": "Extract SPECIFIC molecular entities: exact gene names (TP53, BRCA1, MYC), named proteins with domains, specific pathways (Wnt/beta-catenin, MAPK/ERK), organisms by exact species name, quantitative phenotypes (expression fold-change, KD values). AVOID generic terms.",
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
        "extraction_guide": "Extract SPECIFIC climate entities: exact emission values (GtCO2, ppm), named technologies (perovskite solar cells, Li-ion batteries), specific policies (Paris Agreement Article 6, EU ETS Phase 4), named regions with quantitative data, temperature targets (1.5C, 2.0C), exact timeframes. AVOID generic terms like 'emissions' or 'technology' without specifics.",
    },

    "space_astronomy": {
        "label": "Space & Astronomy",
        "description": "Celestial bodies, missions, exoplanets, galaxies, stars — with NASA image + exoplanet archive + arXiv enrichment",
        "aliases": ["space", "astronomy", "astro", "nasa", "cosmos"],
        "entity_types": {
            "celestial_body":    {"color": "#e056fd", "description": "Planet, moon, asteroid, or other body"},
            "mission":           {"color": "#00b894", "description": "Space mission or program"},
            "telescope":         {"color": "#00cec9", "description": "Telescope or observatory"},
            "exoplanet":         {"color": "#fdcb6e", "description": "Planet outside our solar system"},
            "spectral_feature":  {"color": "#ff6b6b", "description": "Spectral line, band, or signature at specific wavelength"},
            "molecule_gas":      {"color": "#a29bfe", "description": "Specific atmospheric molecule or gas (CH4, CO2, PH3, H2O, O2, NH3)"},
            "stellar_property":  {"color": "#ffeaa7", "description": "Stellar radiation, UV flux, activity metric"},
            "atmospheric_param": {"color": "#74b9ff", "description": "Atmospheric mixing ratio, pressure, temperature, composition metric"},
            "phenomenon":        {"color": "#fd79a8", "description": "Astrophysical phenomenon"},
            "theory":            {"color": "#74b9ff", "description": "Astrophysical theory or model"},
        },
        "enrichment": ["nasa_api", "arxiv", "semantic_scholar"],
        "generation": "hypothesis",
        "extraction_guide": "Extract SPECIFIC scientific variables: exact molecule names (CH4, CO2, PH3, H2O, O2, NH3, N2O), spectral line wavelengths (1.6um, 4.5um, 15um), atmospheric mixing ratios (1ppm, 0.1ppb), stellar UV flux values, planetary equilibrium temperatures (300K, 500K), transit depths (200ppm), orbital periods, stellar types (M-dwarf, G2V), instrument sensitivities (R=100,000), photochemical rates, biosignature metrics (DES, CDD). AVOID broad categories like 'exoplanet' or 'star' without specific type or property.",
    },

    "ecology": {
        "label": "Ecology & Environment",
        "description": "Species, habitats, ecosystems, conservation — with GBIF biodiversity + Semantic Scholar enrichment",
        "aliases": ["ecology", "environment", "biodiversity", "conservation", "nature"],
        "entity_types": {
            "species":             {"color": "#55efc4", "description": "Species or taxon"},
            "habitat":             {"color": "#00b894", "description": "Habitat or ecosystem type"},
            "ecosystem":           {"color": "#81ecec", "description": "Ecosystem or biome"},
            "organism":            {"color": "#74b9ff", "description": "Organism or life form"},
            "threat":              {"color": "#ff7675", "description": "Environmental threat or stressor"},
            "conservation_action": {"color": "#fdcb6e", "description": "Conservation strategy or action"},
            "region":              {"color": "#55efc4", "description": "Geographic region"},
        },
        "enrichment": ["gbif", "semantic_scholar"],
        "generation": "hypothesis",
        "extraction_guide": "Extract SPECIFIC ecological entities: exact species by binomial name (Panthera tigris, Quercus robur), population numbers, habitat types with specific locations, conservation status (IUCN categories), threat levels, ecosystem service values. AVOID generic terms without specific names or values.",
    },

    "physics": {
        "label": "Physics",
        "description": "Particles, forces, theories, experiments — with arXiv + Semantic Scholar enrichment",
        "aliases": ["physics", "particle", "quantum", "relativity", "mechanics"],
        "entity_types": {
            "particle":     {"color": "#fd79a8", "description": "Fundamental or composite particle"},
            "force":        {"color": "#e17055", "description": "Fundamental force or interaction"},
            "theory":       {"color": "#74b9ff", "description": "Physical theory or model"},
            "experiment":   {"color": "#00cec9", "description": "Experiment or detector"},
            "phenomenon":   {"color": "#fdcb6e", "description": "Physical phenomenon or effect"},
            "constant":     {"color": "#a29bfe", "description": "Physical constant"},
            "material":     {"color": "#00b894", "description": "Physical material or state"},
        },
        "enrichment": ["arxiv", "semantic_scholar"],
        "generation": "hypothesis",
        "extraction_guide": "Extract SPECIFIC physics entities: named particles (Higgs boson, neutrino, gluon), interaction cross-sections, coupling constants, experimental collaborations (ATLAS, LIGO), exact energy values (13 TeV, 125 GeV), detector names, physical constants with values. AVOID generic particle categories without specifics.",
    },

    "computer_science": {
        "label": "Computer Science",
        "description": "Algorithms, frameworks, datasets, benchmarks, models — with GitHub repo search + Semantic Scholar enrichment",
        "aliases": ["cs", "computer science", "software", "programming", "coding", "ai", "ml"],
        "entity_types": {
            "algorithm":   {"color": "#00b894", "description": "Algorithm or computational method"},
            "framework":   {"color": "#74b9ff", "description": "Software framework or library"},
            "dataset":     {"color": "#fdcb6e", "description": "Dataset or benchmark"},
            "model":       {"color": "#a29bfe", "description": "Computational model or architecture"},
            "technique":   {"color": "#55efc4", "description": "Programming or ML technique"},
            "architecture": {"color": "#fd79a8", "description": "System architecture or design pattern"},
            "language":    {"color": "#ffeaa7", "description": "Programming language"},
        },
        "enrichment": ["github", "semantic_scholar"],
        "generation": "hypothesis",
        "extraction_guide": "Extract SPECIFIC computer science entities: exact algorithm names (Transformer, ResNet-50, BERT), named frameworks (PyTorch, TensorFlow), specific datasets (ImageNet, CIFAR-10, SQuAD), architecture names with parameter counts, performance metrics (BLEU, F1, accuracy %), programming language versions, benchmark names (GLUE, HumanEval). AVOID generic categories like 'ML model' or 'neural network' without specific name or architecture.",
    },

    "earth_science": {
        "label": "Earth Science & Geology",
        "description": "Geological features, minerals, earthquakes, volcanoes, formations — with USGS data + Semantic Scholar",
        "aliases": ["earth", "geology", "geoscience", "earthquake", "volcano", "mineral"],
        "entity_types": {
            "geological_feature": {"color": "#e17055", "description": "Geological formation or feature"},
            "mineral":            {"color": "#00cec9", "description": "Mineral or rock type"},
            "process":            {"color": "#fdcb6e", "description": "Geological process"},
            "event":              {"color": "#ff7675", "description": "Geological event (earthquake, eruption)"},
            "region":             {"color": "#55efc4", "description": "Geographic or geologic region"},
            "formation":          {"color": "#a29bfe", "description": "Rock formation or stratigraphic unit"},
        },
        "enrichment": ["usgs", "semantic_scholar"],
        "generation": "hypothesis",
        "extraction_guide": "Extract SPECIFIC geological entities: named formations (Morrison Formation, Bakken Shale), specific minerals with formulae (Fe2O3, SiO2), exact magnitudes (Mw 6.7), named faults (San Andreas), eruption dates, specific locations with coordinates. AVOID generic geological terms.",
    },

    "oceanography": {
        "label": "Oceanography & Marine Science",
        "description": "Ocean regions, currents, marine species, chemistry — with NOAA tides + Semantic Scholar",
        "aliases": ["ocean", "marine", "oceanography", "sea", "coastal"],
        "entity_types": {
            "ocean_region":   {"color": "#00cec9", "description": "Ocean or sea region"},
            "current":        {"color": "#74b9ff", "description": "Ocean current or circulation"},
            "marine_species": {"color": "#55efc4", "description": "Marine species or organism"},
            "phenomenon":     {"color": "#fdcb6e", "description": "Oceanographic phenomenon"},
            "chemical":       {"color": "#a29bfe", "description": "Marine chemical or nutrient"},
            "basin":          {"color": "#81ecec", "description": "Ocean basin or trench"},
        },
        "enrichment": ["noaa", "semantic_scholar"],
        "generation": "hypothesis",
        "extraction_guide": "Extract SPECIFIC oceanographic entities: named currents (Gulf Stream, Kuroshio), exact temperatures (SST anomalies), salinity values (35 PSU), pH levels, named basins, specific species by binomial name, nutrient concentrations (nitrate, phosphate uM). AVOID generic ocean terms.",
    },

    "economics": {
        "label": "Economics & Finance",
        "description": "Economic indicators, markets, policies, countries — with World Bank data + Semantic Scholar",
        "aliases": ["economics", "economy", "finance", "trade", "market"],
        "entity_types": {
            "economic_indicator": {"color": "#fdcb6e", "description": "Economic metric (GDP, inflation, etc.)"},
            "market":             {"color": "#74b9ff", "description": "Market or economic sector"},
            "policy":             {"color": "#a29bfe", "description": "Economic or fiscal policy"},
            "sector":             {"color": "#55efc4", "description": "Industry or economic sector"},
            "country":            {"color": "#00b894", "description": "Country or economy"},
            "institution":        {"color": "#fd79a8", "description": "Economic institution or organization"},
        },
        "enrichment": ["world_bank", "semantic_scholar"],
        "generation": "hypothesis",
        "extraction_guide": "Extract SPECIFIC economic entities: exact GDP values (trillions USD), specific inflation rates, named policies by official name, specific market indices (S&P 500), elasticity estimates, country names with quantitative data. AVOID generic economic terms.",
    },

    "public_health": {
        "label": "Public Health & Epidemiology",
        "description": "Diseases, risk factors, interventions, populations — with WHO disease data + Semantic Scholar",
        "aliases": ["health", "public health", "epidemiology", "disease", "medicine"],
        "entity_types": {
            "disease":     {"color": "#ff7675", "description": "Disease or health condition"},
            "risk_factor": {"color": "#e17055", "description": "Health risk factor or exposure"},
            "intervention": {"color": "#00b894", "description": "Health intervention or treatment"},
            "population":  {"color": "#74b9ff", "description": "Population or demographic group"},
            "region":      {"color": "#55efc4", "description": "Geographic region"},
        },
        "enrichment": ["who", "semantic_scholar"],
        "generation": "hypothesis",
        "extraction_guide": "Extract SPECIFIC public health entities: exact disease names (COVID-19, tuberculosis), incidence rates (per 100,000), named interventions (vaccine names, drug regimens), population demographics with values, risk ratios, odds ratios, confidence intervals. AVOID generic health terms.",
    },

    "mathematics": {
        "label": "Mathematics",
        "description": "Integer sequences, theorems, conjectures, constants, functions — with OEIS sequence data + arXiv + Semantic Scholar",
        "aliases": ["math", "mathematics", "mathematical", "number theory", "algebra", "geometry"],
        "entity_types": {
            "sequence":   {"color": "#6c5ce7", "description": "Integer sequence or numeric pattern"},
            "constant":   {"color": "#fd79a8", "description": "Mathematical constant"},
            "theorem":    {"color": "#00b894", "description": "Theorem or mathematical proof"},
            "conjecture": {"color": "#fdcb6e", "description": "Conjecture or open problem"},
            "function":   {"color": "#74b9ff", "description": "Mathematical function or transform"},
            "structure":  {"color": "#a29bfe", "description": "Algebraic or geometric structure"},
        },
        "enrichment": ["oeis", "arxiv", "semantic_scholar"],
        "generation": "hypothesis",
        "extraction_guide": "Extract SPECIFIC mathematical entities: named theorems (Fermat's Last Theorem), exact sequences (OEIS A000045), named constants (pi, e, gamma), specific functions with domains, named conjectures with status, exact equations or identities. AVOID generic math terms.",
    },

    "social_science": {
        "label": "Social Sciences",
        "description": "Sociology, political science, psychology, anthropology — with OpenAlex paper search + Semantic Scholar",
        "aliases": ["social", "sociology", "political science", "psychology", "anthropology"],
        "entity_types": {
            "theory":      {"color": "#e17055", "description": "Social or behavioral theory"},
            "concept":     {"color": "#74b9ff", "description": "Social science concept or construct"},
            "methodology": {"color": "#00b894", "description": "Research methodology or framework"},
            "population":  {"color": "#fdcb6e", "description": "Population or demographic group"},
            "institution": {"color": "#a29bfe", "description": "Institution or organization"},
            "phenomenon":  {"color": "#55efc4", "description": "Social phenomenon or trend"},
        },
        "enrichment": ["openalex", "semantic_scholar"],
        "generation": "hypothesis",
        "extraction_guide": "Extract SPECIFIC social science entities: named theories (Social Identity Theory, Rational Choice Theory), sample sizes and demographics, specific survey instruments (SES, Big Five), named institutions, effect sizes, p-values. AVOID generic social terms.",
    },

    "chemistry": {
        "label": "Chemistry",
        "description": "Chemical compounds, elements, reactions, lab techniques — with NCI CIR resolver + PubChem + Semantic Scholar",
        "aliases": ["chemistry", "chemical", "organic chemistry", "inorganic", "biochemistry"],
        "entity_types": {
            "chemical":   {"color": "#00cec9", "description": "Chemical compound or substance"},
            "compound":   {"color": "#e17055", "description": "Chemical compound or molecule"},
            "element":    {"color": "#fdcb6e", "description": "Chemical element"},
            "reaction":   {"color": "#fd79a8", "description": "Chemical reaction or process"},
            "technique":  {"color": "#74b9ff", "description": "Lab or analytical technique"},
            "property":   {"color": "#a29bfe", "description": "Chemical or physical property"},
        },
        "enrichment": ["cir", "pubchem", "semantic_scholar"],
        "generation": "hypothesis",
        "extraction_guide": "Extract SPECIFIC chemical entities: exact compound names with formulae (C6H12O6, NaCl), named reactions (Friedel-Crafts, Suzuki coupling), specific techniques (HPLC, NMR), yields (85%), temperatures (150C), solvents (THF, DCM). AVOID generic chemical categories.",
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
        "extraction_guide": "Extract SPECIFIC entities: named concepts, specific methods, quantitative findings with values, named technologies, organisms by exact name. AVOID vague categories without specific identifiers.",
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
