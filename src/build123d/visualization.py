"""Visualization layer for Material.

Build123d's Material owns physical properties; visualization (PBR scalars,
textures, finishes) is delegated to VisProperties. Two backends are
available:

- pymat (use_pymat=True): source pointer (ambientcg/Wood095) resolved at
  Material.pbr time. The pymat material's vis identity is mutated
  (deepcopy first) and vis.to_threejs() produces the PbrProperties.

- threejs_materials (use_pymat=False): a fully-formed PbrProperties from
  threejs_materials. Used directly, no pymat involvement.

Apply tweaks via the .override(...) method, which returns a new
VisProperties — chain or store for variants.
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any, Literal, TYPE_CHECKING

import pymat
from pymat.vis._model import Vis as PymatVis
from threejs_materials import PbrOverrides, PbrProperties

VisSource = Literal["gpuopen", "ambientcg", "polyhaven", "physicallybased", "unknown"]

_PBRLOADER = {
    "ambientcg": PbrProperties.from_ambientcg,
    "gpuopen": PbrProperties.from_gpuopen,
    "polyhaven": PbrProperties.from_polyhaven,
    "physicallybased": PbrProperties.from_physicallybased,
}

_COLOR_FIELDS = (
    "color",
    "emissive",
    "sheen_color",
    "specular_color",
    "attenuation_color",
)

if TYPE_CHECKING:  # pragma: no cover
    from .geometry import ColorLike


def _coerce_color(c):
    """Convert a build123d Color to a tuple; pass other forms through.

    Build123d Color is detected via duck-typing on categorical_set (a public
    classmethod unique to Color) so visualization.py keeps zero runtime imports
    from geometry.py. Should Color move to its own module, this becomes
    isinstance(c, Color).
    """
    if c is not None and hasattr(c, "categorical_set"):
        return tuple(c)
    return c


class VisProperties:  # pylint: disable=too-many-instance-attributes
    """External visualization properties for a Material.

    Built via from_ambientcg / from_gpuopen / from_polyhaven / from_physicallybased
    / from_gltf factories. Apply per-instance tweaks via the .override(...)
    method, which returns a new VisProperties:

        base = VisProperties.from_gpuopen("Portoro Green Marble", use_pymat=False)
        polished = base.override(roughness=0.3)
        red_polished = polished.override(color="red")
    """

    DEFAULT_FINISH_NAME = "custom"

    def __init__(
        self,
        source: VisSource | Literal["gltf"],
        name: str,
        *,
        path: str | Path | None = None,
        use_pymat: bool = True,
        tier: str | None = "1k",
    ):
        """Create external visualization properties for a Material.

        Args:
            source (VisSource | Literal["gltf"]): Which web resource the material
                lives on, or "gltf" to load from a local glTF/GLB file.
            name (str): Material identifier from the source website, or material name
                inside the glTF file.
            path (str | Path | None): Path to a local .gltf/.glb file. Required when
                source == "gltf"; ignored otherwise. Defaults to None
            use_pymat (bool): When True, textures and scalars come from pymat's
                mat-vis-client. When False, falls back to threejs_materials' direct
                catalog — needed for materials not yet covered by pymat (currently
                most of gpuopen and polyhaven). GLTF always uses threejs_materials
                regardless. Defaults to True
            tier (str | None): Texture resolution tier (e.g. "1k", "2k", "4k").
                Ignored for GLTF. Defaults to "1k"
        """
        self._source = source
        self._name = name
        self._overrides: PbrOverrides = PbrOverrides()
        self._texture_scale: tuple[float, float] | None = None
        self._pymat_vis: PymatVis | None = None
        self._path = path
        self._finish: str | None = None

        if source == "gltf":
            # GLTF only has a threejs_materials loader.
            # tier is fixed by the file content.
            self._use_pymat = False
            self._tier = None
        else:
            self._use_pymat = use_pymat
            self._tier = tier

    @property
    def source(self) -> VisSource | Literal["gltf"]:
        """The visualization source ("ambientcg", "gpuopen", etc., or "gltf")."""
        return self._source

    @property
    def material_id(self) -> str:
        """Material identifier within the source — name on the website or in the glTF file."""
        return self._name

    @property
    def finish(self) -> str | None:
        """Name of the active pymat finish, or None for vis with no finish concept."""
        return self._finish

    def override(  # pylint: disable=too-many-locals,unused-argument
        self,
        *,
        color: ColorLike | None = None,
        roughness: float | None = None,
        metalness: float | None = None,
        ior: float | None = None,
        transmission: float | None = None,
        opacity: float | None = None,
        transparent: bool | None = None,
        alpha_test: float | None = None,
        clearcoat: float | None = None,
        clearcoat_roughness: float | None = None,
        sheen: float | None = None,
        sheen_color: ColorLike | None = None,
        sheen_roughness: float | None = None,
        anisotropy: float | None = None,
        anisotropy_rotation: float | None = None,
        specular_intensity: float | None = None,
        specular_color: ColorLike | None = None,
        emissive: ColorLike | None = None,
        emissive_intensity: float | None = None,
        attenuation_color: ColorLike | None = None,
        attenuation_distance: float | None = None,
        thickness: float | None = None,
        iridescence: float | None = None,
        iridescence_ior: float | None = None,
        iridescence_thickness_range: tuple[float, float] | None = None,
        dispersion: float | None = None,
        normal_scale: tuple[float, float] | None = None,
        displacement_scale: float | None = None,
        texture_scale: tuple[float, float] | None = None,
    ) -> VisProperties:
        """Return a new VisProperties with overrides applied on top.

        Inherits this VisProperties' current overrides; new kwargs win on conflict.

        Color-typed fields (color, emissive, sheen_color, specular_color,
        attenuation_color) accept any build123d ColorLike — names, hex strings,
        RGB(A) tuples, Color instances, hex ints. Numeric fields take floats
        in [0, 1] except ior, thickness, and attenuation_distance which take
        physical units. texture_scale is a (u, v) UV scale factor; (2, 2)
        makes the texture appear 2x larger.

            base = VisProperties.from_gpuopen("Portoro Green Marble", use_pymat=False)
            polished = base.override(roughness=0.3)
            red_polished = polished.override(color="red")
        """

        kwargs = {k: v for k, v in locals().items() if v is not None and k != "self"}

        new_vis = copy.copy(self)

        ts = kwargs.pop("texture_scale", None)
        if ts is not None:
            new_vis._texture_scale = ts

        if kwargs:
            for fname in _COLOR_FIELDS:
                if fname in kwargs:
                    kwargs[fname] = _coerce_color(kwargs[fname])
            merged = new_vis._overrides.as_kwargs()
            merged.update(kwargs)
            new_vis._overrides = PbrOverrides(**merged)
        return new_vis

    @classmethod
    def from_ambientcg(
        cls,
        name: str,
        *,
        tier: str | None = "1k",
        use_pymat: bool = True,
    ):
        """Load visualization properties from https://ambientCG.com.

        Args:
            name (str): Material identifier from the source website
            tier (str | None): Texture resolution tier (e.g. "1k", "2k", "4k").
                Defaults to "1k"
            use_pymat (bool): True uses pymat's mat-vis-client; False falls back
                to threejs_materials' direct catalog. Defaults to True
        """
        return cls("ambientcg", name, use_pymat=use_pymat, tier=tier)

    @classmethod
    def from_gpuopen(
        cls,
        name: str,
        *,
        tier: str | None = "1k",
        use_pymat: bool = True,
    ):
        """Load visualization properties from https://matlib.gpuopen.com/.

        Args:
            name (str): Material identifier from the source website
            tier (str | None): Texture resolution tier (e.g. "1k", "2k", "4k").
                Defaults to "1k"
            use_pymat (bool): True uses pymat's mat-vis-client; False falls back
                to threejs_materials' direct catalog. Defaults to True
        """
        return cls("gpuopen", name, use_pymat=use_pymat, tier=tier)

    @classmethod
    def from_polyhaven(
        cls,
        name: str,
        *,
        tier: str | None = "1k",
        use_pymat: bool = True,
    ):
        """Load visualization properties from https://polyhaven.com/textures.

        Args:
            name (str): Material identifier from the source website
            tier (str | None): Texture resolution tier (e.g. "1k", "2k", "4k").
                Defaults to "1k"
            use_pymat (bool): True uses pymat's mat-vis-client; False falls back
                to threejs_materials' direct catalog. Defaults to True
        """
        return cls("polyhaven", name, use_pymat=use_pymat, tier=tier)

    @classmethod
    def from_physicallybased(
        cls,
        name: str,
        *,
        use_pymat: bool = False,
    ):
        """Load visualization properties from https://physicallybased.info/.

        Note:
            PhysicallyBased does not provide any textures.

        Args:
            name (str): Material identifier from the source website
            use_pymat (bool): True uses pymat's mat-vis-client; False falls back
                to threejs_materials' direct catalog. Defaults to False
        """
        return cls("physicallybased", name, use_pymat=use_pymat, tier=None)

    @staticmethod
    def list_gltf_materials(path: str | Path) -> list[str]:
        """Return material names available in a glTF/GLB file.

        Use to discover what's in a file before calling from_gltf(path, name).

            for name in VisProperties.list_gltf_materials("file.glb"):
                print(name)

        Args:
            path (str | Path): Path to the .gltf/.glb file.
        """
        path = Path(path)
        if not path.exists():
            raise ValueError(f"File {path} does not exist")
        if path.suffix.lower() not in (".gltf", ".glb"):
            raise ValueError("File name must end with '.gltf' or '.glb'")
        loaded = PbrProperties.load_gltf(str(path))
        if isinstance(loaded, dict):
            return list(loaded.keys())
        return [loaded.name]

    @classmethod
    def from_gltf(cls, path: str | Path, name: str) -> VisProperties:
        """Load visualization properties from a gltf/glb file.

        Args:
            path (str | Path): Path to a local .gltf/.glb file.
            name (str): Material identifier for the material inside the glTF file.
        """
        if path is None:
            raise ValueError("Path to a gltf/glb file must be given")
        path = Path(path)
        if not path.exists():
            raise ValueError(f"File {path} does not exist")
        if path.suffix.lower() not in (".gltf", ".glb"):
            raise ValueError("File name must end with '.gltf' or '.glb'")

        return cls("gltf", name, path=path)

    @classmethod
    def _from_pymat(cls, material: pymat.Material) -> VisProperties:
        """Wrap a pymat.Material's vis as a VisProperties.

        Used by Material for the simple-kwargs path so resolution always
        flows through VisProperties.resolve. The caller deepcopies and sets
        material.vis.finish if needed before calling — no further mutation
        happens here.

        Args:
            material (pymat.Material): The pymat material whose vis is wrapped.
                Its source, material_id, tier, and currently-selected finish
                are taken as-is.
        """
        vis = cls(
            material.vis.source or "unknown",
            material.vis.material_id or "material",
            use_pymat=True,
            tier=material.vis.tier,
        )
        vis._pymat_vis = material.vis
        vis._finish = material.vis.finish
        return vis

    def resolve(self) -> PbrProperties:
        """Return a PbrProperties for this VisProperties."""
        if self._source == "gltf":
            loaded: Any = PbrProperties.load_gltf(str(self._path))
            if isinstance(loaded, dict):
                pbr = loaded[self._name]
            else:
                pbr = loaded
        elif self._use_pymat:
            if self._pymat_vis is None:
                pymat_vis = PymatVis(
                    source=self._source,
                    material_id=self._name,
                    finishes={
                        self.DEFAULT_FINISH_NAME: {
                            "source": self._source,
                            "id": self._name,
                        }
                    },
                )
                pymat_vis.finish = self.DEFAULT_FINISH_NAME
                pymat_vis.tier = self._tier
            else:
                pymat_vis = self._pymat_vis
            pbr = PbrProperties.from_pymat(
                pymat_vis.to_threejs(),
                name=self._name or "Material",
                id=self._name or "Material",
                source=pymat_vis.source or "unknown",
            )
        else:
            pbr = _PBRLOADER[self._source](self._name, self._tier or "1k")

        override_kwargs = self._overrides.as_kwargs()
        if override_kwargs:
            pbr = pbr.override(**override_kwargs)

        if self._texture_scale is not None:
            u, v = self._texture_scale
            pbr = pbr.scale(u, v)

        # Ensure that textures always have the same size independent of face size
        pbr.normalize_uvs = True

        return pbr

    def __repr__(self) -> str:
        result = f"VisProperties(source={self._source}, name={self._name!r}"
        if self._source == "gltf":
            result += f", path={self._path}"
        else:
            result += f", tier={self._tier!r}, use_pymat={self._use_pymat}"
        if self._overrides.as_kwargs():
            result += f", overrides={self._overrides}"
        if self._texture_scale is not None:
            result += f", texture_scale={self._texture_scale}"
        result += ")"
        return result
