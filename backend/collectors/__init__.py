from .steam_market import SteamMarketCollector, MockSteamMarketCollector
from .csfloat_market import CSFloatMarketCollector
from .data_validation import DataValidator, DataCleaner
from .pipeline import DataPipeline, PipelineMonitor


def _optional_import(module_name, names):
    """Import optional collectors without breaking package imports."""
    try:
        module = __import__(f"{__name__}.{module_name}", fromlist=names)
    except ModuleNotFoundError:
        return {name: None for name in names}
    return {name: getattr(module, name) for name in names}


_cs2_data_sources = _optional_import(
    "cs2_data_sources", ["CS2ItemCatalog", "CS2GameEvents", "HistoricalDataGenerator"]
)
_comprehensive_loader = _optional_import(
    "comprehensive_loader",
    ["ComprehensiveDataLoader", "load_all_cs2_data", "load_demo_cs2_data", "load_catalog_only"],
)
_free_data_importer = _optional_import(
    "free_data_importer",
    ["CS2ShClient", "FreeDataBackfillImporter", "SteamAnnouncementsImporter", "load_free_cs2_data"],
)

CS2ItemCatalog = _cs2_data_sources["CS2ItemCatalog"]
CS2GameEvents = _cs2_data_sources["CS2GameEvents"]
HistoricalDataGenerator = _cs2_data_sources["HistoricalDataGenerator"]

ComprehensiveDataLoader = _comprehensive_loader["ComprehensiveDataLoader"]
load_all_cs2_data = _comprehensive_loader["load_all_cs2_data"]
load_demo_cs2_data = _comprehensive_loader["load_demo_cs2_data"]
load_catalog_only = _comprehensive_loader["load_catalog_only"]

CS2ShClient = _free_data_importer["CS2ShClient"]
FreeDataBackfillImporter = _free_data_importer["FreeDataBackfillImporter"]
SteamAnnouncementsImporter = _free_data_importer["SteamAnnouncementsImporter"]
load_free_cs2_data = _free_data_importer["load_free_cs2_data"]

__all__ = [
    'SteamMarketCollector',
    'MockSteamMarketCollector',
    'CSFloatMarketCollector',
    'DataValidator',
    'DataCleaner',
    'DataPipeline',
    'PipelineMonitor',
    'CS2ItemCatalog',
    'CS2GameEvents',
    'HistoricalDataGenerator',
    'ComprehensiveDataLoader',
    'load_all_cs2_data',
    'load_demo_cs2_data',
    'load_catalog_only',
    'CS2ShClient',
    'FreeDataBackfillImporter',
    'SteamAnnouncementsImporter',
    'load_free_cs2_data',
]
