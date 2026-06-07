"""
nist_api.py — NIST Chemistry WebBook & Physical Reference Data

Free, no API key needed. Searches for chemical compounds and retrieves
thermochemical data, spectral data, and physical properties.

Usage:
    from discovery.nist_api import search_compound, get_thermochemical_data
"""

import re
import urllib.request
import urllib.parse
import time
from typing import Optional


_NIST_WEBBOOK_BASE = "https://webbook.nist.gov"
_NIST_CHEMSEARCH = f"{_NIST_WEBBOOK_BASE}/cgi/cbook.cgi"


def _rate_limit():
    time.sleep(0.5)


def _fetch(url: str) -> Optional[str]:
    """Fetch a URL with proper headers."""
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "RUMI/1.0 (scientific discovery engine)",
            "Accept": "text/html,application/json",
        })
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        return None


def search_compound(name: str, limit: int = 3) -> list[dict]:
    """
    Search NIST Chemistry WebBook for a compound by name.
    Returns list of matching compounds with IDs and names.
    """
    _rate_limit()
    encoded = urllib.parse.quote(name)
    url = f"{_NIST_CHEMSEARCH}?Name={encoded}&Units=SI&cTP=on"
    html = _fetch(url)
    if not html:
        return []

    results = []

    # Check if we got a direct result page (single compound)
    cas_match = re.search(r'CAS Registry Number:</a>\s*(\d+-\d+-\d+)', html)
    name_match = re.search(r'<h1(?:\s[^>]*)?>(.*?)</h1>', html)
    formula_match = re.search(r'<h1(?:\s[^>]*)?>.*?\((.*?)\)', html)

    if cas_match:
        result = {
            "name": name_match.group(1).strip() if name_match else name,
            "formula": formula_match.group(1).strip() if formula_match else "",
            "cas": cas_match.group(1),
            "source": "NIST Chemistry WebBook",
            "url": url,
        }

        # Try to extract molecular weight
        mw_match = re.search(r'Molecular weight:\s*([\d.]+)', html)
        if mw_match:
            result["molecular_weight"] = float(mw_match.group(1))

        # Try to extract IUPAC name
        iupac_match = re.search(r'IUPAC Standard InChI:</a>\s*(.*?)<', html)
        if iupac_match:
            result["inchi"] = iupac_match.group(1).strip()

        results.append(result)
    else:
        # Search results page — extract links to compounds
        links = re.findall(
            r'<a href="(/cgi/cbook\.cgi\?ID=\d+[^"]*)">(.*?)</a>',
            html, re.DOTALL
        )
        for href, link_text in links[:limit]:
            clean_name = re.sub(r'<[^>]+>', '', link_text).strip()
            if clean_name:
                results.append({
                    "name": clean_name,
                    "url": f"{_NIST_WEBBOOK_BASE}{href}",
                    "source": "NIST Chemistry WebBook",
                })

    return results[:limit]


def get_thermochemical_data(compound_id: str) -> dict:
    """
    Get thermochemical data for a compound from NIST WebBook.
    compound_id can be a CAS number or NIST ID.
    """
    _rate_limit()
    url = f"{_NIST_CHEMSEARCH}?ID={compound_id}&Units=SI&cTP=on&cTS=on"
    html = _fetch(url)
    if not html:
        return {"status": "error", "error": "Failed to fetch"}

    data = {"source": "NIST Chemistry WebBook", "url": url}

    # Extract name
    name_match = re.search(r'<h1(?:\s[^>]*)?>(.*?)</h1>', html)
    if name_match:
        data["name"] = re.sub(r'<[^>]+>', '', name_match.group(1)).strip()

    # Extract formula
    formula_match = re.search(r'<h1(?:\s[^>]*)?>.*?\((.*?)\)', html)
    if formula_match:
        data["formula"] = formula_match.group(1).strip()

    # Extract phase transition data
    bp_match = re.search(r'Boiling point.*?([\d.]+)\s*K', html, re.DOTALL)
    if bp_match:
        data["boiling_point_K"] = float(bp_match.group(1))

    mp_match = re.search(r'Melting point.*?([\d.]+)\s*K', html, re.DOTALL)
    if mp_match:
        data["melting_point_K"] = float(mp_match.group(1))

    # Extract enthalpy of formation
    hf_match = re.search(
        r'Enthalpy of formation.*?(-?[\d.]+)\s*kJ/mol',
        html, re.DOTALL
    )
    if hf_match:
        data["enthalpy_of_formation_kj_mol"] = float(hf_match.group(1))

    # Extract entropy
    s_match = re.search(
        r'Standard entropy.*?([\d.]+)\s*J/mol\*K',
        html, re.DOTALL
    )
    if s_match:
        data["entropy_J_mol_K"] = float(s_match.group(1))

    # Extract heat capacity
    cp_match = re.search(
        r'Heat capacity.*?([\d.]+)\s*J/mol\*K',
        html, re.DOTALL
    )
    if cp_match:
        data["heat_capacity_J_mol_K"] = float(cp_match.group(1))

    data["status"] = "ok" if len(data) > 3 else "partial"
    return data


def get_spectral_lines(element: str, wavelength_range: tuple = None) -> list[dict]:
    """
    Get spectral lines for an element from NIST ASD (Atomic Spectra Database).
    Returns list of spectral lines with wavelengths and intensities.
    """
    _rate_limit()
    encoded = urllib.parse.quote(element)
    url = (
        f"https://physics.nist.gov/cgi-bin/ASD/lines1.pl"
        f"?spectra={encoded}&limits_type=0&low_w=&upp_w=&unit=1"
        f"&submit=Retrieve+Data"
    )
    html = _fetch(url)
    if not html:
        return []

    lines = []
    # Parse spectral lines from the HTML table
    rows = re.findall(
        r'<tr[^>]*>\s*<td[^>]*>(.*?)</td>\s*<td[^>]*>(.*?)</td>\s*<td[^>]*>(.*?)</td>',
        html, re.DOTALL
    )
    for wavelength, intensity, transition in rows[:20]:
        w = re.sub(r'<[^>]+>', '', wavelength).strip()
        i = re.sub(r'<[^>]+>', '', intensity).strip()
        t = re.sub(r'<[^>]+>', '', transition).strip()
        if w:
            try:
                lines.append({
                    "wavelength_nm": float(w),
                    "intensity": i,
                    "transition": t,
                    "element": element,
                    "source": "NIST ASD",
                })
            except ValueError:
                continue

    return lines


def get_fundamental_constants() -> dict:
    """
    Get NIST CODATA fundamental physical constants.
    Returns dict of constant_name -> {value, units, uncertainty}.
    """
    constants = {
        "speed_of_light": {"value": 299792458, "units": "m/s", "uncertainty": 0},
        "planck_constant": {"value": 6.62607015e-34, "units": "J*s", "uncertainty": 0},
        "boltzmann_constant": {"value": 1.380649e-23, "units": "J/K", "uncertainty": 0},
        "elementary_charge": {"value": 1.602176634e-19, "units": "C", "uncertainty": 0},
        "avogadro_number": {"value": 6.02214076e23, "units": "1/mol", "uncertainty": 0},
        "electron_mass": {"value": 9.1093837015e-31, "units": "kg", "uncertainty": 5.1e-40},
        "proton_mass": {"value": 1.67262192369e-27, "units": "kg", "uncertainty": 5.1e-37},
        "neutron_mass": {"value": 1.67492749804e-27, "units": "kg", "uncertainty": 9.5e-37},
        "gravitational_constant": {"value": 6.67430e-11, "units": "m^3/(kg*s^2)", "uncertainty": 1.5e-15},
        "fine_structure_constant": {"value": 7.2973525693e-3, "units": "1", "uncertainty": 1.1e-12},
        "rydberg_constant": {"value": 10973731.568160, "units": "1/m", "uncertainty": 2.1e-5},
        "bohr_radius": {"value": 5.29177210903e-11, "units": "m", "uncertainty": 8e-21},
        "stefan_boltzmann_constant": {"value": 5.670374419e-8, "units": "W/(m^2*K^4)", "uncertainty": 0},
        "vacuum_permittivity": {"value": 8.8541878128e-12, "units": "F/m", "uncertainty": 1.3e-21},
        "vacuum_permeability": {"value": 1.25663706212e-6, "units": "N/A^2", "uncertainty": 1.9e-16},
    }
    return {"source": "NIST CODATA 2018", "constants": constants}


def search_spectra(element: str, limit: int = 10) -> list[dict]:
    """
    Search for spectral data — combines ASD spectral lines with
    fundamental constants lookup. Main entry point for physics domain.
    """
    results = []

    # Get spectral lines
    lines = get_spectral_lines(element)
    results.extend(lines[:limit])

    # If no spectral lines found, return fundamental constants as reference
    if not results:
        constants = get_fundamental_constants()
        for name, data in list(constants["constants"].items())[:limit]:
            results.append({
                "constant": name,
                "value": data["value"],
                "units": data["units"],
                "source": "NIST CODATA 2018",
            })

    return results
