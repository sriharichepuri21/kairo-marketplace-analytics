"""
Chaos engine configuration.

Defines which chaos types to apply, at what intensity,
and to which tables. Every parameter is tunable.
"""

from pydantic import BaseModel, Field


class DuplicateConfig(BaseModel):
    """Near-duplicate records from retry logic and CDC replays."""

    enabled: bool = True
    rate: float = Field(default=0.03, description="Fraction of rows to duplicate")
    timestamp_drift_seconds: int = Field(
        default=5,
        description="Max seconds of timestamp drift in duplicates",
    )
    modify_id: bool = Field(
        default=True,
        description="Give duplicates a new ID (simulates retry with new txn ID)",
    )


class NullChaosConfig(BaseModel):
    """Mixed null representations across source systems."""

    enabled: bool = True
    rate: float = Field(default=0.08, description="Fraction of nullable values to corrupt")
    representations: list[str] = Field(
        default=["N/A", "", "NULL", "null", "None", "-", "n/a", "NA", " ", "  "],
        description="Null representations to randomly choose from",
    )


class TypeDriftConfig(BaseModel):
    """Schema type changes — numbers as strings, mixed date formats."""

    enabled: bool = True
    rate: float = Field(default=0.05, description="Fraction of values to type-corrupt")
    date_formats: list[str] = Field(
        default=[
            "%m/%d/%Y",      # US: 01/15/2024
            "%d/%m/%Y",      # EU: 15/01/2024
            "%Y-%m-%d",      # ISO: 2024-01-15
            "%d-%b-%Y",      # 15-Jan-2024
            "%B %d, %Y",     # January 15, 2024
        ],
    )
    currency_prefixes: list[str] = Field(
        default=["$", "USD ", "€", "R$", ""],
        description="Prefixes randomly added to monetary values",
    )


class EncodingChaosConfig(BaseModel):
    """UTF-8/Latin-1 encoding corruption in text fields."""

    enabled: bool = True
    rate: float = Field(default=0.04, description="Fraction of text values to corrupt")
    replacements: dict[str, str] = Field(
        default={
            "é": "Ã©",
            "á": "Ã¡",
            "ñ": "Ã±",
            "ü": "Ã¼",
            "ö": "Ã¶",
            "ç": "Ã§",
            "í": "Ã­",
            "ó": "Ã³",
            "ú": "Ãº",
            "ã": "Ã£",
        },
        description="Character replacements simulating UTF-8 read as Latin-1",
    )


class LateArrivalConfig(BaseModel):
    """Records arriving in the wrong time batch."""

    enabled: bool = True
    rate: float = Field(default=0.02, description="Fraction of records that arrive late")
    max_delay_days: int = Field(
        default=90,
        description="Maximum days a record can be delayed",
    )


class OrphanRecordConfig(BaseModel):
    """Records with broken foreign keys."""

    enabled: bool = True
    rate: float = Field(default=0.01, description="Fraction of FK values to break")


class BusinessLogicViolationConfig(BaseModel):
    """Impossible business states from upstream bugs."""

    enabled: bool = True
    rate: float = Field(default=0.02, description="Fraction of records with logic violations")


class ZombieTestDataConfig(BaseModel):
    """Test/QA records that were never cleaned up."""

    enabled: bool = True
    count: int = Field(default=50, description="Number of zombie records to inject")


class SchemaEvolutionConfig(BaseModel):
    """Columns that appear, rename, or disappear over time."""

    enabled: bool = True
    add_columns: list[str] = Field(
        default=["promo_code", "loyalty_points", "referral_source"],
        description="Columns that appear partway through the data",
    )
    rename_columns: dict[str, str] = Field(
        default={"customer_external_id": "cust_ext_id"},
        description="Column renames that happen mid-stream",
    )


class ChaosConfig(BaseModel):
    """Master chaos configuration."""

    duplicates: DuplicateConfig = DuplicateConfig()
    null_chaos: NullChaosConfig = NullChaosConfig()
    type_drift: TypeDriftConfig = TypeDriftConfig()
    encoding: EncodingChaosConfig = EncodingChaosConfig()
    late_arrival: LateArrivalConfig = LateArrivalConfig()
    orphan_records: OrphanRecordConfig = OrphanRecordConfig()
    business_logic: BusinessLogicViolationConfig = BusinessLogicViolationConfig()
    zombie_test_data: ZombieTestDataConfig = ZombieTestDataConfig()
    schema_evolution: SchemaEvolutionConfig = SchemaEvolutionConfig()

    # Global seed for reproducibility
    seed: int = 42