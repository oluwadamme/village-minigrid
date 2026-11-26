"""Download (once) and locate the public data this project uses. Raw files go to data/raw/.

| Data | Source | Licence |
|---|---|---|
| Village clusters, Cross River | RLI / GIZ NESP, energydata.info | CC BY-SA 4.0 |
| Household survey, Nigeria 2018 | World Bank ESMAP Multi-Tier Framework, energydata.info | CC BY 4.0 |
| Solar typical year | EU JRC PVGIS 5.3 (SARAH3 2005-2023) | free to use, cite PVGIS |
"""
import json
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
CKAN = "https://energydata.info/api/3/action/package_show?id="

RLI_PACKAGE = "rural-electrification-modelling-for-five-nigerian-federal-states"
RLI_RESOURCE = "Village electrification Cross River"
MTF_PACKAGE = "nigeria-multi-tier-framework-mtf-survey-59"
MTF_RESOURCES = ["MTF_Nigeria_Raw_Data.zip", "MTF_Nigeria_Codebook.xlsx", "Nigeria_Weights.dta"]

# Umon South ward, Biase LGA (RLI cluster 10645): centre of the cluster polygon
SITE = {"name": "Umon South, Biase LGA, Cross River State", "rli_id": 10645,
        "lat": 5.364, "lon": 8.050, "utc_offset_h": 1}


def _ckan_url(package: str, resource_name: str) -> str:
    res = requests.get(CKAN + package, timeout=60).json()["result"]["resources"]
    return next(r["url"] for r in res if r["name"] == resource_name)


def _download(url: str, path: Path) -> Path:
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        r = requests.get(url, timeout=300)
        r.raise_for_status()
        path.write_bytes(r.content)
    return path


def _unzip(path: Path, dest: Path) -> Path:
    import zipfile
    if not dest.exists():
        with zipfile.ZipFile(path) as z:
            z.extractall(dest)
    return dest


def rli_cross_river() -> Path:
    """Folder with the Cross River village-cluster shapefiles."""
    folder = RAW / "rli_cross_river"
    z = _download(_ckan_url(RLI_PACKAGE, RLI_RESOURCE), folder / "village_electrification_cross_river.zip")
    _unzip(z, folder / "unzipped")
    shp = next((folder).rglob("cluster_phases_State_Cross River.shp"))
    return shp.parent


def mtf_nigeria() -> Path:
    """Folder with the MTF Nigeria .dta files."""
    folder = RAW / "mtf"
    for name in MTF_RESOURCES:
        _download(_ckan_url(MTF_PACKAGE, name), folder / name)
    _unzip(folder / "MTF_Nigeria_Raw_Data.zip", folder / "raw")
    return next((folder / "raw").rglob("MTF_NG_HH_SEC_N_ELEC_ASSET.dta")).parent


def mtf_weights() -> Path:
    mtf_nigeria()
    return RAW / "mtf" / "Nigeria_Weights.dta"


def pvgis_tmy(lat: float = SITE["lat"], lon: float = SITE["lon"]) -> dict:
    """PVGIS typical meteorological year (hourly, UTC) for the site."""
    path = RAW / "pvgis" / f"tmy_{lat:.3f}_{lon:.3f}.json"
    legacy = RAW / "pvgis" / "tmy_umon_south.json"  # first download, same request
    if not path.exists() and legacy.exists():
        path = legacy
    url = f"https://re.jrc.ec.europa.eu/api/v5_3/tmy?lat={lat}&lon={lon}&outputformat=json"
    return json.loads(_download(url, path).read_text())
