from enum import Enum


class ChangeType(str, Enum):
    FOREST = "forest"
    FARMING = "farming"
    GLACIER = "glacier"
    GROUND = "ground"
    WETLAND = "wetland"
    INFRASTRUCTURE = "infrastructure"
    AUTO = "auto"


# Which NISAR products can support which analysis. Not every product feeds every module.
CHANGE_PRODUCTS: dict[ChangeType, list[str]] = {
    ChangeType.GROUND: ["GUNW"],
    ChangeType.FOREST: ["GCOV", "GSLC"],
    ChangeType.WETLAND: ["GCOV", "GSLC"],
    ChangeType.FARMING: ["GCOV", "SME2"],
    ChangeType.GLACIER: ["GOFF"],
    ChangeType.INFRASTRUCTURE: ["GUNW", "GCOV"],
    ChangeType.AUTO: ["GUNW", "GSLC", "GCOV", "GOFF", "SME2"],
}
