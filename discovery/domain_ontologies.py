"""
domain_ontologies.py — Real scientific ontologies for all 17 domains.

Not generic terms. Real physics. Real biology. Real chemistry.

Each domain has:
- entities: real objects/concepts in that field
- relationships: real relationships between them
- mechanisms: known causal pathways
- constraints: known physical/mathematical constraints
- equations: key equations in that field
- observables: what can be measured
- anomalies: known unsolved problems

This is what makes RUMI sound like a scientist, not a chatbot.
"""

DOMAIN_ONTOLOGIES = {
    "space_astronomy": {
        "entities": {
            "compact_objects": ["magnetar", "pulsar", "neutron star", "black hole", "white dwarf", "binary pulsar"],
            "emission_mechanisms": ["synchrotron radiation", "curvature radiation", "inverse Compton", "cyclotron emission", "bremsstrahlung", "pair annihilation"],
            "plasma_physics": ["dispersion measure", "rotation measure", "Faraday rotation", "plasma lens", "scattering", "scintillation", "free-free absorption"],
            "transients": ["fast radio burst", "gamma-ray burst", "supernova", "kilonova", "tidal disruption event", "X-ray burst"],
            "cosmology": ["Hubble constant", "dark energy", "dark matter", "cosmic microwave background", "baryon acoustic oscillation", "large-scale structure"],
            "instrumentation": ["radio telescope", "interferometer", "antenna", "receiver", "spectrometer", "polarimeter"],
            "quantities": ["flux density", "luminosity", "redshift", "distance modulus", "spectral index", "polarization angle", "rotation measure", "dispersion measure", "scattering timescale"],
        },
        "mechanisms": {
            "magnetar_flare": "Magnetic reconnection in magnetar magnetosphere releases ~10^46 erg in <1ms, producing coherent radio emission via curvature radiation",
            "pulsar_emission": "Rotating magnetic dipole radiates at omega=2pi/P, particles accelerated along field lines emit curvature radiation at nu_c ~ gamma^3*c/R_LC",
            "frb_dispersion": "Cold plasma dispersion: DM = integral(n_e dl), delay ~ 4.15 GHz^-2 ms * DM * nu^-2",
            "scattering_broadening": "Multipath propagation in turbulent ISM: tau_s ~ 0.1 ms * (DM/100)^2 * (GHz/nu)^4",
            "synchrotron_emission": "Relativistic electrons in B field: nu_c ~ 3*gamma^2*e*B/(4*pi*m_e*c), P(nu) ~ nu^(-alpha)",
            "hubble_tension": "CMB gives H0=67.4 km/s/Mpc, SNe give H0=73.0. 5-sigma discrepancy. Possible new physics at z~1100 or systematics.",
        },
        "equations": {
            "dispersion_delay": "Delta_t = 4.15 GHz^-2 ms * DM * (nu_lo^-2 - nu_hi^-2)",
            "synchrotron_frequency": "nu_c = 3 * gamma^2 * e * B / (4 * pi * m_e * c)",
            "curvature_radiation": "nu_c = 3 * gamma^3 * c / (2 * pi * R_LC)",
            "scattering_timescale": "tau_s = 0.1 ms * (DM/100)^2 * (GHz/nu)^4",
            "rotation_measure": "Delta_chi = RM * lambda^2, RM = 0.81 rad/m^2 * integral(n_e * B_parallel dl)",
            "friedmann_equation": "H^2 = (8*pi*G/3)*rho + Lambda/3 - k*c^2/a^2",
            "luminosity_distance": "d_L = (1+z) * c/H0 * integral(1/E(z') dz', 0, z)",
        },
        "constraints": {
            "speed_of_light": "c = 2.998e8 m/s (exact)",
            "planck_constant": "h = 6.626e-34 J*s",
            "electron_mass": "m_e = 9.109e-31 kg",
            "proton_mass": "m_p = 1.673e-27 kg",
            "gravitational_constant": "G = 6.674e-11 m^3/kg/s^2",
            "hubble_constant_range": "60 < H0 < 80 km/s/Mpc (all measurements)",
            "cmb_temperature": "T_CMB = 2.725 K",
            "baryon_density": "Omega_b * h^2 = 0.0224 (BBN+CMB)",
        },
        "known_anomalies": [
            "Hubble tension: CMB vs SNe H0 discrepancy at 5-sigma",
            "FRB origin: coherent emission mechanism unknown",
            "Dark matter: 85% of matter is non-baryonic, nature unknown",
            "Dark energy: cosmological constant or dynamical field?",
            "Cosmic lithium problem: 3x less Li-7 than BBN predicts",
            "Ultra-high-energy cosmic rays: sources unknown above GZK limit",
        ],
    },

    "drug_discovery": {
        "entities": {
            "targets": ["kinase", "receptor", "enzyme", "ion channel", "transporter", "transcription factor", "GPCR"],
            "molecules": ["small molecule", "antibody", "peptide", "nucleic acid", "PROTAC", "molecular glue", "allosteric modulator"],
            "pathways": ["MAPK pathway", "PI3K/AKT", "JAK/STAT", "Wnt signaling", "Notch signaling", "Hedgehog", "NF-kB"],
            "diseases": ["cancer", "autoimmune", "neurodegenerative", "cardiovascular", "metabolic", "infectious"],
            "measurements": ["IC50", "EC50", "Kd", "Ki", "selectivity ratio", "therapeutic index", "bioavailability", "half-life"],
            "resistance": ["point mutation", "gene amplification", "efflux pump", "bypass pathway", "epithelial-mesenchymal transition"],
        },
        "mechanisms": {
            "competitive_inhibition": "Drug binds active site, competes with substrate. IC50 = Ki*(1+[S]/Km)",
            "allosteric_modulation": "Drug binds allosteric site, changes protein conformation. Can be positive (PAM) or negative (NAM)",
            "protac_degradation": "PROTAC brings E3 ligase to target protein, inducing ubiquitination and proteasomal degradation. Catalytic mechanism.",
            "resistance_bypass": "Cancer cells activate alternative pathway when primary target is inhibited. E.g., MET amplification bypasses EGFR inhibition.",
            "synthetic_lethality": "Two genes are synthetically lethal if losing both kills cell but losing either alone doesn't. E.g., BRCA1 + PARP1.",
        },
        "equations": {
            "michaelis_menten": "v = Vmax * [S] / (Km + [S])",
            "ic50_cheng_prusoff": "IC50 = Ki * (1 + [S]/Km) for competitive inhibition",
            "drug_concentration": "C(t) = C0 * e^(-k*t), k = 0.693/t_half",
            "therapeutic_index": "TI = TD50 / ED50",
            "binding_affinity": "Delta_G = -RT*ln(Ka) = RT*ln(Kd)",
        },
        "constraints": {
            "lipinski_rule_of_5": "MW<500, LogP<5, HBD<=5, HBA<=10 for oral bioavailability",
            "selectivity_window": "Target IC50 / off-target IC50 > 100x for safety",
            "plasma_protein_binding": "Free fraction f_u = C_unbound / C_total, only free drug is active",
            "hepatic_clearance": "CLh = Q*f_u*CLint/(Q + f_u*CLint)",
        },
    },

    "neuroscience": {
        "entities": {
            "cells": ["pyramidal neuron", "interneuron", "astrocyte", "oligodendrocyte", "microglia", "Schwann cell"],
            "transmitters": ["glutamate", "GABA", "dopamine", "serotonin", "acetylcholine", "norepinephrine", "glycine"],
            "receptors": ["AMPA", "NMDA", "GABA-A", "GABA-B", "D1", "D2", "5-HT1A", "5-HT2A", "muscarinic", "nicotinic"],
            "circuits": ["cortical column", "basal ganglia loop", "cerebellar circuit", "hippocampal trisynaptic", "thalamic relay"],
            "measurements": ["fMRI BOLD", "EEG", "MEG", "calcium imaging", "patch clamp", "single-unit recording"],
        },
        "mechanisms": {
            "ltp_induction": "High-frequency stimulation -> Ca2+ influx through NMDA -> CaMKII activation -> AMPA receptor insertion -> synaptic strengthening",
            "dopamine_reward": "VTA dopamine neurons fire to unexpected reward, encode prediction error: delta = R - V(s)",
            "neural_oscillation": "Pyramidal-interneuron network gamma (PING): excitation -> inhibition -> rebound -> excitation, period ~25ms for 40Hz gamma",
            "action_potential": "Hodgkin-Huxley: C*dV/dt = I_Na - I_K - I_L + I_ext, where I_x = g_x * m^p * h^q * (V - E_x)",
        },
        "equations": {
            "hodgkin_huxley": "C*dV/dt = g_Na*m^3*h*(V-E_Na) - g_K*n^4*(V-E_K) - g_L*(V-E_L) + I",
            "cable_equation": "lambda^2 * d^2V/dx^2 - tau*dV/dt = V, lambda=sqrt(r_m/r_i)",
            "fick_diffusion": "J = -D * dc/dx",
            "synaptic_current": "I_syn = g_syn * (V - E_syn) * s(t), s(t) = (t/tau)*e^(1-t/tau)",
        },
    },

    "materials_science": {
        "entities": {
            "structures": ["crystal", "amorphous", "polycrystalline", "nanocrystalline", "quasicrystal", "liquid crystal"],
            "defects": ["vacancy", "interstitial", "dislocation", "grain boundary", "stacking fault", "twin boundary", "precipitate"],
            "properties": ["bandgap", "conductivity", "hardness", "toughness", "elastic modulus", "thermal expansion", "magnetization"],
            "classes": ["metal", "ceramic", "polymer", "composite", "semiconductor", "superconductor", "2D material"],
        },
        "mechanisms": {
            "phonon_transport": "Heat conduction via lattice vibrations: k = 1/3 * C_v * v * l, where v=group velocity, l=mfp",
            "dislocation_motion": "Stress drives dislocation glide on slip planes: tau = tau_0 + k*d^(-1/2) (Hall-Petch)",
            "semiconductor_doping": "Adding donor/acceptor atoms shifts Fermi level: n = N_D * exp(-(E_D-E_F)/kT)",
            "corrosion": "Electrochemical: anode M -> M^n+ + n*e-, cathode O2 + 2H2O + 4e- -> 4OH-",
        },
        "equations": {
            "schrodinger": "-hbar^2/(2m) * nabla^2*psi + V*psi = E*psi",
            "boltzmann_transport": "df/dt + v*grad_r(f) + F/m*grad_v(f) = (df/dt)_collision",
            "arrhenius": "k = A * exp(-Ea/(R*T))",
            "band_structure": "E(k) = E_c + hbar^2*k^2/(2*m*) for conduction band",
        },
    },

    "physics": {
        "entities": {
            "particles": ["electron", "proton", "neutron", "photon", "neutrino", "quark", "boson", "fermion", "Higgs boson", "W boson", "Z boson", "gluon"],
            "forces": ["gravity", "electromagnetic", "strong nuclear", "weak nuclear"],
            "theories": ["general relativity", "quantum mechanics", "standard model", "quantum field theory", "string theory", "loop quantum gravity"],
            "phenomena": ["entanglement", "superposition", "tunneling", "pair production", "Hawking radiation", "Cherenkov radiation"],
        },
        "mechanisms": {
            "higgs_mechanism": "Scalar field gives mass to W/Z bosons via spontaneous symmetry breaking. v = 246 GeV.",
            "quantum_tunneling": "Particle penetrates classically forbidden barrier: T ~ exp(-2*integral(sqrt(2m(V-E))/hbar dx))",
            "chiral_symmetry_breaking": "QCD vacuum condensate <q*q_bar> != 0 breaks chiral symmetry, generates hadron masses",
        },
        "equations": {
            "einstein_field": "G_uv + Lambda*g_uv = 8*pi*G/c^4 * T_uv",
            "dirac_equation": "(i*gamma^mu*d_mu - m)*psi = 0",
            "schrodinger": "i*hbar*d_psi/dt = H*psi",
            "maxwell": "d*F = J, d*F = 0 (in differential forms)",
        },
    },

    "ecology": {
        "entities": {
            "organisms": ["species", "population", "community", "ecosystem", "biome"],
            "interactions": ["predation", "competition", "mutualism", "parasitism", "commensalism"],
            "processes": ["primary production", "decomposition", "nutrient cycling", "succession", "disturbance"],
            "measurements": ["species richness", "Shannon diversity", "biomass", "productivity", "carrying capacity"],
        },
        "mechanisms": {
            "lotka_volterra": "Prey: dN/dt = rN - aNP. Predator: dP/dt = baNP - mP. Limit cycles.",
            "competitive_exclusion": "Two species competing for same resource cannot coexist: one goes extinct (Gause's principle)",
            "island_biogeography": "Species richness S = equilibrium of immigration and extinction rates. S = I*X/E(X).",
        },
        "equations": {
            "lotka_volterra": "dN1/dt = r1*N1*(1 - N1/K1 - alpha12*N2/K1)",
            "shannon_diversity": "H = -sum(p_i * ln(p_i))",
            "species_area": "S = c*A^z, z ~ 0.25 for islands",
        },
    },

    "climate_energy": {
        "entities": {
            "greenhouse": ["CO2", "methane", "N2O", "water vapor", "ozone", "CFCs"],
            "systems": ["ocean circulation", "atmospheric circulation", "ice sheets", "permafrost", "carbon cycle"],
            "energy": ["solar irradiance", "albedo", "radiative forcing", "climate sensitivity"],
        },
        "mechanisms": {
            "greenhouse_effect": "GHGs absorb IR radiation, re-emit in all directions. Forcing: dF = 5.35 * ln(C/C0) W/m^2 for CO2",
            "ice_albedo_feedback": "Warming -> ice melt -> lower albedo -> more absorption -> more warming. Positive feedback.",
            "thermohaline_circulation": "Density-driven ocean circulation. Salty water sinks at poles, flows along bottom, upwells at tropics.",
        },
        "equations": {
            "stefan_boltzmann": "F = sigma * T^4",
            "radiative_forcing": "dF = 5.35 * ln(C/C0) W/m^2 for CO2",
            "climate_sensitivity": "dT = lambda * dF, lambda ~ 0.8 K/(W/m^2) for ECS ~ 3K per CO2 doubling",
        },
    },

    "molecular_biology": {
        "entities": {
            "molecules": ["DNA", "RNA", "protein", "lipid", "carbohydrate", "metabolite"],
            "processes": ["transcription", "translation", "replication", "repair", "splicing", "folding"],
            "regulation": ["promoter", "enhancer", "silencer", "transcription factor", "microRNA", "epigenetic mark"],
        },
        "mechanisms": {
            "central_dogma": "DNA -> (transcription) -> mRNA -> (translation) -> protein. Information flow with exceptions (reverse transcriptase, prions).",
            "gene_regulation": "Transcription factors bind promoter/enhancer regions, recruit RNA polymerase or repressors. Combinatorial control.",
            "protein_folding": "Anfinsen's dogma: amino acid sequence determines 3D structure. Levinthal paradox: 10^300 conformations, folded in ms.",
        },
        "equations": {
            "michaelis_menten": "v = Vmax*[S]/(Km+[S])",
            "hill_equation": "theta = [L]^n / (K_d + [L]^n)",
            "gibbs_free_energy": "dG = dH - T*dS",
        },
    },

    "mathematics": {
        "entities": {
            "structures": ["group", "ring", "field", "vector space", "topology", "manifold", "graph"],
            "analysis": ["limit", "derivative", "integral", "series", "transform"],
            "algebra": ["polynomial", "matrix", "eigenvalue", "determinant", "tensor"],
        },
        "mechanisms": {
            "fourier_analysis": "Any periodic function decomposes into sinusoids: f(x) = a0/2 + sum(a_n*cos(nx) + b_n*sin(nx))",
            "eigendecomposition": "A*v = lambda*v. Principal components, stability analysis, quantum mechanics.",
        },
        "equations": {
            "euler_identity": "e^(i*pi) + 1 = 0",
            "gaussian_integral": "integral(e^(-x^2), -inf, inf) = sqrt(pi)",
            "navier_stokes": "rho*(dv/dt + v*grad(v)) = -grad(p) + mu*nabla^2(v) + f",
        },
    },

    "chemistry": {
        "entities": {
            "bonding": ["covalent bond", "ionic bond", "metallic bond", "hydrogen bond", "van der Waals"],
            "reactions": ["synthesis", "decomposition", "substitution", "elimination", "addition", "redox"],
            "analysis": ["spectroscopy", "chromatography", "mass spectrometry", "X-ray diffraction", "NMR"],
        },
        "mechanisms": {
            "sn2_mechanism": "Nucleophile attacks electrophilic carbon from backside, concerted bond breaking/forming. Walden inversion.",
            "electrophilic_aromatic": "Electrophile attacks aromatic ring, Wheland intermediate, rearomatization. Rate depends on substituent.",
        },
        "equations": {
            "arrhenius": "k = A*exp(-Ea/RT)",
            "nernst": "E = E0 - (RT/nF)*ln(Q)",
            "gibbs": "dG = dH - TdS = -RT*ln(K)",
        },
    },

    "computer_science": {
        "entities": {
            "algorithms": ["sorting", "searching", "graph algorithm", "dynamic programming", "greedy", "divide and conquer"],
            "architecture": ["CPU", "GPU", "TPU", "memory hierarchy", "cache", "pipeline"],
            "ml": ["neural network", "transformer", "attention", "gradient descent", "backpropagation", "regularization"],
        },
        "mechanisms": {
            "attention": "QKV attention: Attention(Q,K,V) = softmax(QK^T/sqrt(d_k))*V. Scaled dot-product.",
            "backpropagation": "Chain rule applied layer by layer: dL/dw_i = dL/dy * dy/dw_i. Gradient descent updates.",
            "transformer": "Multi-head attention + FFN + residual + layer norm. Self-attention is O(n^2) in sequence length.",
        },
        "equations": {
            "softmax": "softmax(x_i) = exp(x_i) / sum(exp(x_j))",
            "cross_entropy": "L = -sum(y_i * log(p_i))",
            "adam": "m_t = beta1*m_{t-1} + (1-beta1)*g, v_t = beta2*v_{t-1} + (1-beta2)*g^2",
        },
    },

    "public_health": {
        "entities": {
            "epidemiology": ["incidence", "prevalence", "mortality rate", "case fatality rate", "R0", "herd immunity"],
            "interventions": ["vaccine", "quarantine", "contact tracing", "sanitation", "health education"],
            "diseases": ["infectious disease", "chronic disease", "mental health", "maternal health", "nutrition"],
        },
        "mechanisms": {
            "sir_model": "S->I->R: dS/dt=-beta*S*I, dI/dt=beta*S*I-gamma*I, dR/dt=gamma*I. R0=beta/gamma.",
            "herd_immunity": "When fraction immune > 1-1/R0, epidemic cannot sustain. Threshold immunity.",
        },
        "equations": {
            "sir": "dS/dt = -beta*S*I, dI/dt = beta*S*I - gamma*I, dR/dt = gamma*I",
            "r0": "R0 = beta / gamma",
            "ppv": "PPV = (sensitivity * prevalence) / (sensitivity*prevalence + (1-specificity)*(1-prevalence))",
        },
    },

    "economics": {
        "entities": {
            "macro": ["GDP", "inflation", "unemployment", "interest rate", "money supply", "trade balance"],
            "micro": ["supply", "demand", "elasticity", "market structure", "externalities", "public goods"],
        },
        "mechanisms": {
            "supply_demand": "Price where Q_s = Q_d. Shifts in S or D change equilibrium price and quantity.",
            "monetary_policy": "Central bank sets interest rate. Lower rate -> cheaper borrowing -> more investment -> higher GDP. Transmission lag ~12-18 months.",
        },
        "equations": {
            "gdp": "Y = C + I + G + NX",
            "phillips_curve": "pi = pi_e - beta*(u - u_n) + v",
            "taylor_rule": "i = r* + pi + 0.5*(pi - pi*) + 0.5*(y - y*)",
        },
    },

    "oceanography": {
        "entities": {
            "physical": ["thermohaline circulation", "Ekman transport", "upwelling", "tides", "waves", "eddies"],
            "chemical": ["dissolved oxygen", "pH", "salinity", "nutrients", "carbon cycle"],
            "biological": ["phytoplankton", "zooplankton", "food web", "primary production"],
        },
        "mechanisms": {
            "thermohaline": "Density-driven circulation. Cold salty water sinks at poles, flows along bottom, upwells at tropics. ~1000 year cycle.",
            "coral_bleaching": "Temperature stress -> coral expels symbiotic zooxanthellae -> white skeleton -> death if prolonged.",
        },
    },

    "earth_science": {
        "entities": {
            "geology": ["plate tectonics", "earthquake", "volcano", "mineral", "rock cycle", "erosion"],
            "geophysics": ["seismic wave", "magnetic field", "gravity anomaly", "heat flow"],
        },
        "mechanisms": {
            "plate_tectonics": "Mantle convection drives plate motion. Plates interact at boundaries: divergent, convergent, transform.",
            "earthquake_cycle": "Stress accumulates on locked fault -> elastic strain -> rupture when stress exceeds friction -> seismic waves -> aftershocks.",
        },
    },

    "social_science": {
        "entities": {
            "sociology": ["social structure", "institution", "norm", "culture", "inequality", "social mobility"],
            "psychology": ["cognition", "emotion", "motivation", "personality", "social influence"],
        },
        "mechanisms": {
            "conformity": "Asch experiments: ~75% conform at least once. Normative + informational influence.",
            "cognitive_dissonance": "Holding contradictory beliefs -> psychological discomfort -> attitude change to restore consistency.",
        },
    },

    "general": {
        "entities": {
            "scientific_method": ["hypothesis", "experiment", "observation", "theory", "law", "model"],
            "reasoning": ["induction", "deduction", "abduction", "analogy", "Occam's razor"],
        },
        "mechanisms": {
            "scientific_method": "Observation -> Hypothesis -> Prediction -> Experiment -> Theory -> Law",
            "falsification": "Popper: A theory is scientific only if it can be falsified. One counterexample disproves.",
        },
    },
}


def get_ontology(domain: str) -> dict:
    """Get the ontology for a domain."""
    return DOMAIN_ONTOLOGIES.get(domain, DOMAIN_ONTOLOGIES.get("general", {}))


def get_entity_types(domain: str) -> list:
    """Get all entity type names for a domain."""
    ont = get_ontology(domain)
    return list(ont.get("entities", {}).keys())


def get_all_entity_names(domain: str) -> list:
    """Get all entity names for a domain."""
    ont = get_ontology(domain)
    names = []
    for category, entities in ont.get("entities", {}).items():
        names.extend(entities)
    return names


def get_mechanisms(domain: str) -> dict:
    """Get known mechanisms for a domain."""
    return get_ontology(domain).get("mechanisms", {})


def get_equations(domain: str) -> dict:
    """Get key equations for a domain."""
    return get_ontology(domain).get("equations", {})


def get_constraints(domain: str) -> dict:
    """Get known constraints for a domain."""
    return get_ontology(domain).get("constraints", {})


def get_known_anomalies(domain: str) -> list:
    """Get known unsolved problems for a domain."""
    return get_ontology(domain).get("known_anomalies", [])
