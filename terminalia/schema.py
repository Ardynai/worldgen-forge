"""Terminalia scene schema — world.json contract (pydantic)."""
from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Literal


class WorldSpec(BaseModel):
    prompt: str
    seed: int = 42
    size_hectares: float = 100.0
    biomes: list[str] = Field(default_factory=list)
    points_of_interest: list[str] = Field(default_factory=list)
    time_of_day: Literal["dawn", "noon", "dusk", "night"] = "dusk"
    style: str = "stylized realistic"


class Region(BaseModel):
    name: str
    mask: str  # path to region mask PNG
    biome: str
    color_hint: tuple[int, int, int] | None = None


class Terrain(BaseModel):
    heightmap: str
    regions: list[Region] = Field(default_factory=list)
    operators: list[str] = Field(default_factory=list)  # authored op log
    meters_per_pixel: float = 2.0
    min_height_m: float = 0.0
    max_height_m: float = 250.0


class InstancePose(BaseModel):
    frame: int
    translation: tuple[float, float, float]
    rotation_xyzw: tuple[float, float, float, float]


class Physics(BaseModel):
    urdf: str | None = None
    mass_kg: float | None = None
    static: bool = False


class PlacedObject(BaseModel):
    id: str
    asset: str  # key into assets
    pos_xy: tuple[float, float]
    rot_z: float = 0.0
    scale: float = 1.0
    z_offset: float = 0.0
    contact_ratio: float = 0.0  # from placement search
    role: Literal["hero", "prop", "foliage", "terrain_feature"] = "prop"
    poses: list[InstancePose] = Field(default_factory=list)
    physics: Physics | None = None


class Layout(BaseModel):
    composition_image: str | None = None
    layout_map: str | None = None
    objects: list[PlacedObject] = Field(default_factory=list)


class AssetEntry(BaseModel):
    glb: str
    concept_image: str | None = None
    tris: int = 0
    source_preset: str = "1024_cascade"
    bbox_size: tuple[float, float, float] | None = None


class ModelRef(BaseModel):
    name: str
    version: str
    license: str


class VideoProvenance(BaseModel):
    source_sha256: str = ""
    consent_note: str = ""
    models: list[ModelRef]
    engine: str | None = None
    seed: int | None = None
    backend: str | None = None
    profile: str | None = None
    artifacts: list["ArtifactRef"] = Field(default_factory=list)


class CameraPath(BaseModel):
    waypoints: list[tuple[float, float, float]] = Field(default_factory=list)


class HistoryEntry(BaseModel):
    stage: str
    at: str
    notes: str = ""


class ArtifactRef(BaseModel):
    uri: str
    kind: Literal["frames", "video", "mesh_render"]


class FixAnythingPass(BaseModel):
    status: Literal["ran", "skipped"]
    inputs: list[ArtifactRef] = Field(default_factory=list)
    outputs: list[ArtifactRef] = Field(default_factory=list)
    seed: int
    backend: str
    profile: str
    weights: dict[str, str] = Field(default_factory=dict)
    reason: str | None = None


class Refinement(BaseModel):
    render_artifacts: list[ArtifactRef] = Field(default_factory=list)
    fix_anything: FixAnythingPass | None = None


class SplatScene(BaseModel):
    """A local source descriptor; it is not publication consent."""
    model_config = {"extra": "forbid"}
    file: str = Field(min_length=1, max_length=512)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    license: str = Field(min_length=1, max_length=128)
    attribution: str = Field(min_length=1, max_length=500)
    up_axis: Literal["Y", "Z"] = "Y"


class World(BaseModel):
    version: str = "0.3"
    spec: WorldSpec
    terrain: Terrain | None = None
    layout: Layout = Field(default_factory=Layout)
    assets: dict[str, AssetEntry] = Field(default_factory=dict)
    camera: CameraPath = Field(default_factory=CameraPath)
    refine: Refinement = Field(default_factory=Refinement)
    history: list[HistoryEntry] = Field(default_factory=list)
    video_provenance: VideoProvenance | None = None
    splat: SplatScene | None = None

    def save(self, path: str) -> None:
        import json
        with open(path, "w") as f:
            json.dump(self.model_dump(), f, indent=1)

    @classmethod
    def load(cls, path: str) -> "World":
        import json
        with open(path) as f:
            return cls.model_validate(json.load(f))
